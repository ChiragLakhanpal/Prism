"""The registry and config files for the change drill, each read through one function.

Each file in config/ is one of the spec's single places ("Ten single places"), so a change
request lands in one file (CLAUDE.md rule 9). This module reads six of them:

- load_sources()     config/sources.toml, the source registry
- load_slice()       config/slice.toml, the slice file
- load_sectors()     config/sectors.toml, the one sector taxonomy
- load_models()      config/models.toml, the model file (load_layout_parser() reads its [layout] table,
                     and load_search() its [search] table)
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
    known_gaps: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    indicators: tuple[str, ...] = ()
    countries: tuple[Country, ...] = ()

    @property
    def paged(self) -> bool:
        """Whether the nightly job fetches this source page by page."""
        return self.api is not None


SOURCE_REQUIRED = ("dataset_name", "endpoint", "watermark_field", "cadence", "license", "silver_transform")
SOURCE_PAGING = ("api", "records", "page_size", "fixture_dataset", "scope")  # all of them or none
SOURCE_OPTIONAL = ("dataset_id", "resource_id", "stratum", "country_filter")
SOURCE_LISTS = ("ignore_keys", "known_gaps", "limitations", "indicators")


def load_sources(path: Path = CONFIG_DIR / "sources.toml",
                 slice_path: Path = CONFIG_DIR / "slice.toml") -> dict[str, Source]:
    """Every source in the registry, by its key. A source fetched for the slice countries carries
    the countries of the slice file at slice_path."""
    data = _read(path)
    _Entry(path, "the file", data).only({"sources"})
    sources = {}
    for key, table in data.get("sources", {}).items():
        entry = _Entry(path, f"sources.{key}", table)
        entry.only(set(SOURCE_REQUIRED + SOURCE_PAGING + SOURCE_OPTIONAL + SOURCE_LISTS))
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
        sources[key] = Source(key=key, **fields)
    return sources


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


@dataclass(frozen=True)
class ShelfItem:
    """One document on the stress shelf. Without a project_id it is a slot still to fill."""

    why: str
    project_id: str | None = None
    document_type: str | None = None


@dataclass(frozen=True)
class Slice:
    countries: tuple[Country, ...]
    sectors: tuple[str, ...]
    first_fiscal_year: int
    last_fiscal_year: int
    showcase: Showcase
    demo_plan: DemoPlan
    stress_shelf: tuple[ShelfItem, ...]

    @property
    def fiscal_years(self) -> range:
        return range(self.first_fiscal_year, self.last_fiscal_year + 1)


def load_slice(path: Path = CONFIG_DIR / "slice.toml") -> Slice:
    """The document slice, the showcase project, the demo plan and the stress shelf."""
    data = _read(path)
    top = _Entry(path, "the file", data)
    top.only({"first_fiscal_year", "last_fiscal_year", "sectors", "countries", "showcase", "demo_plan",
              "stress_shelf"})

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

    shelf = []
    for entry in _tables(path, data, "stress_shelf"):
        entry.only({"project_id", "document_type", "why"})
        shelf.append(ShelfItem(why=entry.text("why"), project_id=entry.project_id("project_id", required=False),
                               document_type=entry.text("document_type", required=False)))

    return Slice(
        countries=tuple(countries),
        sectors=sectors,
        first_fiscal_year=first,
        last_fiscal_year=last,
        showcase=Showcase(showcase.project_id("project_id"), showcase.text("name")),
        demo_plan=DemoPlan(plan.project_id("project_id"), plan.text("project_name"),
                           plan.text("implementing_agency"), plan.text("agency_short_name"), plan.date("plan_date")),
        stress_shelf=tuple(shelf),
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
    _Entry(path, "the file", data).only({"roles", "layout", "search"})
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
    entry.only({"parser"})
    return entry.text("parser")


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
    abstentions_with_rows: tuple[str, ...] = ()  # the abstentions that still come with rows
    summary_fields: tuple[str, ...] = ()  # the derived figures returned as one citable record, the summary


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
        entry.only({"description", "adapter", "benchmark", "sources", "parameters", "result"})
        adapter = entry.text("adapter")
        if not ADAPTER.fullmatch(adapter):
            entry._fail("adapter", f"must name a function as module:function, such as strata.tools.{name}:{name}")
        tools[name] = Tool(name=name, description=entry.text("description"), adapter=adapter,
                           benchmark=entry.text("benchmark"), sources=entry.texts("sources"),
                           parameters=parameters, result=result)
    return tools


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
    entry.only({"row", "row_fields", "source_fields", "fields", "reasons", "abstentions", "abstentions_with_rows",
                "summary_fields"})
    result = ToolResult(entry.text("row"), entry.texts("row_fields"), entry.texts("source_fields"),
                        entry.texts("fields"), entry.texts("reasons"), entry.texts("abstentions"),
                        entry.texts("abstentions_with_rows"), entry.texts("summary_fields"))
    # A summary carries the tool's own fields, and the coverage line's counts, which every result has.
    strays = [field for field in result.summary_fields if field not in (*result.fields, "coverage")]
    if strays:
        entry._fail("summary_fields", f"names {', '.join(strays)}, which fields does not list")
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
