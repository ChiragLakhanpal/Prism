"""Values for the package form schema (config/package_form.toml; spec, "Ten single places", item 7).

strata.config.load_package_form() reads the schema, as every registry is read: its groups, in the card's order,
and its fields, each with its group, kind, source (typed, computed or guessed), STEP field name and the
find_comparables parameter it sets, if any. payload() hands it to the package workspace with the limits below.

value() is the one check a value passes before it is kept, whether the package reader or the person gave
it: a choice is one of its options (an old method name, such as ICB, maps to the Procurement Regulations'
name and the market approach it says, through strata.lakehouse.clean's OLD_METHODS); a country is a code
in the World Bank's country list; an amount, a count and a plan's months are numbers in their range.
"""

from __future__ import annotations

import math

from strata.config import FormField, PackageForm
from strata.lakehouse import clean

# The schema's own types, by their short names here.
Field = FormField
Form = PackageForm
# The limits a person's values must keep, each defined once here and handed to the package workspace in the
# form's payload, so the browser checks the same ones (CLAUDE.md rule 4).
TEXT_LIMIT = 200
MAX_COUNT = 99


class Invalid(ValueError):
    """A value a field does not take."""


def payload(form: PackageForm, countries: list[dict], max_months: float) -> dict:
    """The schema as the package workspace reads it, with the World Bank's country list, the old method names a
    method chip takes, and the limits a person's values must keep: the longest plan, the most lots and the
    longest description."""
    return {"groups": [{"key": g.key, "label": g.label, "name": g.name} for g in form.groups],
            "fields": [field.as_dict() for field in form.fields],
            "countries": countries,
            "aliases": {name: {"method": method.name, "market_approach": method.market_approach}
                        for name, method in clean.OLD_METHODS.items()},
            "max_months": max_months, "max_count": MAX_COUNT, "text_limit": TEXT_LIMIT}


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
