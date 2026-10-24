"""The package form schema (config/package_form.toml; spec, "Ten single places", item 7).

load_form() reads the schema once: its groups, in the card's order, and its fields, each with its group, kind,
source (typed, computed or guessed), STEP field name and the find_comparables parameter it sets, if any.
Nothing else in Strata names a field, so adding an entry to the file adds a chip and removing one removes it.

value() is the one check a value passes before it is kept, whether the package reader or the person gave
it: a choice is one of its options (an old method name, such as ICB, maps to the Procurement Regulations'
name and the market approach it says, through strata.lakehouse.clean's OLD_METHODS); a country is a code
in the World Bank's country list; an amount, a count and a plan's months are numbers in their range.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from strata.config import CONFIG_DIR, ConfigError, _read
from strata.lakehouse import clean

KINDS = ("choice", "text", "amount", "count", "country", "months")
SOURCES = ("typed", "computed", "guessed")
RULES = ("review", "market_approach")
FIELD_KEYS = {"key", "group", "kind", "source", "label", "add_label", "step_field", "picks", "default", "options",
              "rule", "optional", "asked", "unit", "unit_one", "aliases"}
TEXT_LIMIT = 200
MAX_COUNT = 99


class Invalid(ValueError):
    """A value a field does not take."""


@dataclass(frozen=True)
class Option:
    value: str
    label: str


@dataclass(frozen=True)
class Group:
    key: str
    label: str
    name: str


@dataclass(frozen=True)
class Field:
    key: str
    group: str
    kind: str
    source: str
    label: str
    add_label: str
    step_field: str | None = None
    picks: str | None = None
    default: str | None = None
    options: tuple[Option, ...] = ()
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
class Form:
    groups: tuple[Group, ...]
    fields: tuple[Field, ...]

    def field(self, key: str) -> Field:
        for field in self.fields:
            if field.key == key:
                return field
        raise KeyError(key)

    def has(self, key: str) -> bool:
        return any(field.key == key for field in self.fields)

    def payload(self, countries: list[dict], max_months: float) -> dict:
        """The schema as the package workspace reads it, with the World Bank's country list, the old method
        names a method chip takes, and the longest plan a person can type."""
        return {"groups": [{"key": g.key, "label": g.label, "name": g.name} for g in self.groups],
                "fields": [field.as_dict() for field in self.fields],
                "countries": countries,
                "aliases": {name: {"method": method.name, "market_approach": method.market_approach}
                            for name, method in clean.OLD_METHODS.items()},
                "max_months": max_months}


def load_form(path: Path = CONFIG_DIR / "package_form.toml") -> Form:
    """The package form schema, checked: each field in a group the file defines, with a kind, a source and, for a
    computed field, a rule the thresholds file has."""
    data = _read(path)
    def fail(where: str, need: str):
        raise ConfigError(f"In {path.name}, {where} {need}.")

    groups = []
    for key, table in (data.get("groups") or {}).items():
        if not isinstance(table, dict) or not table.get("label") or not table.get("name"):
            fail(f"groups.{key}", "needs a label and a name")
        groups.append(Group(key, str(table["label"]), str(table["name"])))
    if not groups:
        fail("the file", "needs [groups]")
    group_keys = {group.key for group in groups}
    fields, seen = [], set()
    for number, table in enumerate(data.get("fields") or [], 1):
        where = f"field {number} ({table.get('key', 'no key')})"
        unknown = set(table) - FIELD_KEYS
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
        if table["kind"] not in KINDS:
            fail(where, f"has the kind {table['kind']}; the kinds are {', '.join(KINDS)}")
        if table["source"] not in SOURCES:
            fail(where, f"has the source {table['source']}; the sources are {', '.join(SOURCES)}")
        options = tuple(Option(str(o["value"]), str(o["label"])) for o in table.get("options") or [])
        if table["kind"] == "choice" and not options:
            fail(where, "is a choice with no options")
        if table["source"] == "computed" and table.get("rule") not in RULES:
            fail(where, f"is computed, so it needs a rule: {', '.join(RULES)}")
        if table.get("default") is not None and options and table["default"] not in {o.value for o in options}:
            fail(where, "has a default that is not one of its options")
        fields.append(Field(
            key=table["key"], group=table["group"], kind=table["kind"], source=table["source"], label=table["label"],
            add_label=table["add_label"], step_field=table.get("step_field"), picks=table.get("picks"),
            default=table.get("default"), options=options, rule=table.get("rule"),
            optional=bool(table.get("optional", False)), asked=bool(table.get("asked", table["source"] != "computed")),
            unit=table.get("unit"), unit_one=table.get("unit_one"), aliases=bool(table.get("aliases", False))))
    return Form(tuple(groups), tuple(fields))


# ── Values ───────────────────────────────────────────────────────────────

def _number(raw) -> float:
    if isinstance(raw, bool) or not isinstance(raw, int | float) or not math.isfinite(raw):
        raise Invalid("not a number")
    return float(raw)


def old_method(text: str) -> clean.Method | None:
    """What an old method name, such as ICB or Shopping, is now, or None for any other text."""
    key = " ".join(str(text).split()).upper()
    return clean.OLD_METHODS.get(key)


def value(field: Field, raw, country_codes: dict[str, str], max_months: float):
    """The value a field keeps for this input, in STEP's words for a choice, or Invalid."""
    if raw is None:
        raise Invalid("no value")
    if field.kind == "choice":
        text = " ".join(str(raw).split()).casefold()
        for option in field.options:
            if text in (option.value.casefold(), option.label.casefold()):
                return option.value
        if field.aliases and (method := old_method(str(raw))) is not None:
            return method.name
        raise Invalid("not one of the options")
    if field.kind == "text":
        text = " ".join(str(raw).split())
        if not text or len(text) > TEXT_LIMIT:
            raise Invalid("no words, or too many")
        return text[0].upper() + text[1:]
    if field.kind == "amount":
        amount = _number(raw)
        if amount <= 0:
            raise Invalid("not above zero")
        return round(amount, 2) if amount != int(amount) else int(amount)
    if field.kind == "count":
        count = _number(raw)
        if count != int(count) or not 1 <= count <= MAX_COUNT:
            raise Invalid("not a whole number in range")
        return int(count)
    if field.kind == "country":
        code = str(raw).strip()
        if code.upper() in country_codes:
            return code.upper()
        for known, name in country_codes.items():
            if code.casefold() == name.casefold():
                return known
        raise Invalid("not in the World Bank's country list")
    months = _number(raw)
    if not 0.5 <= months <= max_months or round(months, 1) != months:
        raise Invalid("not a plan in range")
    return months
