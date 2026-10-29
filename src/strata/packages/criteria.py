"""A planned package's criteria: one value per field of the package form schema, each with where it came
from, and how a reading, a person's change and the thresholds file set them (ticket 15).

Where a value came from (its provenance):
- sentence: the package reader read it from the person's sentence;
- default: the sentence did not say, so the field took the schema's default;
- unlisted: the sentence named a value the schema does not list, such as a method STEP has no name for, so the
  field took the schema's default, and read_as keeps the sentence's words;
- guess: the reader guessed it, for a field the schema says may be guessed, and the person has not kept it;
- computed: a computed field's value, from the thresholds file's rule;
- you: the person set it, kept a guess, or set a computed field themselves.

After every change, each computed field the person has not set is computed again. A value that changes is
listed in changed, with the field whose change caused it, until the next change.
"""

from __future__ import annotations

from dataclasses import dataclass, field as dataclass_field

from strata.config import Thresholds
from strata.packages import compute
from strata.packages.form import Field, Form, Invalid, old_method, value as checked

SENTENCE, DEFAULT, UNLISTED, GUESS, COMPUTED, YOU = "sentence", "default", "unlisted", "guess", "computed", "you"
ACTIONS = ("set", "remove", "keep", "use_computed")


@dataclass
class Criteria:
    values: dict[str, dict] = dataclass_field(default_factory=dict)  # key -> {"value": ..., "provenance": ...}
    changed: list[dict] = dataclass_field(default_factory=list)
    refusal: str | None = None
    approximate: bool = False  # the sentence gave the amount as about, around or roughly

    def get(self, key: str):
        return (self.values.get(key) or {}).get("value")

    def provenance(self, key: str) -> str | None:
        return (self.values.get(key) or {}).get("provenance")

    def plain(self) -> dict:
        return {key: entry["value"] for key, entry in self.values.items() if entry.get("value") is not None}

    def as_json(self) -> dict:
        return {"values": self.values, "changed": self.changed, "refusal": self.refusal, "approximate": self.approximate}

    @classmethod
    def from_json(cls, data: dict) -> Criteria:
        return cls(dict(data.get("values") or {}), list(data.get("changed") or []), data.get("refusal"),
                   bool(data.get("approximate")))


def _set(criteria: Criteria, key: str, value, provenance: str | None) -> None:
    criteria.values[key] = {"value": value, "provenance": provenance if value is not None else None}


def recompute(form: Form, criteria: Criteria, thresholds: Thresholds, cause: str | None) -> list[dict]:
    """Compute each computed field the person has not set, and say which values changed and why."""
    changed = []
    for field in form.fields:
        if field.source != "computed" or criteria.provenance(field.key) == YOU:
            continue
        result = compute.compute(field.rule, thresholds, criteria.plain())
        before, after = criteria.get(field.key), result.value if result else None
        _set(criteria, field.key, after, COMPUTED)
        # A value that changed, or that emptied because the thresholds give none now, is said, with its cause.
        if cause is not None and before is not None and before != after:
            changed.append({"field": field.key, "from": before, "to": after, "cause": cause})
    return changed


def from_reading(form: Form, read: dict[str, dict], dividing: bool, thresholds: Thresholds,
                 unlisted: dict[str, str] | None = None) -> Criteria:
    """The criteria from the package reader's checked values: each typed field it read is from the sentence and
    each it left out takes the schema's default; a guessed field is a guess unless the sentence said it. unlisted
    holds the words the reader gave a field that the schema does not take, such as a method STEP has no name for:
    that field takes the default too, and says the sentence named something else (ticket 15's verification round 3,
    V4)."""
    unlisted = unlisted or {}
    criteria = Criteria(refusal="dividing" if dividing else None)
    for field in form.fields:
        found = read.get(field.key)
        if field.source == "computed":
            continue
        if found is not None:
            stated = found.get("stated", True) or field.source != "guessed"
            _set(criteria, field.key, found["value"], SENTENCE if stated else GUESS)
            if field.kind == "amount":
                criteria.approximate = bool(found.get("approximate"))
        elif field.default is not None and field.key in unlisted:
            _set(criteria, field.key, field.default, UNLISTED)
            criteria.values[field.key]["read_as"] = unlisted[field.key]
        elif field.default is not None:
            _set(criteria, field.key, field.default, DEFAULT)
        else:
            _set(criteria, field.key, None, None)
    recompute(form, criteria, thresholds, cause=None)
    return criteria


def empty(form: Form) -> Criteria:
    """No criteria at all, for a person who chose to set them themselves: every chip asks for its value."""
    criteria = Criteria()
    for field in form.fields:
        _set(criteria, field.key, None, None)
    return criteria


def change(form: Form, before: Criteria, key: str, action: str, raw, thresholds: Thresholds,
           country_codes: dict[str, str], max_months: float) -> Criteria:
    """The criteria after one change by the person, with the computed fields computed again. Invalid when the
    field, the action or the value is one the schema does not take."""
    if action not in ACTIONS or not form.has(key):
        raise Invalid(f"{action} {key}")
    field: Field = form.field(key)
    after = Criteria.from_json(before.as_json())
    after.changed = []
    after.refusal = before.refusal
    if action == "set":
        _set(after, key, checked(field, raw, country_codes, max_months, thresholds), YOU)
        method = old_method(str(raw)) if field.aliases else None
        if method is not None and method.market_approach and form.has("market_approach"):
            _set(after, "market_approach", method.market_approach, YOU)
            # The old method name that set it, so the note says you chose that name, not that you set the market
            # approach (ticket 58). Setting the market approach itself writes a value with none.
            after.values["market_approach"]["via"] = str(raw).strip()
        if field.kind == "amount":
            after.approximate = False
    elif action == "remove":
        if not field.optional:
            raise Invalid(f"{key} cannot be removed")
        _set(after, key, None, None)
    elif action == "keep":
        if after.provenance(key) != GUESS:
            raise Invalid(f"{key} is not a guess")
        _set(after, key, after.get(key), YOU)
    else:
        if field.source != "computed":
            raise Invalid(f"{key} is not computed")
        after.values[key] = {"value": None, "provenance": COMPUTED}
    after.changed = recompute(form, after, thresholds, cause=key)
    return after


def view(form: Form, criteria: Criteria, thresholds: Thresholds) -> dict:
    """The criteria as the package workspace shows them: each field in the schema's order with its value, where
    it came from and, for a computed field, what the thresholds give; the rules behind the computed values;
    the find_comparables arguments the fields that pick comparables give; and the ones still missing."""
    plain = criteria.plain()
    fields, rules, query, missing = [], {}, {}, []
    for field in form.fields:
        result = compute.compute(field.rule, thresholds, plain) if field.source == "computed" else None
        if result is not None:
            rules[field.rule] = result.rule
        fields.append({"key": field.key, "group": field.group, "value": criteria.get(field.key),
                       "provenance": criteria.provenance(field.key),
                       "computed": result.value if result else None,
                       # The sentence's own words for a value the schema does not list.
                       **({"read_as": criteria.values[field.key].get("read_as")}
                          if criteria.provenance(field.key) == UNLISTED else {}),
                       # The old method name that set a value, when one did (ticket 58).
                       **({"via": criteria.values[field.key]["via"]}
                          if criteria.values.get(field.key, {}).get("via") else {})})
        if field.picks:
            if criteria.get(field.key) is None:
                missing.append(field.key)
            else:
                query[field.picks] = criteria.get(field.key)
    return {"fields": fields, "guesses": sum(1 for entry in fields if entry["provenance"] == GUESS),
            "rules": rules, "changed": criteria.changed, "refusal": criteria.refusal,
            "approximate": criteria.approximate, "comparables_query": query if not missing else None,
            "missing": missing}
