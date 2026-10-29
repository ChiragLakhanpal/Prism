"""The package reader: one structured call to the drafting model that reads a sentence into the package form's
fields (ticket 15; config/agents.toml, package_reader).

message() is what the reader is sent: data only, since its rules live in its instructions (Prompt Shields
refuses data that holds rules). It names each field the schema asks for, with its kind and, for a choice,
its values, so a field added to the schema is asked for with no other change. read() checks the answer:
each value must pass the schema's own check (strata.packages.form.value), and a value that does not is left
out, so the chip asks the person for it instead of showing something the schema does not hold.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field

from strata.agent.claims import ClaimsError
from strata.config import Thresholds
from strata.packages.form import Form, Invalid, text_limit, value as checked

log = logging.getLogger("strata.packages")


@dataclass(frozen=True)
class Reading:
    package: bool
    dividing: bool
    values: dict[str, dict]  # key -> {"value": ..., "stated": bool, "approximate": bool}
    # key -> the words the reader gave a choice the schema does not list, such as a method STEP has no name for
    unlisted: dict[str, str] = field(default_factory=dict)


def message(sentence: str, form: Form) -> dict:
    fields = []
    for field in form.fields:
        if not field.asked:
            continue
        entry = {"key": field.key, "kind": field.kind}
        if field.kind == "choice":
            entry["values"] = [option.value for option in field.options]
        if field.source == "guessed":
            entry["may_guess"] = True
        fields.append(entry)
    return {"task": "read_package", "sentence": sentence, "fields": fields}


def read(text: str, form: Form, country_codes: dict[str, str], max_months: float, thresholds: Thresholds) -> Reading:
    """The reader's answer, checked against the schema and the thresholds file's limits. ClaimsError when it is not
    the JSON its instructions ask for."""
    try:
        answer = json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ClaimsError(f"The package reader's answer is not JSON: {error}.") from error
    if not isinstance(answer, dict) or not isinstance(answer.get("package"), bool):
        raise ClaimsError("The package reader's answer must be an object that says whether it found a package.")
    given = answer.get("fields") or {}
    if not isinstance(given, dict):
        raise ClaimsError("The package reader's fields must be an object.")
    values, unlisted = {}, {}
    for key, entry in given.items():
        if not form.has(key) or not form.field(key).asked or not isinstance(entry, dict):
            continue
        chosen = form.field(key)
        try:
            kept = checked(chosen, entry.get("value"), country_codes, max_months, thresholds)
        except Invalid:
            log.info("The package reader gave %s a value the schema does not take; the chip will ask for it.", key)
            words = entry.get("value")
            if chosen.kind == "choice" and isinstance(words, str) and words.strip():
                unlisted[key] = " ".join(words.split())[:text_limit(thresholds)]
            continue
        values[key] = {"value": kept, "stated": bool(entry.get("stated", True)),
                       "approximate": bool(entry.get("approximate", False))}
    found = answer["package"]
    return Reading(found, bool(answer.get("dividing", False)), values if found else {}, unlisted if found else {})
