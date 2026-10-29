"""The registry and config files for the change drill, each read through one function.

Each file in config/ is one of the spec's single places ("Ten single places"), so a change
request lands in one file (CLAUDE.md rule 9). This module reads them:

- load_sources()     config/sources.toml, the source registry
- load_slice()       config/slice.toml, the slice file
- load_sectors()     config/sectors.toml, the one sector taxonomy
- load_models()      config/models.toml, the model file (load_layout_parser() reads its [layout] table,
                     load_search() its [search] table, load_supplier_matching() its
                     [supplier_matching] table, and load_time_estimate() its [time_estimate] table)
- load_thresholds()  config/thresholds.toml, the thresholds file
- load_tools()       config/tools.toml, the tool registry (strata.tools.registry calls the tools)
- load_agent()       config/agents.toml, the agent registry: one Foundry agent and its guardrail
                     (strata.agent.definition builds the agent's definition from it)
- load_draft_kinds() config/drafts.toml, the draft-kind registry: each kind of draft and its holds
- load_roles()       config/roles.toml, the roles file: the teams that share drafts, by workspace
                     group, and the groups that review lessons, with the people in them, their
                     regions and their projects (ticket 29)
- load_ladder()      config/evidence_ladder.toml, the evidence ladder: the rules that choose the
                     assertion Strata leans on when two disagree, the evidence tiers, the attributes
                     an assertion can be about and their rating scales
- load_lesson_lists() config/lessons.toml, the lesson lists: the closed lists of risk factors, stages
                     and kinds, and the extractor's example projects (ticket 29)
- load_editions()    config/editions.toml, the editions of the procurement rules a project followed
- load_package_form() config/package_form.toml, the package form schema: the groups and fields a
                     package planned from a sentence has, each one a chip (ticket 15)
- load_uploads()     config/uploads.toml, the upload and STEP row registry: what an implementing agency's
                     upload may be and the STEP columns its reader and the STEP rows CSV use (ticket 38)
- load_languages()   config/languages.toml, the language registry: each language a source can be
                     written in, and how Strata writes and checks the four working languages (ticket 42)
- load_method_names() config/method_names.toml, the method-name registry: the current Procurement
                     Regulations' names and every other name a source writes for one (ticket 42)
- load_budget()      config/budget.toml, the Azure budget: the free credit, the day it ends and the
                     monthly budget after it, for the daily cost pull and the wizard (ticket 45)
- load_kpis()        config/kpis.toml, the KPI registry: each KPI the dashboard shows, defined once by
                     its query, with its kind, rounding, target and copy keys (ticket 45)
- load_urls()        config/urls.toml, the panel's addresses: Strata, the dashboard and the repo, and the
                     deck and the proposal that follow from them (ticket 46)
- load_rubric()      config/rubric.toml, the rubric map: the assessment's dimensions, points and criteria,
                     and where the proposal answers each one (ticket 46)
- load_change_drills() config/change_drills.toml, the change drill: each likely change, its one place and
                     its proving test (tickets 46 and 49). Its rehearsal times are measured results, in
                     docs/proposal/rehearsals.toml (strata.proposal.register.load_rehearsals)
- load_designed_not_built() config/designed_not_built.toml, what is designed but not built: the app's
                     labels and the proposal's short list both read it (ticket 46)

Each function checks the file's shape and raises ConfigError with a sentence that names the
file, the entry and the fix. It uses only the standard library, so the nightly job can call it.
"""

from __future__ import annotations

import datetime as dt
import os
import pickle
import re
import tomllib
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PROJECT_ID = re.compile(r"P\d{6}")


class ConfigError(ValueError):
    """A config file that does not follow its shape, with what to change."""


# Each file as parsed, pickled, by its path and the size, time and inode it had then (ticket 56). The readers
# run on every call, and parsing TOML took about a tenth of the processor time of the slowest tests. A file
# that changes is parsed again on its next read, and each caller gets its own copy, which a pickle gives at
# about a hundredth of the cost of parsing.
_PARSED: dict[str, tuple[tuple[int, int, int], bytes]] = {}


def _read(path: Path) -> dict:
    try:
        found = os.stat(path)
        stamp = (found.st_mtime_ns, found.st_size, found.st_ino)
        held = _PARSED.get(str(path))
        if held and held[0] == stamp:
            return pickle.loads(held[1])
        with open(path, "rb") as handle:
            data = tomllib.load(handle)
    except FileNotFoundError as error:
        raise ConfigError(f"I could not find {path}.") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path.name} is not valid TOML: {error}.") from error
    blob = pickle.dumps(data)
    _PARSED[str(path)] = (stamp, blob)
    return pickle.loads(blob)


class _Entry:
    """One table in a config file, read key by key so each mistake names its place."""

    def __init__(self, path: Path, where: str, table):
        if not isinstance(table, dict):
            raise ConfigError(f"In {path.name}, {where} must be a table of keys.")
        self.path, self.where, self.table = path, where, table

    def _fail(self, key: str, need: str):
        raise ConfigError(f"In {self.path.name}, {self.where}.{key} {need}.")

    def text(self, key: str, required: bool = True) -> str | None:
        value = self.table.get(key)
        if value is None:
            if required:
                self._fail(key, "is missing")
            return None
        if not isinstance(value, str) or not value.strip():
            self._fail(key, "must be text")
        return value

    def integer(self, key: str, required: bool = True) -> int | None:
        value = self.table.get(key)
        if value is None:
            if required:
                self._fail(key, "is missing")
            return None
        if not isinstance(value, int) or isinstance(value, bool):
            self._fail(key, "must be a whole number")
        return value

    def boolean(self, key: str) -> bool:
        value = self.table.get(key)
        if not isinstance(value, bool):
            self._fail(key, "must be true or false")
        return value

    def date(self, key: str) -> dt.date:
        value = self.table.get(key)
        if not isinstance(value, dt.date) or isinstance(value, dt.datetime):
            self._fail(key, "must be a date such as 2026-10-09, without quotes")
        return value

    def texts(self, key: str) -> tuple[str, ...]:
        value = self.table.get(key, [])
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            self._fail(key, "must be a list of text")
        return tuple(value)

    def project_id(self, key: str, required: bool = True) -> str | None:
        value = self.text(key, required)
        if value is not None and not PROJECT_ID.fullmatch(value):
            self._fail(key, f"must be a project ID, P followed by six digits, not {value!r}")
        return value

    def only(self, allowed: set[str]):
        unknown = sorted(set(self.table) - allowed)
        if unknown:
            raise ConfigError(f"In {self.path.name}, {self.where} has keys I do not know: {', '.join(unknown)}. "
                              f"It can use only these: {', '.join(sorted(allowed))}.")


def _tables(path: Path, data: dict, key: str) -> list[_Entry]:
    tables = data.get(key, [])
    if not isinstance(tables, list):
        raise ConfigError(f"In {path.name}, write each of {key} as a [[{key}]] table.")
    return [_Entry(path, f"{key}[{number}]", table) for number, table in enumerate(tables, 1)]


# ── The source registry ──────────────────────────────────────────────────

CADENCES = ("daily", "weekly", "monthly", "quarterly", "yearly", "frozen")
STRATA = ("What", "How", "Why")
APIS = ("finances_one", "search", "indicators")
EVERY_COUNTRY, SLICE_COUNTRIES = "every country", "slice countries"
SCOPES = (EVERY_COUNTRY, SLICE_COUNTRIES)
# The schedule a readiness row can give in place of its source's cadence: documents arrive when
# their authors publish them, so their freshness is the newest document's date and never late.
AS_PUBLISHED = "as published"
# The four columns of the Data readiness page's Sources table (the 16 brief, section 5.1).
READINESS_COLUMNS = ("coverage", "linked", "read_well", "fresh")


@dataclass(frozen=True)
class ReadinessColumn:
    """The measure one cell of the Sources table shows, and the words around its number."""

    measure: str  # the measure in strata.ops.data_readiness, for this source
    counts: str  # what the number counts, shown under it, such as "carry a STEP reference"
    noun: str  # one counted thing, in the plural, for the number's tooltip and the gap sentence
    counted_in: str  # the table the measure counts, by its three-part name
    lack: str | None = None  # for a share: what a row that falls short lacks, for the gap sentence
    years: str | None = None  # for coverage: the measure that counts its fiscal years
    counts_one: str | None = None  # counts in the singular, for a count or a denominator of one
    noun_one: str | None = None  # noun in the singular, likewise
    # For a document collection's coverage: the measure that counts the projects its documents belong to,
    # and the one that counts the slice's projects whose documents were read, out of the slice's projects.
    projects: str | None = None
    slice_read: str | None = None
    # For a check of what Strata found, in place of lack: what it found none of on a row that falls short, so the gap
    # says "where I found no paragraph numbers" (ticket 58).
    not_found: str | None = None


@dataclass(frozen=True)
class ReadinessRoute:
    """One way a reader reads a source's pages, whose pages read well the dashboard charts by route."""

    measure: str  # the measure in strata.ops.data_readiness that counts the pages it read well
    label: str  # its name on the dashboard's chart, such as "Plan pages, layout parser"
    noun: str  # what the measure counts, in the plural
    counted_in: str  # the table it counts, by its three-part name


@dataclass(frozen=True)
class ReadinessRow:
    """One row of the Sources table: a source, or one reader's part of the documents source."""

    id: str
    label: str
    noun: str  # the source's records in the plural, for the gap sentences, such as "CPIA scores"
    stratum: str
    covers: str | None = None  # what the rows span, after the scope, such as "since fiscal 2020"
    schedule: str | None = None  # "as published", in place of the source's cadence
    coverage: ReadinessColumn | None = None
    linked: ReadinessColumn | None = None
    read_well: ReadinessColumn | None = None
    fresh: ReadinessColumn | None = None
    checks: tuple[ReadinessColumn, ...] = ()  # more measures that hold answers back when they fall short
    routes: tuple[ReadinessRoute, ...] = ()  # the reading routes of a paged reader, for the dashboard
    published_as: str | None = None  # "text": a row whose records arrive as text, with nothing to read well
    # Whether its Read well counts the same pages its routes do, so its window splits it by route.
    read_well_by_route: bool = False


@dataclass(frozen=True)
class KnownGap:
    """Fiscal years of a source that no dataset publishes, shown as a Gap row under the source."""

    id: str
    label: str
    noun: str
    first_fiscal_year: int
    last_fiscal_year: int
    note: str


@dataclass(frozen=True)
class DeclaredLimit:
    """A limit the source states about itself, which makes one cell Partial with this note."""

    row: str
    column: str
    note: str


@dataclass(frozen=True)
class Fix:
    """What would close a gap: a sentence whose numbers come from measure, ranked by the projects
    it would add evidence to. projects names the measure that counts them; without it, they are
    the measure's subjects, which are project IDs, that fall short."""

    sentence: str
    measure: str
    projects: str | None = None
    gap: str | None = None  # the known gap it closes, by id; otherwise it closes measure's shortfall
    noun: str | None = None  # what measure counts, when no column of the source shows that measure
    counted_in: str | None = None  # the table measure counts, when no column of the source shows it
    projects_counted_in: str | None = None  # the table the projects measure counts


@dataclass(frozen=True)
class Attribution:
    """How the World Bank credits a dataset: "The World Bank: {dataset_name}: {data_source}."."""

    data_source: str
    catalog_url: str
    name_checked: dt.date  # the day dataset_name was checked against the catalog (PLAN.md section 18)


@dataclass(frozen=True)
class Collection:
    """A collection of documents the documents source reads, for the Sources and licenses page."""

    name: str
    publisher: str
    origin: str
    # The language its name is written in, when it is not English (ticket 42): the page sets it as the name's lang.
    language: str | None = None


@dataclass(frozen=True)
class Source:
    """One data source: where it answers, how its pages are fetched, how often it changes, and how
    it is credited. A source the nightly job fetches page by page names api, records, page_size,
    fixture_dataset and scope; a source its own reader fetches, such as documents (the plan
    reader), names none of them.

    countries is empty for a source fetched for every country, which the job asks for in one series
    of pages with no country filter. For a source fetched for the slice countries, it holds the
    slice file's countries, and the job asks for each one with the source's country_filter."""

    key: str
    dataset_name: str
    endpoint: str
    watermark_field: str
    cadence: str
    license: str
    silver_transform: str
    api: str | None = None
    records: str | None = None
    scope: str | None = None
    country_filter: str | None = None
    page_size: int | None = None
    # The most records the API pages through in one fetch. The search API refuses an offset above
    # 100,000 ("Value must be between 0 and 100000. Parameter name: $skip"), so a fetch of a source
    # with more records stops there, and the readiness measures show the rows it could not reach.
    max_offset: int | None = None
    fixture_dataset: str | None = None
    dataset_id: str | None = None
    resource_id: str | None = None
    stratum: str | None = None
    # A record's own page on the World Bank's site, with {id} for its id, such as a notice's page.
    record_url: str | None = None
    # The form of assertion each of its rows gives the evidence ladder, such as contract_record for a dataset of
    # signed contracts (ticket 20, src/strata/knowledge/assertions.py).
    assertion_form: str | None = None
    # For a source a reader fetches document by document: the seconds it waits between two requests to the
    # source's host (ticket 43). The documents host refused every request from one computer on October 25, 2026,
    # after some hundreds of PDFs asked for as fast as they came.
    pause_seconds: float | None = None
    ignore_keys: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    countries: tuple[Country, ...] = ()
    # How the Data readiness page and the Sources and licenses page show the source (ticket 16).
    readiness: tuple[ReadinessRow, ...] = ()
    known_gaps: tuple[KnownGap, ...] = ()
    declared: tuple[DeclaredLimit, ...] = ()
    fixes: tuple[Fix, ...] = ()
    attribution: Attribution | None = None
    collections: tuple[Collection, ...] = ()

    @property
    def paged(self) -> bool:
        """Whether the nightly job fetches this source page by page."""
        return self.api is not None


SOURCE_REQUIRED = ("dataset_name", "endpoint", "watermark_field", "cadence", "license", "silver_transform")
SOURCE_PAGING = ("api", "records", "page_size", "fixture_dataset", "scope")  # all of them or none
SOURCE_OPTIONAL = ("dataset_id", "resource_id", "stratum", "country_filter", "record_url", "max_offset",
                   "assertion_form", "pause_seconds")
SOURCE_LISTS = ("ignore_keys", "limitations", "indicators")
SOURCE_ATTRIBUTION = ("data_source", "catalog_url", "name_checked")  # all of them or none
SOURCE_PAGE = ("readiness", "known_gaps", "declared", "fixes", "collections")  # arrays of tables


def load_sources(path: Path = CONFIG_DIR / "sources.toml",
                 slice_path: Path = CONFIG_DIR / "slice.toml") -> dict[str, Source]:
    """Every source in the registry, by its key. A source fetched for the slice countries carries
    the countries of the slice file at slice_path."""
    data = _read(path)
    _Entry(path, "the file", data).only({"sources"})
    sources = {}
    for key, table in data.get("sources", {}).items():
        entry = _Entry(path, f"sources.{key}", table)
        entry.only(set(SOURCE_REQUIRED + SOURCE_PAGING + SOURCE_OPTIONAL + SOURCE_LISTS + SOURCE_ATTRIBUTION
                       + SOURCE_PAGE))
        fields = {name: entry.text(name) for name in SOURCE_REQUIRED}
        fields |= {name: entry.text(name, required=False) for name in SOURCE_OPTIONAL
                   if name not in ("max_offset", "pause_seconds")}
        pause = table.get("pause_seconds")
        if pause is not None and (isinstance(pause, bool) or not isinstance(pause, int | float) or pause < 0):
            entry._fail("pause_seconds", "must be a number of seconds, 0 or more")
        fields["pause_seconds"] = None if pause is None else float(pause)
        fields |= {name: entry.texts(name) for name in SOURCE_LISTS}
        if fields["cadence"] not in CADENCES:
            entry._fail("cadence", f"must be one of {', '.join(CADENCES)}")
        if fields["stratum"] is not None and fields["stratum"] not in STRATA:
            entry._fail("stratum", f"must be one of {', '.join(STRATA)}")
        if any(name in table for name in SOURCE_PAGING):
            fields |= _paging(entry, table, fields)
            if fields["scope"] == SLICE_COUNTRIES:
                fields["countries"] = load_slice(slice_path).countries
        fields |= _page(path, key, entry, table, fields["stratum"])
        sources[key] = Source(key=key, **fields)
    ids = [row.id for source in sources.values() for row in source.readiness]
    twice = sorted({row for row in ids if ids.count(row) > 1})
    if twice:
        raise ConfigError(f"In {path.name}, more than one readiness row has the id {', '.join(twice)}. "
                          "Give each row its own id.")
    return sources


def _column(path: Path, where: str, table) -> ReadinessColumn:
    entry = _Entry(path, where, table)
    entry.only({"measure", "counts", "noun", "counted_in", "lack", "years", "counts_one", "noun_one", "projects",
                "slice_read", "not_found"})
    return ReadinessColumn(entry.text("measure"), entry.text("counts"), entry.text("noun"), entry.text("counted_in"),
                           entry.text("lack", required=False), entry.text("years", required=False),
                           entry.text("counts_one", required=False), entry.text("noun_one", required=False),
                           entry.text("projects", required=False), entry.text("slice_read", required=False),
                           entry.text("not_found", required=False))


def _route(path: Path, where: str, table) -> ReadinessRoute:
    entry = _Entry(path, where, table)
    entry.only({"measure", "label", "noun", "counted_in"})
    return ReadinessRoute(entry.text("measure"), entry.text("label"), entry.text("noun"), entry.text("counted_in"))


def _page(path: Path, key: str, entry: _Entry, table: dict, stratum: str | None) -> dict:
    """What the Data readiness page and the Sources and licenses page read about a source."""
    fields: dict = {}
    if any(name in table for name in SOURCE_ATTRIBUTION):
        fields["attribution"] = Attribution(entry.text("data_source"), entry.text("catalog_url"),
                                            entry.date("name_checked"))
    rows = []
    for row in _tables(path, table, "readiness"):
        row.where = f"sources.{key}.{row.where}"
        row.only({"id", "label", "noun", "stratum", "covers", "schedule", "checks", "routes", "published_as",
                  "read_well_by_route", *READINESS_COLUMNS})
        row_stratum = row.text("stratum", required=False) or stratum
        if row_stratum not in STRATA:
            row._fail("stratum", f"must be one of {', '.join(STRATA)}, here or on the source")
        schedule = row.text("schedule", required=False)
        if schedule not in (None, AS_PUBLISHED):
            row._fail("schedule", f'can only be "{AS_PUBLISHED}"; leave it out to use the source\'s cadence')
        published_as = row.text("published_as", required=False)
        by_route = row.table.get("read_well_by_route", False)
        if not isinstance(by_route, bool):
            row._fail("read_well_by_route", "must be true or false")
        if by_route and not row.table.get("routes"):
            row._fail("read_well_by_route", "needs routes to split Read well into")
        if published_as not in (None, "text"):
            row._fail("published_as", 'can only be "text": a row whose records arrive as text')
        if published_as and "read_well" in row.table:
            row._fail("read_well", "is not needed: a row published as text has nothing to read well")
        columns = {name: _column(path, f"{row.where}.{name}", row.table[name])
                   for name in READINESS_COLUMNS if name in row.table}
        checks, routes = row.table.get("checks", []), row.table.get("routes", [])
        for name, given in (("checks", checks), ("routes", routes)):
            if not isinstance(given, list):
                row._fail(name, "must be a list of inline tables")
        rows.append(ReadinessRow(row.text("id"), row.text("label"), row.text("noun"), row_stratum,
                                 row.text("covers", required=False), schedule, **columns,
                                 checks=tuple(_column(path, f"{row.where}.checks[{n}]", check)
                                              for n, check in enumerate(checks, 1)),
                                 routes=tuple(_route(path, f"{row.where}.routes[{n}]", route)
                                              for n, route in enumerate(routes, 1)),
                                 published_as=published_as, read_well_by_route=by_route))
    fields["readiness"] = tuple(rows)
    gaps = []
    for gap in _tables(path, table, "known_gaps"):
        gap.where = f"sources.{key}.{gap.where}"
        gap.only({"id", "label", "noun", "first_fiscal_year", "last_fiscal_year", "note"})
        gaps.append(KnownGap(gap.text("id"), gap.text("label"), gap.text("noun"), gap.integer("first_fiscal_year"),
                             gap.integer("last_fiscal_year"), gap.text("note")))
    fields["known_gaps"] = tuple(gaps)
    declared = []
    for limit in _tables(path, table, "declared"):
        limit.where = f"sources.{key}.{limit.where}"
        limit.only({"row", "column", "note"})
        row_id = limit.text("row", required=False) or (rows[0].id if rows else None)
        if row_id not in {row.id for row in rows}:
            limit._fail("row", "must name one of this source's readiness rows")
        if limit.text("column") not in READINESS_COLUMNS:
            limit._fail("column", f"must be one of {', '.join(READINESS_COLUMNS)}")
        declared.append(DeclaredLimit(row_id, limit.text("column"), limit.text("note")))
    fields["declared"] = tuple(declared)
    fixes = []
    for fix in _tables(path, table, "fixes"):
        fix.where = f"sources.{key}.{fix.where}"
        fix.only({"sentence", "measure", "projects", "gap", "noun", "counted_in", "projects_counted_in"})
        gap_id = fix.text("gap", required=False)
        if gap_id is not None and gap_id not in {gap.id for gap in gaps}:
            fix._fail("gap", "must name one of this source's known gaps by its id")
        shown = {column.measure for row in rows for column in (*(getattr(row, name) for name in READINESS_COLUMNS),
                                                                *row.checks) if column}
        noun = fix.text("noun", required=False)
        if noun is None and fix.text("measure") not in shown:
            fix._fail("noun", "must say what its measure counts, because no column of this source shows that measure")
        # Every number's window names the table it was counted in (review r7).
        if fix.text("counted_in", required=False) is None and fix.text("measure") not in shown:
            fix._fail("counted_in", "must name the table its measure counts, because no column of this source shows "
                                    "that measure")
        if fix.text("projects_counted_in", required=False) and not fix.text("projects", required=False):
            fix._fail("projects_counted_in", "names the table of the projects measure, so it needs projects")
        if fix.text("projects", required=False) and not fix.text("projects_counted_in", required=False):
            fix._fail("projects_counted_in", "must name the table the projects measure counts")
        fixes.append(Fix(fix.text("sentence"), fix.text("measure"), fix.text("projects", required=False), gap_id, noun,
                         fix.text("counted_in", required=False), fix.text("projects_counted_in", required=False)))
    fields["fixes"] = tuple(fixes)
    collections = []
    for collection in _tables(path, table, "collections"):
        collection.where = f"sources.{key}.{collection.where}"
        collection.only({"name", "publisher", "origin", "language"})
        language = collection.text("language", required=False)
        if language is not None and language not in {entry.code for entry in load_languages().languages}:
            collection._fail("language", f"names {language!r}, which config/languages.toml does not list")
        collections.append(Collection(collection.text("name"), collection.text("publisher"), collection.text("origin"),
                                      language))
    fields["collections"] = tuple(collections)
    return fields


def _paging(entry: _Entry, table: dict, fields: dict) -> dict:
    """The keys of a source the nightly job fetches page by page, which it names all together. An
    indicators source keeps its records in the second part of each page, so it names no records."""
    api = table.get("api")
    needed = [name for name in SOURCE_PAGING if not (name == "records" and api == "indicators")]
    missing = [name for name in needed if name not in table]
    if missing:
        entry._fail(missing[0], f"is missing. A source the nightly job fetches page by page names all of "
                                f"{', '.join(SOURCE_PAGING)} (an indicators source needs no records), and a "
                                "source its own reader fetches names none")
    paging = {name: entry.text(name) for name in needed if name != "page_size"}
    paging["page_size"] = entry.integer("page_size")
    paging["max_offset"] = entry.integer("max_offset", required=False)
    if paging["max_offset"] is not None and paging["max_offset"] < paging["page_size"]:
        entry._fail("max_offset", "must be at least page_size")
    if paging["api"] not in APIS:
        entry._fail("api", f"must be one of {', '.join(APIS)}")
    if paging["page_size"] < 1:
        entry._fail("page_size", "must be 1 or more")
    if paging["scope"] not in SCOPES:
        entry._fail("scope", f"must be one of {', '.join(SCOPES)}")
    if paging["scope"] == SLICE_COUNTRIES and not fields["country_filter"]:
        entry._fail("country_filter", "is missing. A source fetched for the slice countries asks for each "
                                      "country with it, such as filter=country_code%3D%27{iso2}%27")
    if paging["api"] == "indicators" and (not fields["indicators"] or "{indicator}" not in fields["endpoint"]):
        entry._fail("indicators", "must list the indicator codes, and the endpoint must hold {indicator} where "
                                  "each code goes")
    return paging


# ── The slice file ───────────────────────────────────────────────────────

@dataclass(frozen=True)
class Country:
    name: str
    iso2: str
    iso3: str


@dataclass(frozen=True)
class Onboarded:
    """A country using Strata, from the first day its World Bank staff used it (ticket 44)."""

    iso2: str
    since: dt.date


@dataclass(frozen=True)
class Showcase:
    project_id: str
    name: str


@dataclass(frozen=True)
class DemoPlan:
    """The published Procurement Plan that "Check a plan" opens in the demo, with the demo package and the two
    benchmark questions the demo-ready command asks (config/slice.toml says what each means)."""

    project_id: str
    project_name: str
    implementing_agency: str
    agency_short_name: str
    plan_date: dt.date
    package: str
    smoke_question: str
    genie_question: str


# The stress shelf's kinds, in the order the 18 design brief lists them, and the rules that pick a
# document at run time.
SHELF_KINDS = ("scan_annex", "longest_pad", "large_plan", "other_language", "over_parser_limit")
SHELF_RULES = ("longest", "over_parser_limit")


@dataclass(frozen=True)
class ShelfItem:
    """One entry on the stress shelf: a fixed document (project_id and document_id) or a rule that
    picks one at run time, with what its kind needs (config/slice.toml says what each key means)."""

    key: str
    kind: str
    project_id: str | None = None
    document_id: str | None = None
    rule: str | None = None
    document_type: str | None = None
    part: str | None = None
    first_page: int | None = None
    last_page: int | None = None
    expected_rows: int | None = None
    counted_on: dt.date | None = None
    language: str | None = None


@dataclass(frozen=True)
class Slice:
    countries: tuple[Country, ...]
    sectors: tuple[str, ...]
    first_fiscal_year: int
    last_fiscal_year: int
    showcase: Showcase
    demo_plan: DemoPlan
    stress_shelf: tuple[ShelfItem, ...]
    planned_projects: int | None = None  # docs/PLAN.md section 3's planning figure, never shown as a finding
    notice_types: tuple[str, ...] = ()  # the notice types whose scope and qualification text become passages
    onboarded: tuple[Onboarded, ...] = ()  # the countries using Strata and since when (ticket 44)

    def using_strata(self, iso2: str | None, on: dt.date) -> bool:
        """Whether a country was using Strata on a day: it is onboarded, from its since date on."""
        return any(country.iso2 == iso2 and country.since <= on for country in self.onboarded)

    @property
    def fiscal_years(self) -> range:
        return range(self.first_fiscal_year, self.last_fiscal_year + 1)

    @property
    def named_projects(self) -> tuple[str, ...]:
        """The projects the document run reads by name, whatever the criteria select: the showcase,
        the demo plan's project and each fixed shelf document's project, once each, in that order."""
        named = [self.showcase.project_id, self.demo_plan.project_id,
                 *(item.project_id for item in self.stress_shelf if item.project_id)]
        return tuple(dict.fromkeys(named))


def _shelf_item(entry: _Entry) -> ShelfItem:
    entry.only({"key", "kind", "project_id", "document_id", "rule", "document_type", "part", "first_page",
                "last_page", "expected_rows", "counted_on", "language"})
    kind = entry.text("kind")
    if kind not in SHELF_KINDS:
        entry._fail("kind", f"must be one of {', '.join(SHELF_KINDS)}")
    document_id, rule = entry.text("document_id", required=False), entry.text("rule", required=False)
    if (document_id is None) == (rule is None):
        raise ConfigError(f"In {entry.path.name}, {entry.where} names a document_id and a rule, or neither. "
                          "Name one: a fixed document with its project_id, or a rule that picks one.")
    if rule is not None and rule not in SHELF_RULES:
        entry._fail("rule", f"must be one of {', '.join(SHELF_RULES)}")
    if rule == "longest" and entry.text("document_type", required=False) is None:
        entry._fail("document_type", "is missing. The longest rule picks the longest document of that type")
    item = {"key": entry.text("key"), "kind": kind, "document_id": document_id, "rule": rule,
            "project_id": entry.project_id("project_id", required=document_id is not None),
            "document_type": entry.text("document_type", required=False)}
    if kind == "scan_annex":
        item |= {"part": entry.text("part"), "first_page": entry.integer("first_page"),
                 "last_page": entry.integer("last_page")}
        if not 1 <= item["first_page"] <= item["last_page"]:
            entry._fail("last_page", "must come on or after first_page, and both from 1")
        if "expected_rows" in entry.table:
            if "counted_on" not in entry.table:
                entry._fail("counted_on", "is missing. A hand count needs the day a person counted it")
            item |= {"expected_rows": entry.integer("expected_rows"), "counted_on": entry.date("counted_on")}
    if kind == "other_language":
        language = entry.text("language")
        if not re.fullmatch(r"[a-z]{2}", language):
            entry._fail("language", "must be a two-letter ISO 639-1 code, such as fr")
        item["language"] = language
    return ShelfItem(**item)


def load_slice(path: Path = CONFIG_DIR / "slice.toml") -> Slice:
    """The document slice, the showcase project, the demo plan and the stress shelf."""
    data = _read(path)
    top = _Entry(path, "the file", data)
    top.only({"first_fiscal_year", "last_fiscal_year", "sectors", "countries", "showcase", "demo_plan",
              "stress_shelf", "planned_projects", "notice_types", "onboarded"})

    countries = []
    for entry in _tables(path, data, "countries"):
        entry.only({"name", "iso2", "iso3"})
        country = Country(entry.text("name"), entry.text("iso2"), entry.text("iso3"))
        if not re.fullmatch(r"[A-Z]{2}", country.iso2):
            entry._fail("iso2", "must be two capital letters")
        if not re.fullmatch(r"[A-Z]{3}", country.iso3):
            entry._fail("iso3", "must be three capital letters")
        countries.append(country)
    if not countries:
        raise ConfigError(f"{path.name} names no country. Add at least one [[countries]] entry.")

    first, last = top.integer("first_fiscal_year"), top.integer("last_fiscal_year")
    if first > last:
        raise ConfigError(f"In {path.name}, first_fiscal_year ({first}) comes after last_fiscal_year ({last}).")

    sectors = top.texts("sectors")
    if not sectors:
        raise ConfigError(f"{path.name} names no sector. List at least one in sectors.")
    unknown = [sector for sector in sectors if sector not in load_sectors().names]
    if unknown:
        raise ConfigError(f"In {path.name}, sectors names {', '.join(unknown)}, which config/sectors.toml does not "
                          "list. Use a key from that file.")

    showcase = _Entry(path, "showcase", data.get("showcase"))
    showcase.only({"project_id", "name"})
    plan = _Entry(path, "demo_plan", data.get("demo_plan"))
    plan.only({"project_id", "project_name", "implementing_agency", "agency_short_name", "plan_date", "package",
               "smoke_question", "genie_question"})

    onboarded = []
    for entry in _tables(path, data, "onboarded"):
        entry.only({"iso2", "since"})
        country = Onboarded(entry.text("iso2"), entry.date("since"))
        if country.iso2 not in {known.iso2 for known in countries}:
            entry._fail("iso2", f"names {country.iso2}, which is not one of the [[countries]] above")
        if country.iso2 in {seen.iso2 for seen in onboarded}:
            entry._fail("iso2", f"repeats {country.iso2}. List each country once, with the day it started")
        onboarded.append(country)

    shelf = [_shelf_item(entry) for entry in _tables(path, data, "stress_shelf")]
    keys = [item.key for item in shelf]
    if len(set(keys)) != len(keys):
        raise ConfigError(f"In {path.name}, two stress_shelf entries share a key. Give each its own.")

    return Slice(
        countries=tuple(countries),
        sectors=sectors,
        first_fiscal_year=first,
        last_fiscal_year=last,
        showcase=Showcase(showcase.project_id("project_id"), showcase.text("name")),
        demo_plan=DemoPlan(plan.project_id("project_id"), plan.text("project_name"),
                           plan.text("implementing_agency"), plan.text("agency_short_name"), plan.date("plan_date"),
                           plan.text("package"), plan.text("smoke_question"), plan.text("genie_question")),
        stress_shelf=tuple(shelf),
        planned_projects=top.integer("planned_projects", required=False),
        notice_types=top.texts("notice_types"),
        onboarded=tuple(onboarded),
    )


# ── The sector file ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class Sectors:
    """Strata's one sector taxonomy: each sector's key and name, and the major sector codes of both
    of the projects API's taxonomies that map to it."""

    keys: tuple[str, ...]
    names: dict[str, str]
    codes: dict[str, str]  # a major sector code -> its sector's key

    def of(self, major_sectors) -> tuple[str | None, str | None]:
        """A project's one sector and the major sector code it came from, from the projects API's
        major_sectors. The shares add up by sector, since the older taxonomy splits a sector across
        codes (energy is LX, PX, GX and NX), and the sector with the largest total wins, ties to the
        sector listed first. Its code is the one with the largest share within it. A code no sector
        lists counts on its own. (None, None) when the project lists no major sector; (None, code)
        when an unmapped code wins."""
        shares: dict[str, float] = {}
        for entry in major_sectors or []:
            major = entry.get("major_sector", entry) if isinstance(entry, dict) else {}
            code = (major.get("major_sector_code") or "").strip()
            if code:
                shares[code] = shares.get(code, 0.0) + sum(_percent(sector.get("sector_percent"))
                                                           for sector in major.get("sectors") or [])
        if not shares:
            return None, None

        def group(code: str) -> tuple[str | None, str]:  # (its sector's key, or None and the code itself)
            return (self.codes[code], "") if code in self.codes else (None, code)

        totals: dict[tuple[str | None, str], float] = {}
        for code, share in shares.items():
            totals[group(code)] = totals.get(group(code), 0.0) + share
        order = {key: number for number, key in enumerate(self.keys)}
        best = min(totals, key=lambda found: (-totals[found], order.get(found[0], len(order)), found[1]))
        code = min((code for code in shares if group(code) == best), key=lambda code: (-shares[code], code))
        return best[0], code


def _percent(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def load_sectors(path: Path = CONFIG_DIR / "sectors.toml") -> Sectors:
    """The sector taxonomy, in file order."""
    data = _read(path)
    _Entry(path, "the file", data).only({"sector"})
    keys, names, codes = [], {}, {}
    for entry in _tables(path, data, "sector"):
        entry.only({"key", "name", "codes"})
        key = entry.text("key")
        if key in names:
            entry._fail("key", f"repeats {key!r}. Each sector is listed once")
        keys.append(key)
        names[key] = entry.text("name")
        for code in entry.texts("codes"):
            if code in codes:
                entry._fail("codes", f"lists {code}, which {codes[code]} lists too. Each code maps to one sector")
            codes[code] = key
    if not keys:
        raise ConfigError(f"{path.name} names no sector. Add at least one [[sector]] entry.")
    return Sectors(tuple(keys), names, codes)


# ── The model file ───────────────────────────────────────────────────────

ROLES = ("agent", "draft", "batch", "embed")


@dataclass(frozen=True)
class Model:
    role: str
    deployment: str
    purpose: str
    dimensions: int | None = None


def load_models(path: Path = CONFIG_DIR / "models.toml") -> dict[str, Model]:
    """The deployment each role uses, in the order of ROLES."""
    data = _read(path)
    _Entry(path, "the file", data).only({"roles", "layout", "search", "supplier_matching", "time_estimate", "what_if",
                                         "rebidding", "judge"})
    roles = data.get("roles", {})
    missing = [role for role in ROLES if role not in roles]
    unknown = sorted(set(roles) - set(ROLES))
    if missing or unknown:
        raise ConfigError(f"{path.name} must name a deployment for exactly these roles: {', '.join(ROLES)}. "
                          + (f"Missing: {', '.join(missing)}. " if missing else "")
                          + (f"Not a role: {', '.join(unknown)}." if unknown else ""))
    models = {}
    for role in ROLES:
        entry = _Entry(path, f"roles.{role}", roles[role])
        entry.only({"deployment", "purpose", "dimensions"})
        # The embedding role needs its size: the passage index and the AI Search probe build vectors of it.
        models[role] = Model(role, entry.text("deployment"), entry.text("purpose"),
                             entry.integer("dimensions", required=(role == "embed")))
    return models


def load_judge_role(path: Path = CONFIG_DIR / "models.toml") -> str:
    """The role whose deployment judges whether each sentence follows from its sources (the verifier's check 4)."""
    entry = _Entry(path, "judge", _read(path).get("judge"))
    entry.only({"role"})
    role = entry.text("role")
    if role not in ROLES:
        entry._fail("role", f"must be one of the model file's roles: {', '.join(ROLES)}")
    return role


def load_layout_parser(path: Path = CONFIG_DIR / "models.toml") -> str:
    """The name of the layout parser that reads table pages on the workspace (Route B)."""
    entry = _Entry(path, "layout", _read(path).get("layout"))
    entry.only({"parser", "rejoin_split_words"})
    return entry.text("parser")


def load_rejoin_split_words(path: Path = CONFIG_DIR / "models.toml") -> bool:
    """Whether the offline layout parser joins a word a table cell wrapped at its edge (parked decision)."""
    entry = _Entry(path, "layout", _read(path).get("layout"))
    entry.only({"parser", "rejoin_split_words"})
    return entry.boolean("rejoin_split_words") if "rejoin_split_words" in entry.table else False


@dataclass(frozen=True)
class SearchSetup:
    """One search setup (ticket 32): how the two rankings are fused, whether the reranker runs, and whether
    keyword search reads each passage's header. The model file's [search.setup] is production's; the tuning
    gate compares a candidate with it."""

    keyword_weight: float = 1.0
    vector_weight: float = 1.0
    rerank: bool = True
    rerank_depth: int = 20
    header_in_words: bool = True


@dataclass(frozen=True)
class SearchSettings:
    """How search_passages ranks on the workspace: the AI Search index and the reranker it runs, and the
    search setup production uses."""

    index: str  # the Delta Sync index over strata.gold.passage, by its three-part name
    reranker: str  # the model AI Search reranks the best hits with
    rerank_columns: tuple[str, ...]  # the columns of each passage the reranker reads
    setup: SearchSetup = SearchSetup()


def _weight(entry: _Entry, key: str) -> float:
    value = entry.table.get(key)
    if not isinstance(value, int | float) or isinstance(value, bool) or value < 0:
        entry._fail(key, "must be a number, zero or more")
    return float(value)


def load_search(path: Path = CONFIG_DIR / "models.toml") -> SearchSettings:
    """The AI Search index and the reranker search_passages uses on the workspace, and the search setup."""
    entry = _Entry(path, "search", _read(path).get("search"))
    entry.only({"index", "reranker", "rerank_columns", "setup"})
    setup = SearchSetup()
    if "setup" in entry.table:
        table = _Entry(path, "search.setup", entry.table["setup"])
        table.only({"keyword_weight", "vector_weight", "rerank", "rerank_depth", "header_in_words"})
        depth = table.integer("rerank_depth")
        if depth < 1:
            table._fail("rerank_depth", "must be 1 or more")
        setup = SearchSetup(_weight(table, "keyword_weight"), _weight(table, "vector_weight"), table.boolean("rerank"),
                            depth, table.boolean("header_in_words"))
        if setup.keyword_weight == 0 and setup.vector_weight == 0:
            table._fail("keyword_weight", "or vector_weight must be more than zero, or nothing ranks")
    index = entry.text("index")
    # catalog.build, the deploy's step 2 and the table sizes measure split it in three (ticket 87's review).
    if len(index.split(".")) != 3 or not all(index.split(".")):
        entry._fail("index", f"must be a catalog, a schema and a name, such as strata.gold.passage_index, not {index!r}")
    return SearchSettings(index, entry.text("reranker"), entry.texts("rerank_columns"), setup)


# ── The retrieval loop's lists (ticket 32) ───────────────────────────────

@dataclass(frozen=True)
class QueryKind:
    """One kind of question, which a passage report and a ranking-lower decision are about. words are the
    stemmed words (strata.knowledge.embed.terms) whose presence in a question picks it."""

    key: str
    words: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalLists:
    query_kinds: tuple[QueryKind, ...]  # in the file's order, which breaks a tie; the last has no words
    fallback: str  # the kind a question with none of the words gets


def load_retrieval(path: Path = CONFIG_DIR / "retrieval.toml") -> RetrievalLists:
    """config/retrieval.toml: the kinds of question passage reports are grouped by, each with its words, and
    the fallback kind."""
    data = _read(path)
    _Entry(path, "the file", data).only({"query_kinds", "fallback"})
    kinds = []
    for key, table in (data.get("query_kinds") or {}).items():
        entry = _Entry(path, f"query_kinds.{key}", table)
        entry.only({"words"})
        kinds.append(QueryKind(key, entry.texts("words")))
    fallback = data.get("fallback")
    if not isinstance(fallback, str) or fallback not in {kind.key for kind in kinds}:
        raise ConfigError(f"In {path.name}, fallback must name one of the query_kinds: "
                          f"{', '.join(kind.key for kind in kinds)}.")
    if not kinds:
        raise ConfigError(f"In {path.name}, list at least one kind of question under [query_kinds].")
    return RetrievalLists(tuple(kinds), fallback)


@dataclass(frozen=True)
class TimeEstimateSettings:
    """The time estimate's model (ticket 25): the model file's [time_estimate] table."""

    learner: str  # its name in LEARNERS in src/strata/estimates/time_estimate.py
    registered_model: str  # catalog.schema.model in Unity Catalog
    experiment: str  # the MLflow experiment
    test_years: tuple[int, ...]  # the rolling backtests, each tested on one calendar year
    calibration_every: int  # every this-many-th training package sizes the ranges
    governance_indicators: tuple[str, ...]  # CPIA and WGI indicator codes
    range_checked: tuple[str, ...]  # features a package must sit inside the training range of
    learner_settings: dict  # the learner's own settings, such as XGBoost's, from [time_estimate.<learner>]
    # Each governance indicator's name, by its code, as the model card writes it (ticket 63).
    governance_names: dict[str, str] = field(default_factory=dict)


def load_time_estimate(path: Path = CONFIG_DIR / "models.toml") -> TimeEstimateSettings:
    """The model file's [time_estimate] table, with its learner's settings."""
    entry = _Entry(path, "time_estimate", _read(path).get("time_estimate"))
    learner = entry.text("learner")
    entry.only({"learner", "registered_model", "experiment", "test_years", "calibration_every",
                "governance_indicators", "governance_names", "range_checked", learner})
    registered = entry.text("registered_model")
    if registered.count(".") != 2:
        entry._fail("registered_model", "must be a three-part Unity Catalog name, such as strata.gold.time_estimate")
    years = entry.table.get("test_years")
    if not isinstance(years, list) or not years or not all(isinstance(y, int) and not isinstance(y, bool) for y in years):
        entry._fail("test_years", "must be a list of years, such as [2021, 2022]")
    every = entry.integer("calibration_every")
    if every < 2:
        entry._fail("calibration_every", "must be 2 or more, so the model learns from some packages")
    settings = entry.table.get(learner, {})
    _Entry(path, f"time_estimate.{learner}", settings)
    indicators = entry.texts("governance_indicators")
    names = entry.table.get("governance_names", {})
    if not isinstance(names, dict) or any(not isinstance(names.get(code), str) or not names[code].strip()
                                          for code in indicators):
        entry._fail("governance_names", "must name every code in governance_indicators, such as "
                                        "\"GOV_WGI_GE.EST\" = \"Government Effectiveness: Estimate\"")
    return TimeEstimateSettings(learner, registered, entry.text("experiment"), tuple(sorted(years)), every,
                                indicators, entry.texts("range_checked"), dict(settings),
                                {code: names[code] for code in indicators})


@dataclass(frozen=True)
class Lever:
    """One what-if lever (ticket 26): a part of a procurement approach that "Compare with" can change."""

    key: str  # market_approach, lots or prequalification: which record gives a comparable's value
    feature: str | None  # the model's feature it sets, or None when the model reads no such feature
    values: tuple[str, ...]  # the values the score task scores, in STEP's words; empty for a lever not scored


# The levers whose comparables' values Strata can read from the records (strata.tools.estimate_time).
LEVERS = ("market_approach", "lots", "prequalification")


def load_what_if(path: Path = CONFIG_DIR / "models.toml") -> tuple[Lever, ...]:
    """The model file's [what_if] table: the levers in "Compare with"'s order."""
    entry = _Entry(path, "what_if", _read(path).get("what_if"))
    order = entry.texts("levers")
    entry.only({"levers", *order})
    found = []
    for key in order:
        if key not in LEVERS:
            entry._fail("levers", f"names {key}, which no record gives: use {', '.join(LEVERS)}")
        lever = _Entry(path, f"what_if.{key}", entry.table.get(key))
        lever.only({"feature", "values"})
        feature = lever.table.get("feature", "")
        if not isinstance(feature, str):
            lever._fail("feature", "must be the model's feature name, or empty text for none")
        values = lever.texts("values")
        if feature and not values:
            lever._fail("values", "must list the values the score task scores")
        found.append(Lever(key, feature or None, values))
    return tuple(found)


@dataclass(frozen=True)
class Level:
    """One level of a name-matching comparison: how often rows of one supplier (m) and of different
    suppliers (u) fall in it."""

    name: str
    m: float
    u: float


@dataclass(frozen=True)
class SupplierMatching:
    """The name-matching model for suppliers with no STEP supplier ID (ticket 19)."""

    judge_role: str  # the model role whose deployment decides the uncertain middle
    prior: float  # how likely two rows from one country are one supplier before their names are compared
    comparisons: dict[str, tuple[Level, ...]]  # each comparison's levels, most alike first


def load_supplier_matching(path: Path = CONFIG_DIR / "models.toml") -> SupplierMatching:
    """The model file's [supplier_matching] table. Each comparison's m values add up to 1, and so do its u
    values; the levels' names are checked against their rules by strata.knowledge.suppliers.matching."""
    entry = _Entry(path, "supplier_matching", _read(path).get("supplier_matching"))
    table = entry.table
    judge_role = entry.text("judge_role")
    if judge_role not in ROLES:
        entry._fail("judge_role", f"must be one of the model file's roles: {', '.join(ROLES)}")
    prior = table.get("prior")
    if not isinstance(prior, (int, float)) or not 0 < prior < 1:
        entry._fail("prior", "must be a number between 0 and 1")
    comparisons = {}
    for name, levels in table.items():
        if name in ("judge_role", "prior"):
            continue
        where = _Entry(path, f"supplier_matching.{name}", levels)
        read = []
        for level, values in levels.items():
            level_entry = _Entry(path, f"supplier_matching.{name}.{level}", values)
            level_entry.only({"m", "u"})
            m, u = values.get("m"), values.get("u")
            if not all(isinstance(value, (int, float)) and 0 < value < 1 for value in (m, u)):
                level_entry._fail("m", "and u must each be a number between 0 and 1")
            read.append(Level(level, float(m), float(u)))
        for column in ("m", "u"):
            total = sum(getattr(level, column) for level in read)
            if abs(total - 1) > 1e-9:
                where._fail(column, f"values must add up to 1, and they add up to {total:g}")
        comparisons[name] = tuple(read)
    if not comparisons:
        entry._fail("name", "is missing. The model needs at least one comparison")
    return SupplierMatching(judge_role, float(prior), comparisons)


# ── The thresholds file ──────────────────────────────────────────────────

@dataclass(frozen=True)
class Thresholds:
    path: Path
    values: dict

    def value(self, dotted: str):
        """One threshold, such as value("plan_check.days_before_closing")."""
        value = self.values
        for part in dotted.split("."):
            if not isinstance(value, dict) or part not in value:
                raise ConfigError(f"The thresholds file has no value for {dotted}. "
                                  f"Add it to config/thresholds.toml, with a comment that names its source.")
            value = value[part]
        return value


def load_thresholds(path: Path = CONFIG_DIR / "thresholds.toml") -> Thresholds:
    """Every threshold, read by its dotted name."""
    data = _read(path)
    for section, table in data.items():
        if not isinstance(table, dict):
            raise ConfigError(f"In {path.name}, {section} must sit under a [section] heading.")
    return Thresholds(path, data)


# ── The tool registry ────────────────────────────────────────────────────

PARAMETER_TYPES = ("string", "date", "integer", "number", "boolean")
NOT_CHECKED_WHEN = ("ran", "cited")  # when a tool's "Not checked" clause applies (config/tools.toml)
ROW_CONTRACT = ("evidence_id", "public_from", "source")  # spec, seam 2: every row carries these
ADAPTER = re.compile(r"[a-z_][a-z0-9_.]*:[a-z_][a-z0-9_]*")
TOOL_NAME = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class ToolParameter:
    name: str
    type: str
    required: bool
    description: str
    # Whether it names the record a call is about, such as find_comparables' step_reference, so the summary's
    # evidence id is keyed by it even when it is optional. A required parameter always does.
    key: bool = False


@dataclass(frozen=True)
class ToolResult:
    """The shape of what a tool returns beside the envelope every tool shares."""

    row: str
    row_fields: tuple[str, ...]
    source_fields: tuple[str, ...]
    fields: tuple[str, ...]
    reasons: tuple[str, ...] = ()  # the codes a reason in a row's marks may have
    abstentions: tuple[str, ...] = ()  # the reasons the tool may give for returning no rows
    abstentions_with_rows: tuple[str, ...] = ()  # the abstentions that still come with rows
    summary_fields: tuple[str, ...] = ()  # the derived figures returned as one citable record, the summary
    nested_rows: tuple[str, ...] = ()  # the row fields whose items are citable records of their own
    # Its rows are lessons or comparable packages, so a sentence of kind advice may rest on them (the
    # verifier's check 5: no advice without a lesson or a comparable among its evidence).
    backs_advice: bool = False
    # When the check line's "Not checked" clause for the tool applies: "ran", or "cited" once a sentence on screen
    # cites its evidence (ticket 24).
    not_checked_when: str = "ran"


@dataclass(frozen=True)
class ToolReadiness:
    """The kind of question a tool answers, as the Data readiness page's "What you can ask" shows it:
    its words are copy.ts's dataReadiness.kinds[kind], the number in its "Ready for" cell is
    ready_for_measure in the readiness row ready_for_row, and what holds it back comes from the rows
    it draws on (config/sources.toml, [[sources.<key>.readiness]]). ready_for_counted_in is the
    table that measure counts, when no column or check of its row shows it and so names it."""

    kind: str
    ready_for_row: str
    ready_for_measure: str
    draws_on: tuple[str, ...]
    ready_for_counted_in: str | None = None
    # The key in config/thresholds.toml of the day the tool's records start, when it reads only records from a
    # period: a known gap that ended before that day holds none of its answers back (ticket 63).
    period_from: str | None = None


@dataclass(frozen=True)
class Tool:
    """One tool, defined once: what it does, what it takes, what runs it and what it returns."""

    name: str
    description: str
    adapter: str
    benchmark: str
    sources: tuple[str, ...]
    parameters: tuple[ToolParameter, ...]
    result: ToolResult
    readiness: ToolReadiness | None = None
    # The longest of its results the agent gets whole, in characters of JSON, in place of the thresholds file's
    # agent.max_tool_output_chars; a longer one goes trimmed (strata.agent.loop.call_output, ticket 117). None: that one.
    max_output_chars: int | None = None

    def parameter(self, name: str) -> ToolParameter:
        found = [parameter for parameter in self.parameters if parameter.name == name]
        if not found:
            raise ConfigError(f"The tool {self.name} has no parameter {name}.")
        return found[0]


def load_tools(path: Path = CONFIG_DIR / "tools.toml") -> dict[str, Tool]:
    """Every tool in the registry, by name, in the file's order."""
    data = _read(path)
    _Entry(path, "the file", data).only({"tools"})
    tools = {}
    for name, table in data.get("tools", {}).items():
        if not TOOL_NAME.fullmatch(name):
            raise ConfigError(f"In {path.name}, the tool name {name!r} must be lower case letters, digits and _.")
        entry = _Entry(path, f"tools.{name}", table)
        parameters, result = _tool_parameters(path, name, table), _tool_result(path, name, table)
        entry.only({"description", "adapter", "benchmark", "sources", "parameters", "result", "readiness",
                    "max_output_chars"})
        adapter = entry.text("adapter")
        if not ADAPTER.fullmatch(adapter):
            entry._fail("adapter", f"must name a function as module:function, such as strata.tools.{name}:{name}")
        longest = entry.integer("max_output_chars", required=False)
        if longest is not None and longest < 1:
            entry._fail("max_output_chars", "must be a whole number of characters above 0")
        tools[name] = Tool(name=name, description=entry.text("description"), adapter=adapter,
                           benchmark=entry.text("benchmark"), sources=entry.texts("sources"),
                           parameters=parameters, result=result, readiness=_tool_readiness(path, name, table),
                           max_output_chars=longest)
    return tools


def _tool_readiness(path: Path, name: str, table: dict) -> ToolReadiness | None:
    if "readiness" not in table:
        return None
    entry = _Entry(path, f"tools.{name}.readiness", table["readiness"])
    entry.only({"kind", "ready_for", "draws_on", "period_from"})
    ready_for = _Entry(path, f"tools.{name}.readiness.ready_for", entry.table.get("ready_for"))
    ready_for.only({"row", "measure", "counted_in"})
    draws_on = entry.texts("draws_on")
    if ready_for.text("row") not in draws_on:
        ready_for._fail("row", "must be one of the rows in draws_on")
    return ToolReadiness(entry.text("kind"), ready_for.text("row"), ready_for.text("measure"), draws_on,
                         ready_for.text("counted_in", required=False), entry.text("period_from", required=False))


def _tool_parameters(path: Path, name: str, table: dict) -> tuple[ToolParameter, ...]:
    parameters = []
    for entry in _tables(path, table, "parameters"):
        entry.where = f"tools.{name}.{entry.where}"
        entry.only({"name", "type", "required", "description", "key"})
        parameter = ToolParameter(entry.text("name"), entry.text("type"), entry.boolean("required"),
                                  entry.text("description"), bool(entry.table.get("key", False)))
        if parameter.type not in PARAMETER_TYPES:
            entry._fail("type", f"must be one of {', '.join(PARAMETER_TYPES)}")
        parameters.append(parameter)
    names = [parameter.name for parameter in parameters]
    if len(set(names)) != len(names):
        raise ConfigError(f"In {path.name}, tools.{name} names a parameter twice.")
    as_of = [parameter for parameter in parameters if parameter.name == "as_of"]
    if not as_of or as_of[0].type != "date" or as_of[0].required:
        raise ConfigError(f"In {path.name}, tools.{name} needs an optional as_of parameter of type date, because "
                          f"every tool can answer as of a past date (ADR 0002). Add a [[tools.{name}.parameters]] "
                          f'table with name = "as_of", type = "date" and required = false.')
    return tuple(parameters)


def _tool_result(path: Path, name: str, table: dict) -> ToolResult:
    if "result" not in table:
        raise ConfigError(f"In {path.name}, tools.{name} has no result shape. Add a [tools.{name}.result] table "
                          f"with row, row_fields, source_fields and fields.")
    entry = _Entry(path, f"tools.{name}.result", table["result"])
    entry.only({"row", "row_fields", "source_fields", "fields", "reasons", "abstentions", "abstentions_with_rows",
                "summary_fields", "nested_rows", "backs_advice", "not_checked_when"})
    not_checked_when = entry.table.get("not_checked_when", "ran")
    if not_checked_when not in NOT_CHECKED_WHEN:
        entry._fail("not_checked_when", f"must be one of {', '.join(NOT_CHECKED_WHEN)}")
    result = ToolResult(entry.text("row"), entry.texts("row_fields"), entry.texts("source_fields"),
                        entry.texts("fields"), entry.texts("reasons"), entry.texts("abstentions"),
                        entry.texts("abstentions_with_rows"), entry.texts("summary_fields"), entry.texts("nested_rows"),
                        bool(entry.table.get("backs_advice", False)), not_checked_when)
    # A summary carries the tool's own fields, and the coverage line's counts, which every result has.
    strays = [field for field in result.summary_fields if field not in (*result.fields, "coverage")]
    if strays:
        entry._fail("summary_fields", f"names {', '.join(strays)}, which fields does not list")
    strays = [field for field in result.nested_rows if field not in result.row_fields]
    if strays:
        entry._fail("nested_rows", f"names {', '.join(strays)}, which row_fields does not list")
    unlisted = [reason for reason in result.abstentions_with_rows if reason not in result.abstentions]
    if unlisted:
        entry._fail("abstentions_with_rows", f"names {', '.join(unlisted)}, which abstentions does not list")
    missing = [field for field in ROW_CONTRACT if field not in result.row_fields]
    if missing:
        entry._fail("row_fields", f"must include {', '.join(ROW_CONTRACT)}, so every row can be cited and dated; "
                                  f"it lacks {', '.join(missing)}")
    if not result.source_fields:
        entry._fail("source_fields", "must name the fields of each row's source line")
    return result


# ── The agent registry ───────────────────────────────────────────────────

SEVERITIES = ("Low", "Medium", "High")


@dataclass(frozen=True)
class Guardrail:
    """The content filters and Prompt Shields an agent runs under, kept as an RAI policy in Azure."""

    key: str
    name: str
    base_policy: str
    severity: str
    prompt_shields: bool


@dataclass(frozen=True)
class AgentSpec:
    """One Foundry prompt agent: its name, the model role it runs on, its instructions file and guardrail,
    and the Foundry API versions the app calls it with."""

    key: str
    name: str
    role: str
    instructions: str
    description: str
    guardrail: Guardrail
    api_version: str
    rai_policy_api_version: str
    # The tools it may call, by their names in the tool registry, or None for every tool. A writer
    # that writes from facts the app hands it, such as the review notes writer, has none.
    tools: tuple[str, ...] | None = None


def load_agent(key: str, path: Path = CONFIG_DIR / "agents.toml") -> AgentSpec:
    """One agent of the agent registry, with its guardrail and the Foundry API versions."""
    data = _read(path)
    _Entry(path, "the file", data).only({"agents", "guardrails", "foundry"})
    agents, guardrails = data.get("agents", {}), data.get("guardrails", {})
    if key not in agents:
        raise ConfigError(f"{path.name} has no agent {key}. It has {', '.join(agents) or 'none'}.")
    entry = _Entry(path, f"agents.{key}", agents[key])
    entry.only({"name", "role", "instructions", "guardrail", "description", "tools"})
    role = entry.text("role")
    tools = entry.texts("tools") if "tools" in entry.table else None
    if role not in ROLES:
        entry._fail("role", f"must be one of the model file's roles: {', '.join(ROLES)}")
    rail_key = entry.text("guardrail")
    if rail_key not in guardrails:
        entry._fail("guardrail", f"names {rail_key}, which [guardrails] does not define")
    rail = _Entry(path, f"guardrails.{rail_key}", guardrails[rail_key])
    rail.only({"name", "base_policy", "severity", "prompt_shields"})
    if rail.text("severity") not in SEVERITIES:
        rail._fail("severity", f"must be one of {', '.join(SEVERITIES)}")
    foundry = _Entry(path, "foundry", data.get("foundry"))
    foundry.only({"api_version", "rai_policy_api_version"})
    return AgentSpec(key, entry.text("name"), role, entry.text("instructions"), entry.text("description"),
                     Guardrail(rail_key, rail.text("name"), rail.text("base_policy"), rail.text("severity"),
                               rail.boolean("prompt_shields")),
                     foundry.text("api_version"), foundry.text("rai_policy_api_version"), tools)


# ── The draft-kind registry ──────────────────────────────────────────────

REMOVED_BOXES = ("always", "when_removed")
EXPORTS = ("word", "step_rows")
FUNCTION = re.compile(r"[a-z_][a-z0-9_.]*:[a-z_][a-z0-9_]*")
MODULE = re.compile(r"[a-z_][a-z0-9_]*(?:\.[a-z_][a-z0-9_]*)+")


@dataclass(frozen=True)
class Hold:
    """Something that keeps a draft from export until it lifts, with the words that say what lifts it."""

    key: str
    test: str  # module:function, given the draft's state and the view
    copy: str  # the hold line's key under copy.draft.bar.hold
    capability: str  # what a refused export names (the 40 brief, section 5.1)


@dataclass(frozen=True)
class DraftKind:
    """One kind of draft: the workflow that writes it, its page's columns and lists, its holds and files."""

    key: str
    writer: str  # the workflow module
    agent: str  # its writer in config/agents.toml
    word: str  # module:function that lays out its Word file
    export: str
    csv: tuple[str, ...]
    columns: tuple[str, ...]
    holds: tuple[str, ...]
    sources_list: bool
    removed_box: str
    not_checked: tuple[str, ...]
    files: str
    # Only viewers with the World Bank staff role may start one (ticket 37's mission brief).
    staff_only: bool = False
    # Ticket 39: the values of the sentence that names a row ("Row 1, Cost estimates below market rates."), and the
    # writer that rewrites one row from a lesson's current version, each as module:function, or None.
    row_label: str | None = None
    rewrite_row: str | None = None
    # Only implementing agency officers may start one, for their own agency (ticket 38), and every draft of the kind
    # is Official Use Only. Its words are the agency's (copy.draft.kinds.<kind>).
    agency_only: bool = False


@dataclass(frozen=True)
class DraftKinds:
    kinds: dict[str, DraftKind]
    holds: dict[str, Hold]
    # Whether the draft page shows disagreement cards, so a warning card holds export ([disagreements]).
    cards_on_drafts: bool = False


def load_draft_kinds(path: Path = CONFIG_DIR / "drafts.toml") -> DraftKinds:
    """The draft-kind registry, with every hold a kind names defined below it."""
    data = _read(path)
    _Entry(path, "the file", data).only({"kinds", "holds", "disagreements"})
    cards = _Entry(path, "disagreements", data.get("disagreements", {"cards_on_drafts": False}))
    cards.only({"cards_on_drafts"})
    holds = {}
    for key, table in (data.get("holds") or {}).items():
        entry = _Entry(path, f"holds.{key}", table)
        entry.only({"test", "copy", "capability"})
        if not FUNCTION.fullmatch(entry.text("test")):
            entry._fail("test", "must name a function as module:function")
        holds[key] = Hold(key, entry.text("test"), entry.text("copy"), entry.text("capability"))
    kinds = {}
    for key, table in (data.get("kinds") or {}).items():
        entry = _Entry(path, f"kinds.{key}", table)
        entry.only({"writer", "agent", "word", "export", "csv", "columns", "holds", "sources_list", "removed_box",
                    "not_checked", "files", "staff_only", "agency_only", "row_label", "rewrite_row"})
        if not MODULE.fullmatch(entry.text("writer")):
            entry._fail("writer", "must name a module, such as strata.drafts.review_notes")
        if entry.text("export") not in EXPORTS:
            entry._fail("export", f"must be one of {', '.join(EXPORTS)}")
        # A kind exported to Word names the function that lays out its file; a kind whose file is STEP rows names
        # the CSV writer under csv instead (ticket 38).
        word = entry.text("word", required=entry.text("export") == "word") or ""
        if word and not FUNCTION.fullmatch(word):
            entry._fail("word", "must name a function as module:function")
        if entry.text("export") == "step_rows" and not entry.texts("csv"):
            entry._fail("csv", "must name the STEP rows writer for a kind exported as STEP rows")
        if not all(FUNCTION.fullmatch(name) for name in entry.texts("csv")):
            entry._fail("csv", "must list functions as module:function")
        for name in ("row_label", "rewrite_row"):
            if name in table and not FUNCTION.fullmatch(entry.text(name)):
                entry._fail(name, "must name a function as module:function")
        unknown = [hold for hold in entry.texts("holds") if hold not in holds]
        if unknown:
            entry._fail("holds", f"names {', '.join(unknown)}, which [holds] does not define")
        if entry.text("removed_box") not in REMOVED_BOXES:
            entry._fail("removed_box", f"must be one of {', '.join(REMOVED_BOXES)}")
        if not entry.texts("columns"):
            entry._fail("columns", "must name at least one column")
        # A kind with no agent is worked out by its module alone, with no model call, and still checked by the
        # verifier (ticket 38's planned dates).
        kinds[key] = DraftKind(key, entry.text("writer"), entry.text("agent", required=False) or "", word,
                               entry.text("export"), entry.texts("csv"), entry.texts("columns"), entry.texts("holds"),
                               entry.boolean("sources_list"), entry.text("removed_box"), entry.texts("not_checked"),
                               entry.text("files"), entry.boolean("staff_only") if "staff_only" in table else False,
                               row_label=entry.text("row_label") if "row_label" in table else None,
                               rewrite_row=entry.text("rewrite_row") if "rewrite_row" in table else None,
                               agency_only=entry.boolean("agency_only") if "agency_only" in table else False)
    if not kinds:
        raise ConfigError(f"{path.name} defines no draft kind. Add a [kinds.<key>] table.")
    return DraftKinds(kinds, holds, cards.boolean("cards_on_drafts"))


# ── The PPSD template registry ───────────────────────────────────────────

PPSD_FILLERS = ("strata", "people")
PPSD_CONTROLS = ("text", "rating", "score", "stage")
PPSD_HOLDS = ("owners", "ratings")


@dataclass(frozen=True)
class PpsdColumn:
    """One column of the PPSD risk table, as its template heads it, and who fills it."""

    key: str
    header: str
    value: str  # its entry in tests/ground_truth/values.toml
    filled_by: str  # strata or people
    letter: str | None = None
    control: str | None = None  # for a column people fill
    hold: str | None = None  # the export hold it counts toward
    max_length: int | None = None


@dataclass(frozen=True)
class PpsdForm:
    key: str
    name: str
    document: str
    pdf_page: int
    columns: tuple[PpsdColumn, ...]

    def column(self, key: str) -> PpsdColumn | None:
        return next((column for column in self.columns if column.key == key), None)


@dataclass(frozen=True)
class PpsdRating:
    value: int
    label: str
    short: str


@dataclass(frozen=True)
class PpsdScore:
    definition: str
    minimum: int
    maximum: int


@dataclass(frozen=True)
class PpsdTemplates:
    """The Short Form and Long Form risk tables, the guidance's ratings and stages, and the default form."""

    path: Path
    default_form: str
    forms: dict[str, PpsdForm]
    ratings: tuple[PpsdRating, ...]
    score: PpsdScore
    stages: tuple[str, ...]

    def people_column(self, key: str) -> PpsdColumn | None:
        """A column only a person fills, from whichever form has it."""
        return next((column for form in self.forms.values() for column in form.columns
                     if column.key == key and column.filled_by == "people"), None)


def load_ppsd_templates(path: Path = CONFIG_DIR / "ppsd_templates.toml") -> PpsdTemplates:
    """The PPSD template registry (config/ppsd_templates.toml)."""
    data = _read(path)
    _Entry(path, "the file", data).only({"default_form", "forms", "ratings", "score", "stages"})
    forms = {}
    for key, table in (data.get("forms") or {}).items():
        entry = _Entry(path, f"forms.{key}", table)
        entry.only({"name", "document", "pdf_page", "columns"})
        columns = []
        for column in _tables(path, table, "columns"):
            column.where = f"forms.{key}.{column.where}"
            column.only({"key", "header", "value", "letter", "filled_by", "control", "hold", "max_length"})
            filled = column.text("filled_by")
            if filled not in PPSD_FILLERS:
                column._fail("filled_by", f"must be one of {', '.join(PPSD_FILLERS)}")
            control, hold = column.text("control", filled == "people"), column.text("hold", False)
            if filled == "people" and control not in PPSD_CONTROLS:
                column._fail("control", f"must be one of {', '.join(PPSD_CONTROLS)}")
            if filled == "strata" and (control or hold):
                column._fail("control", "is only for a column people fill")
            if hold is not None and hold not in PPSD_HOLDS:
                column._fail("hold", f"must be one of {', '.join(PPSD_HOLDS)}")
            columns.append(PpsdColumn(column.text("key"), column.text("header"), column.text("value"), filled,
                                      column.text("letter", False), control, hold, column.integer("max_length", False)))
        if not columns:
            entry._fail("columns", "must list the template's columns")
        forms[key] = PpsdForm(key, entry.text("name"), entry.text("document"), entry.integer("pdf_page"), tuple(columns))
    default = _Entry(path, "the file", data).text("default_form")
    if default not in forms:
        raise ConfigError(f"In {path.name}, default_form names {default}, which [forms] does not define.")
    ratings = _Entry(path, "ratings", data.get("ratings"))
    ratings.only({"document", "pdf_page", "levels"})
    levels = tuple(PpsdRating(level["value"], level["label"], level["short"]) for level in ratings.table.get("levels", []))
    if not levels:
        ratings._fail("levels", "must list the guidance's ratings")
    score = _Entry(path, "score", data.get("score"))
    score.only({"definition", "minimum", "maximum"})
    stages = _Entry(path, "stages", data.get("stages"))
    stages.only({"document", "pdf_page", "names"})
    return PpsdTemplates(path, default, forms, levels,
                         PpsdScore(score.text("definition"), score.integer("minimum"), score.integer("maximum")),
                         stages.texts("names"))


# ── The roles file ───────────────────────────────────────────────────────

# The reviewer pages a group's members may open, and what they may do there. Later tickets add theirs.
# Ticket 32 adds Lessons > Passage reports (passage_reports), where passage reviewers decide on reports, and
# Lessons > Judging (judging), where query judges grade the labeled set; each page is its own act.
ROLE_PAGES = ("lesson_review", "passage_reports", "judging")
ROLE_ACTS = ("recommend", "decide", "cross_check")


@dataclass(frozen=True)
class Group:
    """One workspace group and what its members may do in Strata."""

    key: str
    workspace_group: str
    role: str  # what its members are called on reviewer pages
    pages: tuple[str, ...]
    acts: tuple[str, ...]


@dataclass(frozen=True)
class Person:
    """One person in the roles file, found by the email the Databricks App forwards."""

    email: str
    name: str
    groups: tuple[str, ...]
    regions: tuple[str, ...]
    projects: tuple[str, ...]
    # The user id the Databricks App forwards for them, which the seed command sets the examples up under (ticket 41).
    user_id: str | None = None

    def acts(self, roles: Roles) -> tuple[str, ...]:
        """Everything this person may do, from every group they are in, in ROLE_ACTS's order."""
        held = {act for key in self.groups for act in roles.groups[key].acts}
        return tuple(act for act in ROLE_ACTS if act in held)

    def pages(self, roles: Roles) -> tuple[str, ...]:
        """The reviewer pages this person may open, in ROLE_PAGES's order."""
        held = {page for key in self.groups for page in roles.groups[key].pages}
        return tuple(page for page in ROLE_PAGES if page in held)

    def role(self, roles: Roles) -> str:
        """The role a reviewer page names them by: the role of their group that may do the most."""
        groups = sorted((roles.groups[key] for key in self.groups), key=lambda group: -len(group.acts))
        return groups[0].role


@dataclass(frozen=True)
class Team:
    """A team that shares its drafts, by the workspace groups its members are in. A team that names an implementing
    agency is that agency's team (ticket 38): its members are implementing agency officers, who upload their plans and
    draft for their own agency, and everything the team makes is Official Use Only."""

    key: str
    name: str
    groups: tuple[str, ...]
    agency: str | None = None  # the implementing agency, as the projects API's records name it
    # The language its members get answers and drafts in when they have chosen none (ticket 42), or None for English.
    working_language: str | None = None


@dataclass(frozen=True)
class Roles:
    teams: tuple[Team, ...]
    groups: dict[str, Group]
    people: tuple[Person, ...]
    # The workspace groups whose members have the World Bank staff role (ticket 37): they may open Following and
    # follow projects. A roles file with no [staff] section names no one.
    staff: tuple[str, ...] = ()
    # The groups whose members sign off a challenger model, by role: model_owner and lead (ticket 44). A roles file
    # with no [model_sign_off] section names no one, so no challenger can be promoted.
    model_sign_off: dict[str, str] = field(default_factory=dict)

    def signs_off_as(self, email: str | None, role: str) -> bool:
        """Whether this person may sign off a challenger in this role: they are in the role's group."""
        person, group = self.person(email), self.model_sign_off.get(role)
        return person is not None and group is not None and group in person.groups

    def person(self, email: str | None) -> Person | None:
        """The person with this email, ignoring case, or None for anyone the file does not list."""
        if not email:
            return None
        wanted = email.strip().lower()
        return next((person for person in self.people if person.email.lower() == wanted), None)


def load_roles(path: Path = CONFIG_DIR / "roles.toml") -> Roles:
    """The roles file's teams, in the file's order, each with at least one workspace group, then its reviewer
    groups and the people in them."""
    data = _read(path)
    # The [views] section (ticket 40) is load_views()'s, read from the same file.
    _Entry(path, "the file", data).only({"teams", "groups", "people", "staff", "model_sign_off", "views"})
    staff: tuple[str, ...] = ()
    if "staff" in data:
        entry = _Entry(path, "staff", data["staff"])
        entry.only({"groups"})
        staff = entry.texts("groups")
        if not staff:
            entry._fail("groups", "must name at least one workspace group")
    teams = []
    for key, table in (data.get("teams") or {}).items():
        entry = _Entry(path, f"teams.{key}", table)
        entry.only({"name", "groups", "agency", "working_language"})
        if not entry.texts("groups"):
            entry._fail("groups", "must name at least one workspace group")
        working = entry.text("working_language", required=False)
        if working is not None and working not in {language.code for language in load_languages().working}:
            entry._fail("working_language", f"names {working!r}, which is not a working language in "
                                            "config/languages.toml")
        teams.append(Team(key, entry.text("name"), entry.texts("groups"), entry.text("agency", required=False),
                          working))
    groups = {}
    for key, table in (data.get("groups") or {}).items():
        entry = _Entry(path, f"groups.{key}", table)
        entry.only({"workspace_group", "role", "pages", "acts"})
        pages, acts = entry.texts("pages"), entry.texts("acts")
        for name, given, allowed in (("pages", pages, ROLE_PAGES), ("acts", acts, ROLE_ACTS)):
            unknown = [item for item in given if item not in allowed]
            if unknown:
                entry._fail(name, f"names {', '.join(unknown)}, which Strata does not know. Use only these: "
                                  f"{', '.join(allowed)}")
        groups[key] = Group(key, entry.text("workspace_group"), entry.text("role"), pages, acts)
    people, seen = [], set()
    for entry in _tables(path, data, "people"):
        entry.only({"email", "name", "groups", "regions", "projects", "user_id"})
        email = entry.text("email")
        if email.lower() in seen:
            raise ConfigError(f"In {path.name}, {email} is listed more than once. List each person once, with "
                              "all their groups.")
        seen.add(email.lower())
        named = entry.texts("groups")
        if not named:
            entry._fail("groups", "must name at least one group")
        for key in named:
            if key not in groups:
                entry._fail("groups", f"names the group {key}, which [groups] does not define. It defines "
                                      f"{', '.join(groups) or 'none'}")
        regions = entry.texts("regions")
        # A lesson reviewer reviews the lessons of their regions. A query judge or a passage reviewer works on
        # every region's passages, so needs none.
        if not regions and any("lesson_review" in groups[key].pages for key in named):
            entry._fail("regions", "must name at least one region, as strata.gold.project.region writes it")
        projects = entry.texts("projects")
        for project in projects:
            if not PROJECT_ID.fullmatch(project):
                entry._fail("projects", f"must be a project ID, P followed by six digits, not {project!r}")
        people.append(Person(email, entry.text("name"), named, regions, projects, entry.text("user_id", required=False)))
    sign_off = {}
    if "model_sign_off" in data:
        entry = _Entry(path, "model_sign_off", data["model_sign_off"])
        entry.only({"model_owner", "lead"})
        for role in ("model_owner", "lead"):
            key = entry.text(role)
            if key not in groups:
                entry._fail(role, f"names the group {key}, which [groups] does not define")
            sign_off[role] = key
        if sign_off["model_owner"] == sign_off["lead"]:
            entry._fail("lead", "names the model owner's group. The lead co-signs, so name another group")
    return Roles(tuple(teams), groups, tuple(people), staff, sign_off)


# ── The view switch: the roles file's [views] (ticket 40) ────────────────

VIEW_KEYS = ("staff", "piu", "public")  # World Bank staff, an implementing agency officer, the public
CAPABILITY_KINDS = ("read", "setting", "record", "check", "export", "draft")
ACT_KINDS = ("record", "check", "export", "draft")  # what a preview never keeps
TAB_KEYS = ("packages", "projects", "lessons", "drafts", "data")
WRITE_METHODS = ("POST", "PUT", "PATCH", "DELETE")


@dataclass(frozen=True)
class ViewRule:
    """One view: the navy bar's tabs in it, and the app's pages it does not show (by their web/src/routes.ts key)."""

    key: str
    tabs: tuple[str, ...]
    hidden: tuple[str, ...]


@dataclass(frozen=True)
class Capability:
    """Something a person may read or do, its kind, whether each view has it, whether it is private to a team, and for
    an act, the copy key of the sentence a preview gives and whether a preview leaves it out quietly."""

    key: str
    kind: str
    values: dict[str, bool]
    private: bool = False
    reason: str | None = None
    quiet: bool = False

    @property
    def act(self) -> bool:
        return self.kind in ACT_KINDS


@dataclass(frozen=True)
class RouteRule:
    """The capability a route needs: one for the route, or one per value of a path parameter (param)."""

    capability: str | None = None
    param: str | None = None
    by_value: dict[str, str] = field(default_factory=dict)

    def needs(self, path_params: dict) -> str | None:
        if self.param is None:
            return self.capability
        return self.by_value.get(str(path_params.get(self.param, "")))

    def capabilities(self) -> tuple[str, ...]:
        return (self.capability,) if self.param is None else tuple(self.by_value.values())


@dataclass(frozen=True)
class Views:
    views: dict[str, ViewRule]
    capabilities: dict[str, Capability]
    routes: dict[str, RouteRule]  # by "METHOD path", as the server declares the route
    preview_agency: str
    preview_agency_short: str | None = None

    def route(self, method: str, path: str) -> RouteRule | None:
        return self.routes.get(f"{method.upper()} {path}")

    def allows(self, view: str, capability: str) -> bool:
        """Whether the view has the capability. A tool or route asks this, so no view's rule is written anywhere else."""
        return self.capabilities[capability].values[view]


def load_views(path: Path = CONFIG_DIR / "roles.toml") -> Views:
    """The roles file's [views] section: each view's tabs and hidden pages, every capability with its kind and its value
    in each view, the routes that need one, and the implementing agency the agency preview shows."""
    data = _read(path)
    section = _Entry(path, "views", data.get("views"))
    section.only({"preview_agency", "preview_agency_short", "capabilities", "routes", *VIEW_KEYS})
    views = {}
    for key in VIEW_KEYS:
        entry = _Entry(path, f"views.{key}", section.table.get(key))
        entry.only({"tabs", "hidden"})
        tabs = entry.texts("tabs")
        unknown = [tab for tab in tabs if tab not in TAB_KEYS]
        if unknown or not tabs:
            entry._fail("tabs", f"must name tabs from {', '.join(TAB_KEYS)}")
        views[key] = ViewRule(key, tabs, entry.texts("hidden"))
    capabilities = {}
    for key, table in (_Entry(path, "views.capabilities", section.table.get("capabilities")).table).items():
        entry = _Entry(path, f"views.capabilities.{key}", table)
        entry.only({"kind", "private", "reason", "quiet", *VIEW_KEYS})
        kind = entry.text("kind")
        if kind not in CAPABILITY_KINDS:
            entry._fail("kind", f"must be one of {', '.join(CAPABILITY_KINDS)}")
        reason = entry.text("reason", required=False)
        if kind in ACT_KINDS and not reason:
            entry._fail("reason", "is missing: an act names the copy key of the sentence a preview gives")
        capabilities[key] = Capability(key, kind, {view: entry.boolean(view) for view in VIEW_KEYS},
                                       bool(table.get("private", False)), reason, bool(table.get("quiet", False)))
    routes = {}
    for route, value in (_Entry(path, "views.routes", section.table.get("routes")).table).items():
        method, _, address = route.partition(" ")
        if method not in ("GET", *WRITE_METHODS) or not address.startswith("/api/"):
            raise ConfigError(f"In {path.name}, views.routes names {route!r}. Write a method and a path, such as "
                              "\"POST /api/drafts\".")
        if isinstance(value, str):
            rule = RouteRule(value)
        else:
            entry = _Entry(path, f"views.routes.{route!r}", value)
            rule = RouteRule(param=entry.text("param"),
                             by_value={name: capability for name, capability in value.items() if name != "param"})
        for capability in rule.capabilities():
            if capability not in capabilities:
                raise ConfigError(f"In {path.name}, views.routes.{route!r} names the capability {capability!r}, which "
                                  "views.capabilities does not list.")
        routes[route] = rule
    short = section.text("preview_agency_short", required=False)
    return Views(views, capabilities, routes, section.text("preview_agency"), short or None)


# ── The evidence ladder ──────────────────────────────────────────────────

CLASSES = ("judgment", "moment")  # an outcome judgment, or a claim about one moment
KINDS = ("rating", "date", "amount")
TIES = ("tieSpecific", "tieRecent")  # the more specific source, then the more recent one
# The forms an assertion takes, as the readers in strata.knowledge.assertions write them: a rating in its
# own field, a rating or account told in running text, a record of the signed contract in an awards
# dataset, a Contract Award notice, and a package's row in a Procurement Plan.
FORMS = ("rating_field", "narrative", "contract_record", "award_notice", "plan_row")
SIDES = ("satisfactory", "unsatisfactory")


@dataclass(frozen=True)
class LadderRule:
    """One rule of the ladder. A tier rule ranks the sides by their evidence tier, in the order of tiers.
    A moment rule leans on the side made at the moment it describes: a side of a tier in at_the_moment,
    or one made within its own period."""

    id: str
    applies_to: str
    tiers: tuple[str, ...] = ()
    at_the_moment: tuple[str, ...] = ()


@dataclass(frozen=True)
class Tier:
    """An evidence tier: the document types whose reports are in it. Its "written when" words are in the
    screens' copy file (web/src/copy.ts, disagreement.written)."""

    key: str
    document_types: tuple[str, ...]


@dataclass(frozen=True)
class Attribute:
    key: str
    kind: str  # rating, date or amount
    class_: str  # judgment or moment
    scale: str | None
    names: tuple[str, ...]


@dataclass(frozen=True)
class Scale:
    key: str
    satisfactory: tuple[str, ...] = ()
    unsatisfactory: tuple[str, ...] = ()
    values: tuple[str, ...] = ()  # a scale with no sides, such as risk

    @property
    def ratings(self) -> tuple[str, ...]:
        return self.satisfactory + self.unsatisfactory + self.values


@dataclass(frozen=True)
class Ladder:
    path: Path
    rules: tuple[LadderRule, ...]
    ties: tuple[str, ...]
    specificity: tuple[tuple[str, ...], ...]  # forms, most specific group first
    tiers: dict[str, Tier]
    attributes: dict[str, Attribute]
    scales: dict[str, Scale]
    no_rating: tuple[str, ...]

    def tier_of(self, document_type: str | None) -> str | None:
        """The evidence tier of a report by its document type, or None for a type the ladder does not rank."""
        return next((tier.key for tier in self.tiers.values() if document_type in tier.document_types), None)

    def attribute(self, key: str) -> Attribute:
        if key not in self.attributes:
            raise ConfigError(f"The evidence ladder has no attribute {key}. Add it to config/evidence_ladder.toml.")
        return self.attributes[key]

    def attribute_named(self, name: str) -> Attribute | None:
        """The attribute a report's or a record's field name means, word for word, or None."""
        return next((attribute for attribute in self.attributes.values() if name in attribute.names), None)

    def rule_for(self, attribute: str) -> LadderRule | None:
        """The first rule that applies to the attribute's class."""
        return next((rule for rule in self.rules if rule.applies_to == self.attribute(attribute).class_), None)

    def rating(self, attribute: str, value: str | None) -> str | None:
        """The value as its scale writes it (case aside), or None when it is no rating or not on the scale."""
        scale = self.scales.get(self.attribute(attribute).scale or "")
        text = (value or "").strip()
        if scale is None or not text or text in self.no_rating:
            return None
        return next((rating for rating in scale.ratings if rating.lower() == text.lower()), None)

    def side(self, attribute: str, rating: str | None) -> str | None:
        """Which side of the line a rating falls on: satisfactory, unsatisfactory, or None for a scale with no sides."""
        scale = self.scales.get(self.attribute(attribute).scale or "")
        if scale is None or rating is None:
            return None
        return "satisfactory" if rating in scale.satisfactory else "unsatisfactory" if rating in scale.unsatisfactory \
            else None

    def specificity_of(self, form: str) -> int:
        """The place of a form's group in the specificity order: 0 is the most specific."""
        return next(at for at, group in enumerate(self.specificity) if form in group)


def _ladder_rule(path: Path, entry: _Entry, tiers: dict) -> LadderRule:
    entry.only({"id", "applies_to", "tiers", "at_the_moment"})
    applies_to = entry.text("applies_to")
    if applies_to not in CLASSES:
        entry._fail("applies_to", f"must be {' or '.join(CLASSES)}")
    ranked, at_the_moment = entry.texts("tiers"), entry.texts("at_the_moment")
    if bool(ranked) == bool(at_the_moment):
        raise ConfigError(f"In {path.name}, {entry.where} needs either tiers (an order of evidence tiers) or "
                          f"at_the_moment (the tiers whose sources are records made at the moment), not both.")
    for key in ("tiers", "at_the_moment"):
        named = entry.texts(key)
        unknown = [tier for tier in named if tier not in tiers]
        if unknown:
            entry._fail(key, f"names {', '.join(unknown)}, which [tiers] does not define")
        if len(set(named)) != len(named):
            entry._fail(key, "names a tier twice")
    return LadderRule(entry.text("id"), applies_to, ranked, at_the_moment)


def load_ladder(path: Path = CONFIG_DIR / "evidence_ladder.toml") -> Ladder:
    """The evidence ladder: its rules in order, its ties, the evidence tiers, the attributes an assertion can
    be about and their rating scales."""
    data = _read(path)
    _Entry(path, "the file", data).only({"rules", "ties", "tiers", "attributes", "scales"})
    tiers = {}
    for key, table in (data.get("tiers") or {}).items():
        entry = _Entry(path, f"tiers.{key}", table)
        entry.only({"document_types"})
        tiers[key] = Tier(key, entry.texts("document_types"))
    if not tiers:
        raise ConfigError(f"{path.name} names no evidence tier. Add a [tiers.<name>] table for each one.")
    rules = tuple(_ladder_rule(path, entry, tiers) for entry in _tables(path, data, "rules"))
    if not rules:
        raise ConfigError(f"{path.name} has no rule. Add a [[rules]] table for outcome judgments and one for moments.")
    if len({rule.id for rule in rules}) != len(rules):
        raise ConfigError(f"In {path.name}, two rules share an id. Each rule's id names its sentence in the copy.")
    ties = _Entry(path, "ties", data.get("ties"))
    ties.only({"order", "specificity"})
    order = ties.texts("order")
    if not set(order) <= set(TIES) or len(set(order)) != len(order):
        ties._fail("order", f"can use only {' and '.join(TIES)}, each once")
    groups = ties.table.get("specificity")
    if not isinstance(groups, list) or not all(isinstance(group, list) for group in groups):
        ties._fail("specificity", "must be a list of groups of forms, such as [[\"rating_field\"], [\"narrative\"]]")
    listed = [form for group in groups for form in group]
    if sorted(listed) != sorted(FORMS):
        ties._fail("specificity", f"must list each of these forms once: {', '.join(FORMS)}")
    scales_table = data.get("scales") or {}
    scales_entry = _Entry(path, "scales", scales_table)
    scales = {}
    for key, table in scales_table.items():
        if key == "no_rating":
            continue
        entry = _Entry(path, f"scales.{key}", table)
        entry.only({"satisfactory", "unsatisfactory", "values"})
        scale = Scale(key, entry.texts("satisfactory"), entry.texts("unsatisfactory"), entry.texts("values"))
        if not scale.ratings:
            entry._fail("values", "is missing. A scale needs its ratings, with satisfactory and unsatisfactory "
                                  "sides or as plain values")
        scales[key] = scale
    attributes = {}
    for key, table in (data.get("attributes") or {}).items():
        entry = _Entry(path, f"attributes.{key}", table)
        entry.only({"kind", "class", "scale", "names"})
        kind, class_ = entry.text("kind"), entry.text("class")
        if kind not in KINDS:
            entry._fail("kind", f"must be one of {', '.join(KINDS)}")
        if class_ not in CLASSES:
            entry._fail("class", f"must be {' or '.join(CLASSES)}")
        scale = entry.text("scale", required=(kind == "rating"))
        if scale is not None and scale not in scales:
            entry._fail("scale", f"names {scale}, which [scales] does not define")
        if not entry.texts("names"):
            entry._fail("names", "must list the field names that mean this attribute")
        attributes[key] = Attribute(key, kind, class_, scale, entry.texts("names"))
    names = [name for attribute in attributes.values() for name in attribute.names]
    if len(set(names)) != len(names):
        raise ConfigError(f"In {path.name}, a field name means two attributes. Each name must mean one.")
    return Ladder(path, rules, order, tuple(tuple(group) for group in groups), tiers, attributes, scales,
                  scales_entry.texts("no_rating"))


# ── The lesson lists ─────────────────────────────────────────────────────

LESSON_LISTS = ("risk_factors", "stages", "kinds")


@dataclass(frozen=True)
class ListItem:
    key: str
    label: str


@dataclass(frozen=True)
class LessonLists:
    """The closed lists a lesson is tagged from, each in file order, and the extractor's example projects."""

    risk_factors: tuple[ListItem, ...]
    stages: tuple[ListItem, ...]
    kinds: tuple[ListItem, ...]
    example_projects: tuple[str, ...]

    def _find(self, items: tuple[ListItem, ...], key: str | None) -> ListItem | None:
        return next((item for item in items if item.key == key), None)

    def risk_factor(self, key: str | None) -> ListItem | None:
        return self._find(self.risk_factors, key)

    def stage(self, key: str | None) -> ListItem | None:
        return self._find(self.stages, key)

    def kind(self, key: str | None) -> ListItem | None:
        return self._find(self.kinds, key)

    def as_dict(self) -> dict:
        """The lists as a page or a prompt takes them: each item's key and label, in order."""
        return {name: [{"key": item.key, "label": item.label} for item in getattr(self, name)]
                for name in LESSON_LISTS}


def load_lesson_lists(path: Path = CONFIG_DIR / "lessons.toml") -> LessonLists:
    """The lesson lists. A key may appear once in its list."""
    data = _read(path)
    _Entry(path, "the file", data).only({*LESSON_LISTS, "extraction"})
    lists = {}
    for name in LESSON_LISTS:
        items: list[ListItem] = []
        for entry in _tables(path, data, name):
            entry.only({"key", "label"})
            item = ListItem(entry.text("key"), entry.text("label"))
            if not re.fullmatch(r"[a-z][a-z0-9_]*", item.key):
                entry._fail("key", "must be lower case letters, digits and _")
            if item.key in {seen.key for seen in items}:
                entry._fail("key", f"repeats {item.key!r}. Each key is listed once")
            items.append(item)
        if not items:
            raise ConfigError(f"{path.name} lists no {name}. Add at least one [[{name}]] entry.")
        lists[name] = tuple(items)
    extraction = _Entry(path, "extraction", data.get("extraction", {}))
    extraction.only({"example_projects"})
    examples = extraction.texts("example_projects")
    for project in examples:
        if not PROJECT_ID.fullmatch(project):
            extraction._fail("example_projects", f"must list project IDs, not {project!r}")
    return LessonLists(**lists, example_projects=examples)


# ── The item registry of "Check your criteria" (ticket 31) ───────────────

CRITERIA_PARTS = ("contracts", "amount", "window_years", "years")


@dataclass(frozen=True)
class CriteriaItem:
    key: str
    label: str
    phrase: str
    is_criterion: bool
    synonyms: tuple[str, ...]
    parts: tuple[str, ...]


@dataclass(frozen=True)
class CriteriaItems:
    items: tuple[CriteriaItem, ...]
    cues: tuple[str, ...]

    def item(self, key: str) -> CriteriaItem:
        for item in self.items:
            if item.key == key:
                return item
        raise KeyError(key)

    def has(self, key: str) -> bool:
        return any(item.key == key for item in self.items)

    @property
    def criteria(self) -> tuple[CriteriaItem, ...]:
        return tuple(item for item in self.items if item.is_criterion)


def load_criteria_items(path: Path = CONFIG_DIR / "criteria_items.toml") -> CriteriaItems:
    """The kinds of requirement section 5 compares, in the registry's order. The last is other, which has no
    synonyms and holds every rejection reason no other item names."""
    data = _read(path)
    _Entry(path, "the file", data).only({"items", "requirements"})
    items: list[CriteriaItem] = []
    for entry in _tables(path, data, "items"):
        entry.only({"key", "label", "phrase", "is_criterion", "synonyms", "parts"})
        item = CriteriaItem(entry.text("key"), entry.text("label"), entry.text("phrase"), entry.boolean("is_criterion"),
                            tuple(word.lower() for word in entry.texts("synonyms")), entry.texts("parts"))
        if not re.fullmatch(r"[a-z][a-z0-9_]*", item.key):
            entry._fail("key", "must be lower case letters, digits and _")
        if item.key in {seen.key for seen in items}:
            entry._fail("key", f"repeats {item.key!r}. Each key is listed once")
        strays = [part for part in item.parts if part not in CRITERIA_PARTS]
        if strays:
            entry._fail("parts", f"names {', '.join(strays)}; the parts are {', '.join(CRITERIA_PARTS)}")
        items.append(item)
    if not items or items[-1].key != "other" or items[-1].synonyms or items[-1].is_criterion:
        raise ConfigError(f"{path.name} must end with the item other, which has no synonyms and is no criterion.")
    requirements = _Entry(path, "requirements", data.get("requirements", {}))
    requirements.only({"cues"})
    cues = tuple(word.lower() for word in requirements.texts("cues"))
    if not cues:
        requirements._fail("cues", "must list the words that mark a sentence as setting a requirement")
    return CriteriaItems(tuple(items), cues)


# ── Rebidding risk (ticket 28) ───────────────────────────────────────────

@dataclass(frozen=True)
class RebiddingReason:
    """A reason a notice gives in words for advertising a package again, with the patterns that find its sentence."""

    code: str
    patterns: tuple[re.Pattern, ...]


def load_rebidding_reasons(path: Path = CONFIG_DIR / "rebidding_reasons.toml") -> tuple[RebiddingReason, ...]:
    """The reasons a notice gives in words, in the registry's order."""
    data = _read(path)
    _Entry(path, "the file", data).only({"reason"})
    reasons: list[RebiddingReason] = []
    for entry in _tables(path, data, "reason"):
        entry.only({"code", "patterns"})
        code = entry.text("code")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", code) or code in {seen.code for seen in reasons}:
            entry._fail("code", "must be lower case letters, digits and _, and listed once")
        try:
            patterns = tuple(re.compile(pattern, re.IGNORECASE) for pattern in entry.texts("patterns"))
        except re.error as error:
            entry._fail("patterns", f"must be regular expressions ({error})")
        if not patterns:
            entry._fail("patterns", "must list at least one pattern")
        reasons.append(RebiddingReason(code, patterns))
    return tuple(reasons)


@dataclass(frozen=True)
class RebiddingSettings:
    """The rebidding models (ticket 28): the model file's [rebidding] table."""

    learners: tuple[str, ...]  # the two models compared, by their names in strata.estimates.rebidding_model
    registered_model: str  # catalog.schema.model in Unity Catalog
    experiment: str  # the MLflow experiment
    test_years: tuple[int, ...]  # the rolling backtests, each tested on one calendar year
    calibration_every: int  # every this-many-th training package calibrates the gradient boosting
    learner_settings: dict  # each learner's own settings, from [rebidding.<learner>]


def load_rebidding(path: Path = CONFIG_DIR / "models.toml") -> RebiddingSettings:
    """The model file's [rebidding] table, with each learner's settings."""
    entry = _Entry(path, "rebidding", _read(path).get("rebidding"))
    learners = entry.texts("learners")
    entry.only({"learners", "registered_model", "experiment", "test_years", "calibration_every", *learners})
    if len(learners) < 2:
        entry._fail("learners", "must name the two models the backtests compare")
    from strata.estimates.rebidding_model import LEARNERS  # here, so loading other config files never imports numpy

    unknown = [learner for learner in learners if learner not in LEARNERS]
    if unknown:
        entry._fail("learners", f"names {', '.join(unknown)}, which LEARNERS in src/strata/estimates/rebidding_model.py "
                                f"does not have: it has {', '.join(sorted(LEARNERS))}")
    registered = entry.text("registered_model")
    if registered.count(".") != 2:
        entry._fail("registered_model", "must be a three-part Unity Catalog name, such as strata.gold.rebidding_risk")
    years = entry.table.get("test_years")
    if not isinstance(years, list) or not years or not all(isinstance(y, int) and not isinstance(y, bool) for y in years):
        entry._fail("test_years", "must be a list of years, such as [2021, 2022]")
    every = entry.integer("calibration_every")
    if every < 2:
        entry._fail("calibration_every", "must be 2 or more, so the model learns from some packages")
    settings = {}
    for learner in learners:
        settings[learner] = dict(_Entry(path, f"rebidding.{learner}", entry.table.get(learner, {})).table)
    return RebiddingSettings(learners, registered, entry.text("experiment"), tuple(sorted(years)), every, settings)


# ── The editions of the procurement rules ────────────────────────────────

@dataclass(frozen=True)
class Edition:
    key: str
    name: str  # as a sentence names it: "Its projects followed {name}."
    phrases: tuple[str, ...]
    short: str = ""  # as a label names it, with a capital: "Procurement Guidelines, January 2011"
    # The day it took effect, when the file gives one. In the month it falls in, the estimates loop marks the lessons
    # and models of other editions as being re-checked and raises a retrain (ticket 44).
    effective_from: dt.date | None = None


_STRAIGHT = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"'})


def _plain(text: str) -> str:
    """Text as an edition's phrases are matched: lower case, quote marks straight, each run of spaces one."""
    return " ".join(text.translate(_STRAIGHT).lower().split())


@dataclass(frozen=True)
class Editions:
    editions: tuple[Edition, ...]

    def named_in(self, text: str) -> Edition | None:
        """The first edition whose phrases all appear in the text, or None."""
        plain = _plain(text)
        return next((edition for edition in self.editions
                     if all(_plain(phrase) in plain for phrase in edition.phrases)), None)

    def get(self, key: str | None) -> Edition | None:
        return next((edition for edition in self.editions if edition.key == key), None)

    def followed(self, pad_texts: Iterable[str]) -> Edition | None:
        """The edition a project followed: the one the first of its PAD's passages, in order, names, or None. A lesson
        takes its project's (ticket 29), and the backtest counts each edition's packages by it (ticket 44)."""
        return next((found for found in (self.named_in(text) for text in pad_texts) if found), None)


def load_editions(path: Path = CONFIG_DIR / "editions.toml") -> Editions:
    """The editions, in file order, which is the order they are matched in."""
    data = _read(path)
    _Entry(path, "the file", data).only({"editions"})
    editions: list[Edition] = []
    for entry in _tables(path, data, "editions"):
        entry.only({"key", "name", "short", "phrases", "effective_from"})
        edition = Edition(entry.text("key"), entry.text("name"), entry.texts("phrases"), entry.text("short"),
                          entry.date("effective_from") if "effective_from" in entry.table else None)
        if not edition.phrases:
            entry._fail("phrases", "must list at least one phrase a PAD uses for the edition")
        if edition.key in {seen.key for seen in editions}:
            entry._fail("key", f"repeats {edition.key!r}. Each edition is listed once")
        editions.append(edition)
    return Editions(tuple(editions))


# ── The project page's lists (ticket 21) ─────────────────────────────────

LINE_STATES = ("info", "warning")
KEY_DATE = "key_date"  # an event dated by the assertions reader's own key-date pattern (KEY_DATE_LABELS)


@dataclass(frozen=True)
class TimelineEvent:
    """An event the timeline's How lane draws (ticket 23): the words a passage must hold, and the pattern whose one
    group reads the event's date in date_format, or key_date for the assertions reader's pattern for this kind."""
    kind: str
    words: tuple[str, ...]
    pattern: str
    date_format: str


@dataclass(frozen=True)
class TimelineSettings:
    """A project timeline's settings (ticket 23): the state a dashed line takes when no answer or draft open on the
    page depends on it, and the events the How lane draws, in file order."""
    disagreement_line_state: str
    events: tuple[TimelineEvent, ...]


@dataclass(frozen=True)
class ProjectPage:
    """The project page's lists: the documents API's type for each Documents group, in project-cycle
    order; the groups re-issued under one report number; the Summary's ISR ratings and the projects
    API's Procurement rating code; and the Timeline tab's settings."""
    document_groups: dict[str, str]
    reissued: frozenset[str]
    isr_ratings: dict[str, str]
    procurement_rating_code: str
    timeline: TimelineSettings


def _timeline(path: Path, data: dict) -> TimelineSettings:
    timeline = _Entry(path, "timeline", data.get("timeline", {}))
    timeline.only({"disagreement_line_state", "events"})
    state = timeline.text("disagreement_line_state")
    if state not in LINE_STATES:
        timeline._fail("disagreement_line_state", f"must be info or warning, not {state!r}")
    events: list[TimelineEvent] = []
    for entry in _tables(path, timeline.table, "events"):
        entry.only({"kind", "words", "pattern", "date_format"})
        pattern = entry.text("pattern")
        if pattern != KEY_DATE:
            try:
                groups = re.compile(pattern).groups
            except re.error:
                groups = 0
            if groups != 1:
                entry._fail("pattern", "must be key_date or a pattern with one group, which reads the date")
        event = TimelineEvent(entry.text("kind"), entry.texts("words"), pattern, entry.text("date_format"))
        if not event.words:
            entry._fail("words", "must name at least one phrase a passage holds")
        if any(other.kind == event.kind for other in events):
            entry._fail("kind", f"repeats {event.kind!r}. Each event is listed once")
        events.append(event)
    return TimelineSettings(state, tuple(events))


def load_project_page(path: Path = CONFIG_DIR / "project_page.toml") -> ProjectPage:
    """The project page's lists, in file order, which is the order the page shows them in."""
    data = _read(path)
    _Entry(path, "the file", data).only({"documents", "summary", "timeline"})
    documents = _Entry(path, "documents", data.get("documents", {}))
    documents.only({"groups", "reissued"})
    groups: dict[str, str] = {}
    for entry in _tables(path, documents.table, "groups"):
        entry.only({"type", "group"})
        kind, group = entry.text("type"), entry.text("group")
        if group in groups.values() or group == "other":
            entry._fail("group", f"repeats {group!r}. Each group is listed once, and other is kept for the rest")
        groups[kind] = group
    reissued = frozenset(documents.texts("reissued"))
    if not reissued <= set(groups.values()):
        documents._fail("reissued", "may name only the groups listed under [[documents.groups]]")
    summary = _Entry(path, "summary", data.get("summary", {}))
    summary.only({"isr_ratings", "procurement_rating_code"})
    ratings: dict[str, str] = {}
    for entry in _tables(path, summary.table, "isr_ratings"):
        entry.only({"name", "key"})
        ratings[entry.text("name")] = entry.text("key")
    return ProjectPage(groups, reissued, ratings, summary.text("procurement_rating_code"), _timeline(path, data))

# ── The package form schema (ticket 15) ──────────────────────────────────

PACKAGE_FORM_KINDS = ("choice", "text", "amount", "count", "country", "months")
PACKAGE_FORM_SOURCES = ("typed", "computed", "guessed")
PACKAGE_FORM_RULES = ("review", "market_approach")
_PACKAGE_FIELD_KEYS = {"key", "group", "kind", "source", "label", "add_label", "step_field", "picks", "default",
                       "options", "rule", "optional", "asked", "unit", "unit_one", "aliases"}


@dataclass(frozen=True)
class FormOption:
    value: str
    label: str


@dataclass(frozen=True)
class FormGroup:
    key: str
    label: str
    name: str


@dataclass(frozen=True)
class FormField:
    key: str
    group: str
    kind: str
    source: str
    label: str
    add_label: str
    step_field: str | None = None
    picks: str | None = None
    default: str | None = None
    options: tuple[FormOption, ...] = ()
    rule: str | None = None
    optional: bool = False
    asked: bool = True
    unit: str | None = None
    unit_one: str | None = None
    aliases: bool = False

    def as_dict(self) -> dict:
        return {"key": self.key, "group": self.group, "kind": self.kind, "source": self.source, "label": self.label,
                "add_label": self.add_label, "step_field": self.step_field, "picks": self.picks,
                "default": self.default, "options": [{"value": o.value, "label": o.label} for o in self.options],
                "rule": self.rule, "optional": self.optional, "unit": self.unit, "unit_one": self.unit_one,
                "aliases": self.aliases}


@dataclass(frozen=True)
class PackageForm:
    groups: tuple[FormGroup, ...]
    fields: tuple[FormField, ...]

    def field(self, key: str) -> FormField:
        for field in self.fields:
            if field.key == key:
                return field
        raise KeyError(key)

    def has(self, key: str) -> bool:
        return any(field.key == key for field in self.fields)


def load_package_form(path: Path = CONFIG_DIR / "package_form.toml") -> PackageForm:
    """The package form schema, checked: each field in a group the file defines, with a kind, a source and, for a
    computed field, a rule the thresholds file has. Nothing else in Strata names a field, so adding an entry to
    the file adds a chip and removing one removes it."""
    data = _read(path)

    def fail(where: str, need: str):
        raise ConfigError(f"In {path.name}, {where} {need}.")

    groups = []
    for key, table in (data.get("groups") or {}).items():
        if not isinstance(table, dict) or not table.get("label") or not table.get("name"):
            fail(f"groups.{key}", "needs a label and a name")
        groups.append(FormGroup(key, str(table["label"]), str(table["name"])))
    if not groups:
        fail("the file", "needs [groups]")
    group_keys = {group.key for group in groups}
    fields, seen = [], set()
    for number, table in enumerate(data.get("fields") or [], 1):
        where = f"field {number} ({table.get('key', 'no key')})"
        unknown = set(table) - _PACKAGE_FIELD_KEYS
        if unknown:
            fail(where, f"has keys it does not take: {', '.join(sorted(unknown))}")
        for name in ("key", "group", "kind", "source", "label", "add_label"):
            if not isinstance(table.get(name), str) or not table[name].strip():
                fail(where, f"needs {name}")
        if table["key"] in seen:
            fail(where, "repeats a key")
        seen.add(table["key"])
        if table["group"] not in group_keys:
            fail(where, f"names the group {table['group']}, which [groups] does not define")
        if table["kind"] not in PACKAGE_FORM_KINDS:
            fail(where, f"has the kind {table['kind']}; the kinds are {', '.join(PACKAGE_FORM_KINDS)}")
        if table["source"] not in PACKAGE_FORM_SOURCES:
            fail(where, f"has the source {table['source']}; the sources are {', '.join(PACKAGE_FORM_SOURCES)}")
        options = tuple(FormOption(str(o["value"]), str(o["label"])) for o in table.get("options") or [])
        if table["kind"] == "choice" and not options:
            fail(where, "is a choice with no options")
        if table["source"] == "computed" and table.get("rule") not in PACKAGE_FORM_RULES:
            fail(where, f"is computed, so it needs a rule: {', '.join(PACKAGE_FORM_RULES)}")
        if table.get("default") is not None and options and table["default"] not in {o.value for o in options}:
            fail(where, "has a default that is not one of its options")
        fields.append(FormField(
            key=table["key"], group=table["group"], kind=table["kind"], source=table["source"], label=table["label"],
            add_label=table["add_label"], step_field=table.get("step_field"), picks=table.get("picks"),
            default=table.get("default"), options=options, rule=table.get("rule"),
            optional=bool(table.get("optional", False)), asked=bool(table.get("asked", table["source"] != "computed")),
            unit=table.get("unit"), unit_one=table.get("unit_one"), aliases=bool(table.get("aliases", False))))
    return PackageForm(tuple(groups), tuple(fields))


# ── The upload and STEP row registry (ticket 38) ─────────────────────────

UPLOAD_FORMATS = ("step_export", "published_tables")
UPLOAD_CSV = ("copied", "left", "split")
UPLOAD_STEP_CSV = ("planned", "left")


@dataclass(frozen=True)
class UploadColumn:
    """One of STEP's descriptive columns, by its key in src/strata/reader/step.py's COLUMNS."""

    key: str
    need: bool
    csv: str  # copied, left or split


@dataclass(frozen=True)
class Uploads:
    """What an implementing agency's upload may be, and how the STEP rows CSV lays out STEP's columns."""

    accept: tuple[str, ...]
    max_size_bytes: int
    max_rows: int
    format: str
    columns: tuple[UploadColumn, ...]
    step_planned: str
    step_actual: str
    one_row: str
    aliases: dict[str, tuple[str, ...]]
    max_unzipped_bytes: int  # the most an Excel file may hold once unzipped
    max_columns: int  # the last column read on a sheet


def load_uploads(path: Path = CONFIG_DIR / "uploads.toml") -> Uploads:
    """The upload and STEP row registry, in its file's order. src/strata/reader/step_columns.py checks its keys against
    STEP's columns."""
    data = _read(path)
    _Entry(path, "the file", data).only({"uploads", "columns", "steps", "aliases"})
    limits = _Entry(path, "uploads", data.get("uploads"))
    limits.only({"accept", "max_size_bytes", "max_rows", "format", "max_unzipped_bytes", "max_columns"})
    accept = limits.texts("accept")
    if not accept or not all(ending.startswith(".") for ending in accept):
        limits._fail("accept", "must list file name endings, such as .xlsx")
    if limits.text("format") not in UPLOAD_FORMATS:
        limits._fail("format", f"must be one of {', '.join(UPLOAD_FORMATS)}")
    columns = []
    for key, table in (data.get("columns") or {}).items():
        entry = _Entry(path, f"columns.{key}", table)
        entry.only({"need", "csv"})
        if entry.text("csv") not in UPLOAD_CSV:
            entry._fail("csv", f"must be one of {', '.join(UPLOAD_CSV)}")
        columns.append(UploadColumn(key, bool(table.get("need", False)), entry.text("csv")))
    steps = _Entry(path, "steps", data.get("steps"))
    steps.only({"planned", "actual", "one_row"})
    for name in ("planned", "actual"):
        if steps.text(name) not in UPLOAD_STEP_CSV:
            steps._fail(name, f"must be one of {', '.join(UPLOAD_STEP_CSV)}")
    if "{step}" not in steps.text("one_row") or "{head}" not in steps.text("one_row"):
        steps._fail("one_row", "must hold {step} and {head}")
    aliases = {}
    for key, names in (data.get("aliases") or {}).items():
        aliases[key] = _Entry(path, "aliases", {key: names}).texts(key)
    return Uploads(accept, limits.integer("max_size_bytes"), limits.integer("max_rows"), limits.text("format"),
                   tuple(columns), steps.text("planned"), steps.text("actual"), steps.text("one_row"), aliases,
                   limits.integer("max_unzipped_bytes"), limits.integer("max_columns"))
# ── The language registry (ticket 42) ────────────────────────────────────

DIRECTIONS = ("ltr", "rtl")
_LANGUAGE_KEYS = {"code", "api_name", "endonym", "direction", "working"}
_WRITING_KEYS = {"word_locale", "number_locale", "decimal", "group", "group_also", "months", "date_joiner", "joiners",
                 "number_words", "scale_words", "times_words", "joined_ones", "never_write", "terms", "reviewed_by", "reviewed_on"}
ENGLISH = "en"


@dataclass(frozen=True)
class Language:
    """One language a source can be written in, and for a working language, how Strata writes and checks it."""

    code: str  # ISO 639-1, as passages carry it and the screens' lang attribute takes it
    api_name: str  # the Documents API's lang field, word for word
    endonym: str
    direction: str  # ltr or rtl
    working: bool  # Strata writes answers and drafts in it
    word_locale: str | None = None
    number_locale: str | None = None
    decimal: str = "."
    group: str = ","
    group_also: tuple[str, ...] = ()
    months: tuple[str, ...] = ()
    date_joiner: str = ""
    joiners: tuple[str, ...] = ()
    number_words: tuple[tuple[str, int], ...] = ()
    scale_words: tuple[tuple[str, int], ...] = ()
    times_words: tuple[tuple[str, int], ...] = ()  # multiply a smaller number just before them: "quatre-vingts"
    joined_ones: tuple[tuple[str, int], ...] = ()  # the words for one, a number only after a joiner: "vingt et une"
    never_write: tuple[str, ...] = ()
    terms: tuple[tuple[str, str], ...] = ()
    reviewed_by: str = ""
    reviewed_on: str = ""


@dataclass(frozen=True)
class Languages:
    languages: tuple[Language, ...]

    def get(self, code: str | None) -> Language | None:
        return next((language for language in self.languages if language.code == code), None)

    @property
    def working(self) -> tuple[Language, ...]:
        return tuple(language for language in self.languages if language.working)

    def code_for_api_name(self, name: str | None) -> str | None:
        """The code for a Documents API lang field, such as "French", or None when the registry has no such language."""
        return next((language.code for language in self.languages if language.api_name == name), None)


def _word_values(entry: _Entry, key: str) -> tuple[tuple[str, int], ...]:
    table = entry.table.get(key, {})
    if not isinstance(table, dict) or not all(isinstance(word, str) and isinstance(value, int)
                                              and not isinstance(value, bool) for word, value in table.items()):
        entry._fail(key, "must be a table of words, each with a whole number")
    return tuple(table.items())


def _marks(entry: _Entry, key: str, one: bool) -> str | tuple[str, ...]:
    """A number mark, or a list of them: one character each, a space included, so not read with _Entry.text."""
    value = entry.table.get(key, None if one else [])
    marks = [value] if one else value
    if not isinstance(marks, list) or not all(isinstance(mark, str) and len(mark) == 1 for mark in marks):
        entry._fail(key, "must be one character" if one else "must be a list of single characters")
    return value if one else tuple(value)


def load_languages(path: Path = CONFIG_DIR / "languages.toml") -> Languages:
    """Every language, in the file's order. A working language other than English must say how it writes numbers
    and dates, so the verifier can read them."""
    data = _read(path)
    _Entry(path, "the file", data).only({"language"})
    found: list[Language] = []
    for entry in _tables(path, data, "language"):
        entry.only(_LANGUAGE_KEYS | _WRITING_KEYS)
        code = entry.text("code")
        if not re.fullmatch(r"[a-z]{2}", code):
            entry._fail("code", f"must be a two-letter ISO 639-1 code in lower case, not {code!r}")
        if code in {language.code for language in found}:
            entry._fail("code", f"repeats {code!r}. List each language once")
        direction = entry.text("direction")
        if direction not in DIRECTIONS:
            entry._fail("direction", f"must be one of {', '.join(DIRECTIONS)}")
        working = entry.boolean("working")
        fields = {}
        if working:
            months = entry.texts("months")
            if len(months) != 12:
                entry._fail("months", "must list the 12 months, January first")
            terms = entry.table.get("terms", {})
            if not isinstance(terms, dict) or not all(isinstance(value, str) for value in terms.values()):
                entry._fail("terms", "must be a table of GLOSSARY.md terms, each with its words in the language")
            fields = {"word_locale": entry.text("word_locale"), "number_locale": entry.text("number_locale"),
                      "decimal": _marks(entry, "decimal", True), "group": _marks(entry, "group", True),
                      "group_also": _marks(entry, "group_also", False), "months": months,
                      "date_joiner": entry.table.get("date_joiner", ""), "joiners": entry.texts("joiners"),
                      "number_words": _word_values(entry, "number_words"),
                      "scale_words": _word_values(entry, "scale_words"),
                      "times_words": _word_values(entry, "times_words"),
                      "joined_ones": _word_values(entry, "joined_ones"), "never_write": entry.texts("never_write"),
                      "terms": tuple(terms.items()), "reviewed_by": entry.table.get("reviewed_by", ""),
                      "reviewed_on": str(entry.table.get("reviewed_on", ""))}
            if fields["decimal"] == fields["group"]:
                entry._fail("group", "must differ from decimal")
        elif set(entry.table) & _WRITING_KEYS:
            entry._fail("working", "is false, so the language takes none of a working language's keys")
        found.append(Language(code, entry.text("api_name"), entry.text("endonym"), direction, working, **fields))
    if not any(language.code == ENGLISH and language.working for language in found):
        raise ConfigError(f"In {path.name}, English (en) must be listed as a working language.")
    return Languages(tuple(found))


# ── The method-name registry (ticket 42) ─────────────────────────────────

@dataclass(frozen=True)
class MethodName:
    """One name or code a source writes for a method, and the current Procurement Regulations' name it stands for."""

    written: str
    language: str
    method: str
    market_approach: str | None = None
    source: str | None = None  # a recorded file under data/fixture/recorded, without .txt for a document
    pdf_page: int | None = None
    checked: bool = True  # read from a recorded source; false until a person checks it against one


@dataclass(frozen=True)
class MethodNames:
    current: tuple[str, ...]
    names: tuple[MethodName, ...]


def load_method_names(path: Path = CONFIG_DIR / "method_names.toml") -> MethodNames:
    """The current method names, then every other name, in the file's order. Each other name stands for a current
    one, and names a recorded source or says it was not checked against one."""
    data = _read(path)
    _Entry(path, "the file", data).only({"current", "name"})
    current = _Entry(path, "the file", data).texts("current")
    if not current:
        raise ConfigError(f"In {path.name}, current must list STEP's method names.")
    known = {entry.code for entry in load_languages().languages}
    names: list[MethodName] = []
    for entry in _tables(path, data, "name"):
        entry.only({"written", "language", "method", "market_approach", "source", "pdf_page", "checked"})
        method = entry.text("method")
        if method not in current:
            entry._fail("method", f"names {method!r}, which is not one of current")
        language = entry.text("language")
        if language not in known:
            entry._fail("language", f"names {language!r}, which config/languages.toml does not list")
        checked = entry.table.get("checked", True)
        source = entry.text("source", required=False)
        if checked is not False and source is None:
            entry._fail("source", "is missing. Name the recorded file that writes it, or set checked = false")
        names.append(MethodName(entry.text("written"), language, method, entry.text("market_approach", required=False),
                                source, entry.integer("pdf_page", required=False), checked is not False))
    return MethodNames(current, tuple(names))


# ── The nightly job's quality checks ─────────────────────────────────────

THREE_PART_TABLE = re.compile(r"strata\.(bronze|silver|gold|ops)\.[a-z][a-z0-9_]*")
COLUMN_NAME = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class QualityCheck:
    """One table a task of the nightly job checks when it finishes (config/quality_checks.toml)."""

    task: str  # the task's key in bundle/nightly.yml
    table: str  # strata.<schema>.<table>
    key: tuple[str, ...]  # the columns that tell one row from another; empty to take a gold query's key, or none
    contacts: bool  # whether to search its notice text for contact details that ingestion missed


def load_quality_checks(path: Path = CONFIG_DIR / "quality_checks.toml") -> tuple[QualityCheck, ...]:
    """Every table the nightly job checks, in the file's order."""
    data = _read(path)
    _Entry(path, "the file", data).only({"tables"})
    found: list[QualityCheck] = []
    for entry in _tables(path, data, "tables"):
        entry.only({"task", "table", "key", "contacts"})
        task, table, key = entry.text("task"), entry.text("table"), entry.texts("key")
        if not COLUMN_NAME.fullmatch(task):
            entry._fail("task", "must be a task key such as bronze_to_gold")
        if not THREE_PART_TABLE.fullmatch(table):
            entry._fail("table", "must name a table in three parts, such as strata.gold.project")
        if not all(COLUMN_NAME.fullmatch(column) for column in key):
            entry._fail("key", "must list column names")
        if (task, table) in {(check.task, check.table) for check in found}:
            entry._fail("table", "is listed twice for the same task")
        found.append(QualityCheck(task, table, key, entry.boolean("contacts") if "contacts" in entry.table else False))
    return tuple(found)


# ── The Genie space (ticket 33) ──────────────────────────────────────────

GENIE_TABLE = re.compile(r"strata\.gold\.[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class GenieTrusted:
    """One trusted SQL example: a question and the file in src/strata/genie/trusted/ that answers it."""

    question: str
    sql: str


@dataclass(frozen=True)
class GenieConfig:
    """The Genie space as config/genie.toml defines it."""

    title: str
    description: str
    instruction: str
    metric_views: tuple[str, ...]
    tables: tuple[str, ...]
    sample_questions: tuple[str, ...]
    trusted: tuple[GenieTrusted, ...]


def load_genie(path: Path = CONFIG_DIR / "genie.toml") -> GenieConfig:
    """The Genie space: its title, description, one text instruction, what it reads and its trusted SQL."""
    data = _read(path)
    space = _Entry(path, "space", data.get("space"))
    space.only({"title", "description", "instruction", "metric_views", "tables", "sample_questions"})
    reads = space.texts("metric_views") + space.texts("tables")
    wrong = [name for name in reads if not GENIE_TABLE.fullmatch(name)]
    if wrong:
        raise ConfigError(f"In {path.name}, the space reads {', '.join(wrong)}. Name each metric view and table in "
                          "three parts, in strata.gold.")
    trusted = []
    for entry in _tables(path, data, "trusted"):
        entry.only({"question", "sql"})
        trusted.append(GenieTrusted(entry.text("question"), entry.text("sql")))
    if not trusted:
        raise ConfigError(f"In {path.name}, give the space at least one [[trusted]] question with its SQL.")
    return GenieConfig(space.text("title"), space.text("description"), space.text("instruction"),
                       space.texts("metric_views"), space.texts("tables"), space.texts("sample_questions"),
                       tuple(trusted))


# ── Foundry evaluations (ticket 33) ──────────────────────────────────────

@dataclass(frozen=True)
class Evaluator:
    key: str
    label: str
    builtin: str
    data_mapping: dict[str, str]


@dataclass(frozen=True)
class Evaluations:
    api_version: str
    judge_role: str
    evaluators: tuple[Evaluator, ...]


def load_evaluations(path: Path = CONFIG_DIR / "evaluations.toml") -> Evaluations:
    """The Foundry evaluators the full gate runs, with the API version and the judge's model role."""
    data = _read(path)
    top = _Entry(path, "the file", {key: value for key, value in data.items() if key != "evaluators"})
    top.only({"api_version", "judge_role"})
    evaluators = []
    for entry in _tables(path, data, "evaluators"):
        entry.only({"key", "label", "builtin", "data_mapping"})
        mapping = entry.table.get("data_mapping")
        if not isinstance(mapping, dict) or not mapping or not all(
                isinstance(value, str) and value.startswith("{{item.") for value in mapping.values()):
            entry._fail("data_mapping", "must map each input to a field of an item, such as {{item.query}}")
        evaluators.append(Evaluator(entry.text("key"), entry.text("label"), entry.text("builtin"), dict(mapping)))
    if len({evaluator.key for evaluator in evaluators}) != len(evaluators) or not evaluators:
        raise ConfigError(f"In {path.name}, give each evaluator a key of its own.")
    return Evaluations(top.text("api_version"), top.text("judge_role"), tuple(evaluators))


# ── The Azure budget (ticket 45) ─────────────────────────────────────────

@dataclass(frozen=True)
class Budget:
    """The free credit, the day it ends, and the monthly budget after it (config/budget.toml)."""

    credit_usd: int
    credit_ends_on: dt.date
    monthly_usd: int
    name: str
    alert_percents: tuple[int, ...]
    forecast_percent: int
    resource_group: str
    pull_days: int


def load_budget(path: Path = CONFIG_DIR / "budget.toml") -> Budget:
    """The budget the daily cost pull and the Governance page measure spend against, and the wizard sets."""
    data = _read(path)
    unknown = sorted(set(data) - {"credit", "monthly", "pull"})
    if unknown:
        raise ConfigError(f"In {path.name}, {', '.join(unknown)} is not a section I know: use credit, monthly and "
                          "pull.")
    credit = _Entry(path, "credit", data.get("credit"))
    credit.only({"usd", "ends_on"})
    monthly = _Entry(path, "monthly", data.get("monthly"))
    monthly.only({"usd", "name", "alert_percents", "forecast_percent"})
    pull = _Entry(path, "pull", data.get("pull"))
    pull.only({"resource_group", "days"})
    alerts = monthly.table.get("alert_percents", [])
    if not isinstance(alerts, list) or not all(isinstance(value, int) and not isinstance(value, bool)
                                               for value in alerts):
        monthly._fail("alert_percents", "must be a list of whole numbers")
    return Budget(credit.integer("usd"), credit.date("ends_on"), monthly.integer("usd"), monthly.text("name"),
                  tuple(alerts), monthly.integer("forecast_percent"), pull.text("resource_group"),
                  pull.integer("days"))


# ── The KPI registry (ticket 45) ─────────────────────────────────────────

KPI_KINDS = ("count", "share", "money", "median", "rate_per_100", "score")
KPI_LOOPS = ("knowledge", "retrieval", "estimates")
KPI_ROLES = ("leading", "lagging")
KPI_ID = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class Kpi:
    """One KPI, defined once: its kind, rounding, defining query and the loop it belongs to (config/kpis.toml)."""

    id: str
    kind: str
    rounding: int
    query: str
    fewest: str | None = None
    target: bool = False
    loop: str | None = None
    role: str | None = None

    @property
    def copy_keys(self) -> tuple[str, str, str]:
        """Its words in web/src/copy.ts: the tile's title, its description and the counter's fallback sentence."""
        return (f"kpi.{self.id}.name", f"kpi.{self.id}.definition", f"kpi.{self.id}.outof")


def load_kpis(path: Path = CONFIG_DIR / "kpis.toml") -> dict[str, Kpi]:
    """Every KPI in the registry, by id, in the file's order."""
    data = _read(path)
    tables = data.get("kpis")
    if not isinstance(tables, dict) or not tables or set(data) != {"kpis"}:
        raise ConfigError(f"In {path.name}, write each KPI as a [kpis.<id>] table, and nothing else.")
    found = {}
    for key, table in tables.items():
        if not KPI_ID.fullmatch(key):
            raise ConfigError(f"In {path.name}, {key} is not a KPI id: use lower case letters, digits and _.")
        entry = _Entry(path, f"kpis.{key}", table)
        entry.only({"kind", "rounding", "query", "fewest", "target", "loop", "role"})
        kind = entry.text("kind")
        if kind not in KPI_KINDS:
            entry._fail("kind", f"must be one of {', '.join(KPI_KINDS)}")
        loop, role = entry.text("loop", required=False), entry.text("role", required=False)
        if (loop is None) != (role is None) or (loop and loop not in KPI_LOOPS) or (role and role not in KPI_ROLES):
            entry._fail("loop", f"and role go together: a loop of {', '.join(KPI_LOOPS)} and a role of "
                                f"{', '.join(KPI_ROLES)}")
        found[key] = Kpi(key, kind, entry.integer("rounding"), entry.text("query"),
                         entry.text("fewest", required=False),
                         entry.boolean("target") if "target" in table else False, loop, role)
    return found


# ── The examples registry (ticket 41) ────────────────────────────────────

START_HERE_SLOTS = ("showcase", "demo_project", "demo_agency_id", "demo_plan_date", "lesson_notice")
# The pages a box suggestion shows on (ticket 112): home also serves every page with no scope.
ASK_PAGES = ("package", "project", "plan_check", "home")
# What a home suggestion is asked within, filled from the slice file as Start here's links are.
ASK_WITHIN = ("demo_package", "showcase")


@dataclass(frozen=True)
class StartHereLink:
    """One link on Home's Start here strip: its words' key in the copy file and where it lands."""

    key: str
    href: str


@dataclass(frozen=True)
class AskSuggestion:
    """One question the box suggests while it is focused and empty (ticket 112): its words' key in the copy file
    (copy.box.suggest), the page it shows on, the evals/benchmark.yaml question it shortens, and, on Home, the slice
    file's example it is asked within ("demo_package" or "showcase")."""

    key: str
    page: str
    benchmark: str
    within: str | None = None


@dataclass(frozen=True)
class Examples:
    """The examples Strata sets up for the reviewing panel, and where Start here's links land (config/examples.toml).
    The showcase project and the demo plan come from the slice file, so they are not repeated here."""

    viewers: str  # the roles file's group whose people get the examples
    follows: tuple[str, ...]  # project IDs each viewer follows beside the demo plan's project
    sentences: dict[str, str]  # a package planned from a sentence, by its key
    ppsd_package: str
    ppsd_criteria: dict
    ppsd_risks: int
    lesson_change_sentence: str  # the sentence the example lesson change adds to the lesson's wording
    start_here: tuple[StartHereLink, ...]
    showcase: Showcase
    demo_plan: DemoPlan
    asks: tuple[AskSuggestion, ...] = ()

    def suggestions(self) -> list[dict]:
        """Each box suggestion, with what a home row is asked within filled in from the slice file: the demo package's
        STEP reference or the showcase project's ID. A page's own rows are asked within its scope, so theirs is None."""
        values = {"demo_package": self.demo_plan.package, "showcase": self.showcase.project_id}
        return [{"key": ask.key, "page": ask.page, "benchmark": ask.benchmark,
                 "within": values[ask.within] if ask.within else None} for ask in self.asks]

    def links(self, agency_id: str, lesson_notice: str = "") -> list[dict]:
        """Each Start here link with its address filled in: the demo plan's agency id from check_plan's result, and the
        seeded lesson change's anchor on Lessons (#notice-{lesson}-v{version}), or nothing when none was seeded."""
        values = {"showcase": self.showcase.project_id, "demo_project": self.demo_plan.project_id,
                  "demo_agency_id": agency_id, "demo_plan_date": self.demo_plan.plan_date.isoformat(),
                  "lesson_notice": lesson_notice}
        found = []
        for link in self.start_here:
            # The project a link names in its words: the demo plan's, or the showcase project's.
            pid = (self.demo_plan.project_id if "{demo_project}" in link.href else
                   self.showcase.project_id if "{showcase}" in link.href else None)
            found.append({"key": link.key, "href": link.href.format(**values), "pid": pid})
        return found


def load_examples(path: Path = CONFIG_DIR / "examples.toml", slice_path: Path = CONFIG_DIR / "slice.toml") -> Examples:
    """The examples registry, with the slice file's showcase project and demo plan."""
    data = _read(path)
    top = _Entry(path, "the file", data)
    top.only({"viewers", "follows", "packages", "ppsd_rows", "lesson_change", "start_here", "ask"})
    chosen = load_slice(slice_path)
    named = {"showcase": chosen.showcase.project_id}
    follows = []
    for project in top.texts("follows"):
        if project not in named and not PROJECT_ID.fullmatch(project):
            top._fail("follows", f"must name showcase or a project ID, not {project!r}")
        follows.append(named.get(project, project))
    sentences = {}
    for key, table in (data.get("packages") or {}).items():
        entry = _Entry(path, f"packages.{key}", table)
        entry.only({"sentence"})
        sentences[key] = entry.text("sentence")
    ppsd = _Entry(path, "ppsd_rows", data.get("ppsd_rows"))
    ppsd.only({"package", "criteria", "risks"})
    criteria = ppsd.table.get("criteria") or {}
    if not isinstance(criteria, dict):
        ppsd._fail("criteria", "must be a table of find_comparables' parameters")
    change = _Entry(path, "lesson_change", data.get("lesson_change"))
    change.only({"sentence"})
    links = []
    for entry in _tables(path, data, "start_here"):
        entry.only({"key", "href"})
        href = entry.text("href")
        slots = set(re.findall(r"\{(\w+)\}", href))
        if not slots <= set(START_HERE_SLOTS):
            entry._fail("href", f"names {', '.join(sorted(slots - set(START_HERE_SLOTS)))}, which I can't fill. Use only "
                                f"{', '.join(START_HERE_SLOTS)}")
        links.append(StartHereLink(entry.text("key"), href))
    asks = []
    for entry in _tables(path, data, "ask"):
        entry.only({"key", "page", "benchmark", "within"})
        page = entry.text("page")
        if page not in ASK_PAGES:
            entry._fail("page", f"must be one of {', '.join(ASK_PAGES)}, not {page!r}")
        within = entry.text("within", required=page == "home")
        slot = within[1:-1] if within and within.startswith("{") and within.endswith("}") else None
        if within is not None and (page != "home" or slot not in ASK_WITHIN):
            entry._fail("within", "is only for a home row, and must be "
                                  f"{' or '.join('{' + name + '}' for name in ASK_WITHIN)}")
        asks.append(AskSuggestion(entry.text("key"), page, entry.text("benchmark"), slot))
    return Examples(top.text("viewers"), tuple(follows), sentences, ppsd.text("package"), dict(criteria),
                    ppsd.integer("risks"), change.text("sentence"), tuple(links), chosen.showcase, chosen.demo_plan,
                    tuple(asks))


# ── The proposal's registries (ticket 46) ────────────────────────────────

URL_KEYS = ("app", "dashboard", "repo")


@dataclass(frozen=True)
class Urls:
    """Where the panel finds Strata, the deck, the dashboard, the repo and the proposal (config/urls.toml). An
    address that isn't known yet is None, and so is any address that follows from it."""

    app: str | None
    dashboard: str | None
    repo: str | None

    @property
    def deck(self) -> str | None:
        return f"{self.app}/present" if self.app else None

    @property
    def proposal(self) -> str | None:
        return f"{self.repo}/blob/main/docs/proposal.md" if self.repo else None


def load_urls(path: Path = CONFIG_DIR / "urls.toml") -> Urls:
    """The panel's addresses, the one place the proposal, the README and the deck read them."""
    data = _read(path)
    entry = _Entry(path, "the file", data)
    entry.only(set(URL_KEYS))
    found = {}
    for key in URL_KEYS:
        value = data.get(key, "")
        if not isinstance(value, str):
            raise ConfigError(f"In {path.name}, {key} must be text: an https address, or \"\" until it is known.")
        value = value.strip().rstrip("/")
        if value and not re.fullmatch(r"https://[^\s\"<>]+", value):
            raise ConfigError(f"In {path.name}, {key} must be an https address, such as https://example.org, "
                              f"or \"\" until it is known.")
        found[key] = value or None
    return Urls(**found)


@dataclass(frozen=True)
class OpenLink:
    """Something the panel can open to see a criterion working: an app route, a dashboard page or a repo file."""

    label: str
    href: str

    @property
    def kind(self) -> str:
        return self.href.split(":", 1)[0]

    @property
    def target(self) -> str:
        return self.href.split(":", 1)[1]


@dataclass(frozen=True)
class Criterion:
    rubric: str
    says: str
    answered_in: tuple[str, ...]
    open: tuple[OpenLink, ...]


@dataclass(frozen=True)
class Dimension:
    key: str
    name: str
    rubric_name: str
    points: int
    summary: str
    criteria: tuple[Criterion, ...]


@dataclass(frozen=True)
class Rubric:
    """The assessment's rubric as the proposal's map and the deck use it (config/rubric.toml)."""

    source: str
    anchor: str
    dimensions: tuple[Dimension, ...]

    @property
    def total(self) -> int:
        return sum(dimension.points for dimension in self.dimensions)


OPEN_KINDS = ("app", "dashboard", "repo")
ANSWERED_KINDS = ("sec", "fig")


def load_rubric(path: Path = CONFIG_DIR / "rubric.toml") -> Rubric:
    """The rubric map: each dimension with its points and criteria, and where the proposal answers each one."""
    data = _read(path)
    _Entry(path, "the file", data).only({"source", "anchor", "dimensions"})
    head = _Entry(path, "the file", data)
    dimensions = []
    for dimension in _tables(path, data, "dimensions"):
        dimension.only({"key", "name", "rubric_name", "points", "summary", "criteria"})
        criteria = []
        for criterion in _tables(path, dimension.table, "criteria"):
            criterion.where = f"{dimension.where}.{criterion.where}"
            criterion.only({"rubric", "says", "answered_in", "open"})
            answered = criterion.texts("answered_in")
            for ref in answered:
                if ref.split(":", 1)[0] not in ANSWERED_KINDS or ":" not in ref:
                    criterion._fail("answered_in", f"holds {ref}: write sec:<slug> or fig:<slug>")
            links = []
            for number, link in enumerate(criterion.table.get("open", []), 1):
                found = _Entry(path, f"{criterion.where}.open[{number}]", link)
                found.only({"label", "href"})
                opened = OpenLink(found.text("label"), found.text("href"))
                if opened.kind not in OPEN_KINDS or ":" not in opened.href:
                    found._fail("href", f"must start with {', '.join(kind + ':' for kind in OPEN_KINDS)}")
                links.append(opened)
            criteria.append(Criterion(criterion.text("rubric"), criterion.text("says"), tuple(answered), tuple(links)))
        dimensions.append(Dimension(dimension.text("key"), dimension.text("name"), dimension.text("rubric_name"),
                                    dimension.integer("points"), dimension.text("summary"), tuple(criteria)))
    return Rubric(head.text("source"), head.text("anchor"), tuple(dimensions))


@dataclass(frozen=True)
class ChangeDrill:
    """One change the panel is likely to ask for, its one place and its proving test. How long its rehearsal took is
    a measured result, in docs/proposal/rehearsals.toml."""

    change: str
    place: str
    proved_by: str


def load_change_drills(path: Path = CONFIG_DIR / "change_drills.toml") -> tuple[ChangeDrill, ...]:
    """The change drill, in docs/PLAN.md section 15's order (config/change_drills.toml)."""
    data = _read(path)
    _Entry(path, "the file", data).only({"drills"})
    drills = []
    for drill in _tables(path, data, "drills"):
        drill.only({"change", "place", "proved_by"})
        drills.append(ChangeDrill(drill.text("change"), drill.text("place"), drill.text("proved_by")))
    return tuple(drills)


DESIGNED_KEY = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class DesignedNotBuilt:
    """A part of Strata that is designed but not built, where the app labels it and the proposal describes it."""

    key: str
    name: str
    route: str
    paragraph: str
    exists_now: str

    @property
    def copy_key(self) -> str:
        """The app's first-person sentence in web/src/copy.ts, saying what Strata does instead."""
        return f"designedNotBuilt.items.{self.key}"


def load_designed_not_built(path: Path = CONFIG_DIR / "designed_not_built.toml") -> tuple[DesignedNotBuilt, ...]:
    """Every part designed but not built, in the file's order (config/designed_not_built.toml)."""
    data = _read(path)
    _Entry(path, "the file", data).only({"items"})
    items = []
    for item in _tables(path, data, "items"):
        item.only({"key", "name", "route", "paragraph", "exists_now"})
        key = item.text("key")
        if not DESIGNED_KEY.fullmatch(key):
            item._fail("key", "must be lower case letters, digits and _")
        route = item.text("route")
        if not route.startswith("/") or route.startswith("//"):
            item._fail("route", "must be an address in the app, such as /projects/P156634")
        items.append(DesignedNotBuilt(key, item.text("name"), route, item.text("paragraph"), item.text("exists_now")))
    keys = [item.key for item in items]
    twice = sorted({key for key in keys if keys.count(key) > 1})
    if twice:
        raise ConfigError(f"In {path.name}, more than one item has the key {', '.join(twice)}. Give each its own key.")
    return tuple(items)


# ── The deck (ticket 47) ─────────────────────────────────────────────────

@dataclass(frozen=True)
class Deck:
    """Who presents the deck at /present, and on what day (config/deck.toml). None until the user fills it in."""

    presenter_name: str | None
    presentation_date: dt.date | None


def load_deck(path: Path = CONFIG_DIR / "deck.toml") -> Deck:
    """The title slide's presenter and date."""
    data = _read(path)
    _Entry(path, "the file", data).only({"presenter_name", "presentation_date"})
    name, day = data.get("presenter_name", ""), data.get("presentation_date", "")
    if not isinstance(name, str):
        raise ConfigError(f"In {path.name}, presenter_name must be text, or \"\" until it is known.")
    if not isinstance(day, str):
        raise ConfigError(f"In {path.name}, presentation_date must be a date in quotes, such as \"2026-10-30\", "
                          "or \"\" until it is known.")
    try:
        date = dt.date.fromisoformat(day.strip()) if day.strip() else None
    except ValueError as error:
        raise ConfigError(f"In {path.name}, presentation_date must be a date such as \"2026-10-30\", "
                          f"not {day!r}.") from error
    return Deck(name.strip() or None, date)
