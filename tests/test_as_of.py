"""The as-of date at seam 3, the answer contract (ticket 40; ADR 0002).

The page's as-of date goes with every tool call the answer makes. The app sets it from the request, and a date the
agent writes into a call's arguments is replaced, and the replacement is noted in the run's record, so the model never
chooses what was public. The scripted case p130164-as-of-isr-7 asks about P130164's status reports as of August 26,
2016, the day ISR 7 was archived (values.toml, isr-7-date) and disclosed (its disclosure_date, recorded in
api/documents/P130164.json). The completion report became public on November 2, 2019 (icr-disclosed), so no ICR
passage comes back, and check 6 finds no disagreement with ISR 7, because the ICR paragraph that disagrees was not
public yet.
"""

import json
import tomllib
from pathlib import Path

from scripted_answers import ask

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ISR_7 = TRUTH["isr-7-date"]["value"]
ICR = "31525018"  # the completion report's document id (values.toml, icr-disclosed: documents.D31525018)


class Kept:
    """The run log, keeping each run's row as the server writes it to strata.ops.agent_runs."""

    def __init__(self):
        self.rows: list[dict] = []

    def record(self, row: dict) -> None:
        self.rows.append(row)


def test_every_tool_call_of_the_scripted_answer_ran_as_of_the_page_date_and_no_icr_passage_came_back(fixture_db):
    assert TRUTH["icr-disclosed"]["value"] > ISR_7
    runs = Kept()

    asked = ask(fixture_db, "p130164-as-of-isr-7", runs=runs)

    (row,) = runs.rows
    calls = json.loads(row["tool_calls"])
    assert row["as_of"] == ISR_7
    assert [(call["tool"], call["as_of"]) for call in calls] == [("search_passages", "2016-08-26")] * 2
    # The agent wrote a later date into its first search. The app replaced it and the run's record says so.
    assert calls[0]["as_of_replaced"] == "2026-10-23" and "as_of_replaced" not in calls[1]
    # The search of the completion reports found nothing public on that date.
    assert (calls[1]["rows"], calls[1]["abstention"]) == (0, "no_match")
    shown = [data["id"] for data in asked.of("evidence")]
    assert shown and not any(f":{ICR}/" in evidence for evidence in shown)
    assert asked.of("disagreement") == []
    assert [data["text"] for data in asked.of("sentence")] == [
        "The status report of August 26, 2016 rated progress towards the project development objective (PDO) "
        "\"Satisfactory\"."]
