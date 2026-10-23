"""The registry and config files for the change drill, each read through one function.

Each file in config/ is one of the spec's single places ("Ten single places"), so a change
request lands in one file (CLAUDE.md rule 9). This module reads four of them:

- load_sources()     config/sources.toml, the source registry
- load_slice()       config/slice.toml, the slice file
- load_models()      config/models.toml, the model file
- load_thresholds()  config/thresholds.toml, the thresholds file

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


# ── The source registry ──────────────────────────────────────────────────

CADENCES = ("daily", "weekly", "monthly", "quarterly", "yearly", "frozen")
STRATA = ("What", "How", "Why")


@dataclass(frozen=True)
class Source:
    """One data source: where it answers, how often it changes, and how it is credited."""

    key: str
    dataset_name: str
    endpoint: str
    watermark_field: str
    cadence: str
    license: str
    silver_transform: str
    dataset_id: str | None = None
    resource_id: str | None = None
    stratum: str | None = None
    known_gaps: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()


SOURCE_REQUIRED = ("dataset_name", "endpoint", "watermark_field", "cadence", "license", "silver_transform")
SOURCE_OPTIONAL = ("dataset_id", "resource_id", "stratum")
SOURCE_LISTS = ("known_gaps", "limitations")


def load_sources(path: Path = CONFIG_DIR / "sources.toml") -> dict[str, Source]:
    """Every source in the registry, by its key."""
    data = _read(path)
    _Entry(path, "the file", data).only({"sources"})
    sources = {}
    for key, table in data.get("sources", {}).items():
        entry = _Entry(path, f"sources.{key}", table)
        entry.only(set(SOURCE_REQUIRED + SOURCE_OPTIONAL + SOURCE_LISTS))
        fields = {name: entry.text(name) for name in SOURCE_REQUIRED}
        fields |= {name: entry.text(name, required=False) for name in SOURCE_OPTIONAL}
        fields |= {name: entry.texts(name) for name in SOURCE_LISTS}
        if fields["cadence"] not in CADENCES:
            entry._fail("cadence", f"must be one of {', '.join(CADENCES)}")
        if fields["stratum"] is not None and fields["stratum"] not in STRATA:
            entry._fail("stratum", f"must be one of {', '.join(STRATA)}")
        sources[key] = Source(key=key, **fields)
    return sources


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


def _tables(path: Path, data: dict, key: str) -> list[_Entry]:
    tables = data.get(key, [])
    if not isinstance(tables, list):
        raise ConfigError(f"In {path.name}, write each of {key} as a [[{key}]] table.")
    return [_Entry(path, f"{key}[{number}]", table) for number, table in enumerate(tables, 1)]


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
    _Entry(path, "the file", data).only({"roles"})
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
        models[role] = Model(role, entry.text("deployment"), entry.text("purpose"),
                             entry.integer("dimensions", required=False))
    return models


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
