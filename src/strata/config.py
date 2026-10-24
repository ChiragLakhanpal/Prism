"""The registry and config files for the change drill, each read through one function.

Each file in config/ is one of the spec's single places ("Ten single places"), so a change
request lands in one file (CLAUDE.md rule 9). This module reads six of them:

- load_sources()     config/sources.toml, the source registry
- load_slice()       config/slice.toml, the slice file
- load_sectors()     config/sectors.toml, the one sector taxonomy
- load_models()      config/models.toml, the model file (load_layout_parser() reads its [layout] table,
                     load_search() its [search] table, and load_supplier_matching() its
                     [supplier_matching] table)
- load_thresholds()  config/thresholds.toml, the thresholds file
- load_tools()       config/tools.toml, the tool registry (strata.tools.registry calls the tools)
- load_agent()       config/agents.toml, the agent registry: one Foundry agent and its guardrail
                     (strata.agent.definition builds the agent's definition from it)

Each function checks the file's shape and raises ConfigError with a sentence that names the
file, the entry and the fix. It uses only the standard library, so the nightly job can call it.
"""

from __future__ import annotations

import datetime as dt
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
PROJECT_ID = re.compile(r"P\d{6}")


class ConfigError(ValueError):
    """A config file that does not follow its shape, with what to change."""


def _read(path: Path) -> dict:
    try:
        with open(path, "rb") as handle:
            return tomllib.load(handle)
    except FileNotFoundError as error:
        raise ConfigError(f"I could not find {path}.") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{path.name} is not valid TOML: {error}.") from error


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
    projects: str | None = None  # for a document collection's coverage: the measure that counts its projects


@dataclass(frozen=True)
class ReadinessRoute:
    """One way a reader reads a source's pages, whose pages read well the dashboard charts by route."""

    measure: str  # the measure in strata.ops.data_readiness that counts the pages it read well
    label: str  # its name on the dashboard's chart, such as "Layout parser (Route B)"
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
    fixture_dataset: str | None = None
    dataset_id: str | None = None
    resource_id: str | None = None
    stratum: str | None = None
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
SOURCE_OPTIONAL = ("dataset_id", "resource_id", "stratum", "country_filter")
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
        fields |= {name: entry.text(name, required=False) for name in SOURCE_OPTIONAL}
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
    entry.only({"measure", "counts", "noun", "counted_in", "lack", "years", "counts_one", "noun_one", "projects"})
    return ReadinessColumn(entry.text("measure"), entry.text("counts"), entry.text("noun"), entry.text("counted_in"),
                           entry.text("lack", required=False), entry.text("years", required=False),
                           entry.text("counts_one", required=False), entry.text("noun_one", required=False),
                           entry.text("projects", required=False))


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
                  *READINESS_COLUMNS})
        row_stratum = row.text("stratum", required=False) or stratum
        if row_stratum not in STRATA:
            row._fail("stratum", f"must be one of {', '.join(STRATA)}, here or on the source")
        schedule = row.text("schedule", required=False)
        if schedule not in (None, AS_PUBLISHED):
            row._fail("schedule", f'can only be "{AS_PUBLISHED}"; leave it out to use the source\'s cadence')
        published_as = row.text("published_as", required=False)
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
                                 published_as=published_as))
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
        collection.only({"name", "publisher", "origin"})
        collections.append(Collection(collection.text("name"), collection.text("publisher"), collection.text("origin")))
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
class Showcase:
    project_id: str
    name: str


@dataclass(frozen=True)
class DemoPlan:
    """The published Procurement Plan that "Check a plan" opens in the demo."""

    project_id: str
    project_name: str
    implementing_agency: str
    agency_short_name: str
    plan_date: dt.date


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
              "stress_shelf", "planned_projects", "notice_types"})

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
    plan.only({"project_id", "project_name", "implementing_agency", "agency_short_name", "plan_date"})

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
                           plan.text("implementing_agency"), plan.text("agency_short_name"), plan.date("plan_date")),
        stress_shelf=tuple(shelf),
        planned_projects=top.integer("planned_projects", required=False),
        notice_types=top.texts("notice_types"),
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
    _Entry(path, "the file", data).only({"roles", "layout", "search", "supplier_matching"})
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
class SearchSettings:
    """How search_passages ranks on the workspace: the AI Search index and the reranker it runs."""

    index: str  # the Delta Sync index over strata.gold.passage, by its three-part name
    reranker: str  # the model AI Search reranks the best hits with
    rerank_columns: tuple[str, ...]  # the columns of each passage the reranker reads


def load_search(path: Path = CONFIG_DIR / "models.toml") -> SearchSettings:
    """The AI Search index and the reranker search_passages uses on the workspace."""
    entry = _Entry(path, "search", _read(path).get("search"))
    entry.only({"index", "reranker", "rerank_columns"})
    return SearchSettings(entry.text("index"), entry.text("reranker"), entry.texts("rerank_columns"))


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
ROW_CONTRACT = ("evidence_id", "public_from", "source")  # spec, seam 2: every row carries these
ADAPTER = re.compile(r"[a-z_][a-z0-9_.]*:[a-z_][a-z0-9_]*")
TOOL_NAME = re.compile(r"[a-z][a-z0-9_]*")


@dataclass(frozen=True)
class ToolParameter:
    name: str
    type: str
    required: bool
    description: str


@dataclass(frozen=True)
class ToolResult:
    """The shape of what a tool returns beside the envelope every tool shares."""

    row: str
    row_fields: tuple[str, ...]
    source_fields: tuple[str, ...]
    fields: tuple[str, ...]
    reasons: tuple[str, ...] = ()  # the codes a reason in a row's marks may have
    abstentions: tuple[str, ...] = ()  # the reasons the tool may give for returning no rows


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
        entry.only({"description", "adapter", "benchmark", "sources", "parameters", "result", "readiness"})
        adapter = entry.text("adapter")
        if not ADAPTER.fullmatch(adapter):
            entry._fail("adapter", f"must name a function as module:function, such as strata.tools.{name}:{name}")
        tools[name] = Tool(name=name, description=entry.text("description"), adapter=adapter,
                           benchmark=entry.text("benchmark"), sources=entry.texts("sources"),
                           parameters=parameters, result=result, readiness=_tool_readiness(path, name, table))
    return tools


def _tool_readiness(path: Path, name: str, table: dict) -> ToolReadiness | None:
    if "readiness" not in table:
        return None
    entry = _Entry(path, f"tools.{name}.readiness", table["readiness"])
    entry.only({"kind", "ready_for", "draws_on"})
    ready_for = _Entry(path, f"tools.{name}.readiness.ready_for", entry.table.get("ready_for"))
    ready_for.only({"row", "measure", "counted_in"})
    draws_on = entry.texts("draws_on")
    if ready_for.text("row") not in draws_on:
        ready_for._fail("row", "must be one of the rows in draws_on")
    return ToolReadiness(entry.text("kind"), ready_for.text("row"), ready_for.text("measure"), draws_on,
                         ready_for.text("counted_in", required=False))


def _tool_parameters(path: Path, name: str, table: dict) -> tuple[ToolParameter, ...]:
    parameters = []
    for entry in _tables(path, table, "parameters"):
        entry.where = f"tools.{name}.{entry.where}"
        entry.only({"name", "type", "required", "description"})
        parameter = ToolParameter(entry.text("name"), entry.text("type"), entry.boolean("required"),
                                  entry.text("description"))
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
    entry.only({"row", "row_fields", "source_fields", "fields", "reasons", "abstentions"})
    result = ToolResult(entry.text("row"), entry.texts("row_fields"), entry.texts("source_fields"),
                        entry.texts("fields"), entry.texts("reasons"), entry.texts("abstentions"))
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


def load_agent(key: str, path: Path = CONFIG_DIR / "agents.toml") -> AgentSpec:
    """One agent of the agent registry, with its guardrail and the Foundry API versions."""
    data = _read(path)
    _Entry(path, "the file", data).only({"agents", "guardrails", "foundry"})
    agents, guardrails = data.get("agents", {}), data.get("guardrails", {})
    if key not in agents:
        raise ConfigError(f"{path.name} has no agent {key}. It has {', '.join(agents) or 'none'}.")
    entry = _Entry(path, f"agents.{key}", agents[key])
    entry.only({"name", "role", "instructions", "guardrail", "description"})
    role = entry.text("role")
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
                     foundry.text("api_version"), foundry.text("rai_policy_api_version"))
