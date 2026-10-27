"""Disagreements planted at the tool, for the tests of check 6 on the answer paths that run it (ticket 61): the risk
table, the lesson review writer and the check-your-criteria section. Each is get_disagreements' own answer on the
fixture, with one more disagreement about P130164 whose first side is ICR P130164 paragraph 54 (values.toml
icr-para-54) against ISR 7's side of the fixture's real one. A test puts one in the registry with
with_adapter(name), and the criteria recorder (tests/record_criteria_api.py) records a made-up answer with it.
"""

import dataclasses
import tomllib
from pathlib import Path

from strata.config import load_tools
from strata.tools.get_disagreements import get_disagreements

ICR_54 = "strata.gold.passage:31525018/v1/54"
ISR_7 = "strata.gold.passage:26733307/v1/s4"
PLANTED = "strata.gold.disagreement:planted"
PLANTED_TOO = "strata.gold.disagreement:planted-too"
QUOTE = next(entry["value"] for entry in tomllib.loads(
    (Path(__file__).parent / "ground_truth" / "values.toml").read_text())["value"] if entry["id"] == "icr-para-54")


def _plant(result: dict, **side) -> dict:
    if result["rows"]:
        real = result["rows"][0]
        first = {**real["sides"][1], "evidence_id": ICR_54, "passage_id": "31525018/v1/54",
                 "assertion_id": f"{ICR_54}#P130164/rebidding", **side}
        planted = {**real, "evidence_id": PLANTED, "disagreement_id": "planted", "attribute": "rebidding",
                   "sides": [first, real["sides"][0]], "lean_assertion_id": first["assertion_id"],
                   "other_assertion_id": real["sides"][0]["assertion_id"]}
        result["rows"] = [*result["rows"], planted]
    return result


def quoting_icr_54(call, **arguments):
    """The first side quotes paragraph 54's own words, "108 of 328 cases had to go through rebidding"."""
    return _plant(get_disagreements(call, **arguments), value=None, value_form=None, quote=QUOTE)


def _twice(result: dict) -> dict:
    """The planted disagreement and a second one with the same first side, about the rebidding share, so check 6
    attaches two cards to the same sentence (ticket 61's verify, F1)."""
    if result["rows"]:
        first = result["rows"][-1]
        side = {**first["sides"][0], "assertion_id": f"{ICR_54}#P130164/rebidding_share"}
        second = {**first, "evidence_id": PLANTED_TOO, "disagreement_id": "planted-too", "attribute": "rebidding_share",
                  "sides": [side, first["sides"][1]], "lean_assertion_id": side["assertion_id"]}
        result["rows"] = [*result["rows"], second]
    return result


def twice_quoting_icr_54(call, **arguments):
    """Two disagreements whose first side quotes paragraph 54's own words."""
    return _twice(quoting_icr_54(call, **arguments))


def on_market_rates(call, **arguments):
    """The first side judges the works estimates by "market rates", words the risk table's lesson states."""
    return _plant(get_disagreements(call, **arguments), value="market rates", value_form="judgment", quote=None)


def twice_on_market_rates(call, **arguments):
    """Two disagreements whose first side judges the works estimates by "market rates"."""
    return _twice(on_market_rates(call, **arguments))


def with_adapter(name: str) -> dict:
    """The tool registry with get_disagreements answering through one of the planters above."""
    tools = load_tools()
    tools["get_disagreements"] = dataclasses.replace(tools["get_disagreements"], adapter=f"planted_disagreements:{name}")
    return tools
