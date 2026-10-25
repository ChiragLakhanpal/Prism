"""The recording command: it re-records every scripted case from the live agent, and prints the change as a
diff to review (spec, "Model outputs are recorded, not called, in the offline gate").

Offline, a stand-in for the live agent gives answers in other words, and the tools run on the fixture
database. On the workspace, ops/agent/record.py runs the same code with the Foundry agent and the SQL
warehouse.
"""

import copy
import datetime as dt
import json
import shutil
from contextlib import contextmanager
from pathlib import Path

import pytest

from strata.agent import record
from strata.agent.loop import output_text
from strata.agent.scripted import ScriptedAgent, load_cases
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine

FIXTURES = Path(__file__).parent / "fixtures" / "agent"


class LiveStandIn:
    """Answers as the recordings do, except that the rebidding answer's first sentence is worded anew."""

    name, version = "strata-orchestrator", "7"

    def __init__(self, recordings):
        self.recordings, self.answers = recordings, None

    def respond(self, items, previous_response_id):
        if self.answers is None:
            asked = json.loads(items[0]["content"])["question"]
            recording = next(r for r in self.recordings if r["question"] == asked)
            self.answers = copy.deepcopy(recording["responses"])
            final = self.answers[-1]["output"][0]["content"][0]
            claims = json.loads(final["text"])
            if claims["claims"] and "108 of 328" in claims["claims"][0]["sentence"]:
                claims["claims"][0]["sentence"] = ("The completion report says \"108 of 328 cases had to go "
                                                   "through rebidding\".")
            final["text"] = json.dumps(claims)
        return {**self.answers.pop(0), "usage": {"total_tokens": 1234}, "created_at": 1761200000}


@pytest.fixture
def copied(tmp_path):
    shutil.copytree(FIXTURES, tmp_path / "agent")
    return tmp_path / "agent"


def test_the_recording_command_re_records_every_case_and_shows_the_change_as_a_diff(copied, fixture_db):
    cases = load_cases(copied / "cases.toml")
    recordings = [json.loads(path.read_text()) for path in sorted((copied / "recorded").glob("*.json"))]

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    report = record.record_all(cases, lambda: LiveStandIn(recordings), engine_for,
                               Viewer(name="the env file's token"), today=dt.date(2026, 10, 24))

    assert sorted(case for done in report for case in done.cases) == sorted(cases)
    text = record.report_text(report, copied.parent)
    assert '- "recorded": false,' in text.splitlines() and '+ "recorded": true,' in text.splitlines()
    changed = [line for line in text.splitlines() if "108 of 328" in line]
    assert any(line.startswith("-") and "should have been based on the market rate" in line for line in changed)
    assert any(line.startswith("+") and "should have been based" not in line for line in changed)
    rebidding = json.loads((copied / "recorded" / "p130164-rebidding.json").read_text())
    assert (rebidding["recorded"], rebidding["recorded_on"], rebidding["agent"]) == (
        True, "2026-10-24", {"name": "strata-orchestrator", "version": "7"})
    assert "usage" not in rebidding["responses"][0]  # what changes on every call stays out of the diff
    assert json.loads(output_text(rebidding["responses"][-1]))["claims"][0]["sentence"] == (
        'The completion report says "108 of 328 cases had to go through rebidding".')
    # Every case replays from its new recording, with its plants.
    for case in load_cases(copied / "cases.toml").values():
        assert ScriptedAgent(case).responses


class LiveJudge:
    """Stands in for check 4's live judge: every sentence follows, and its answer is kept as the live one is."""

    name = "gpt-5.4"

    def __init__(self):
        self.answers = []

    def judge(self, questions):
        from strata.agent.judge import judgements

        content = {"judgements": [{"index": question.index, "follows": True, "reason": "It follows."}
                                  for question in questions]}
        self.answers.append({"id": "chatcmpl-live", "object": "chat.completion", "model": self.name,
                             "choices": [{"index": 0, "message": {"role": "assistant", "content": json.dumps(content)}}]})
        return judgements(self.answers[-1], questions)


def test_the_recording_command_re_records_the_judge_for_each_case_whose_answer_asks_it(copied, fixture_db):
    """Ticket 24: with --judge, every scripted case is replayed through the answer stream, and the live judge's
    answer is kept for each case that asks it. A case whose judge does not respond, or that never asks it, keeps
    no file."""
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    cases = load_cases(copied / "cases.toml")
    report = record.record_judged(cases, LiveJudge(), engine_for, today=dt.date(2026, 10, 24))

    judged = {done.recording for done in report}
    assert {"p130164-unsupported-summary", "p130164-summaries", "ke-nwwda-541055-advice"} <= judged
    assert {"p130164-rebidding", "p130164-judge-no-response", "refuses-supplier-scores"}.isdisjoint(judged)
    unsupported = json.loads((copied / "judged" / "p130164-unsupported-summary.json").read_text())
    assert (unsupported["recorded"], unsupported["judge"], unsupported["asked"]) == (
        True, {"deployment": "gpt-5.4"}, ["The completion report blamed the contractors for the rebidding."])
    text = record.report_text(report, copied.parent)
    assert '+ "recorded": true,' in text.splitlines()


class LiveWriter:
    """Writes the recorded notes, except that the first note's first sentence is worded anew, and checks it
    was handed the plan's rows with a signal as data."""

    name, version = "strata-review-notes-writer", "3"

    def __init__(self, recording):
        self.recording = recording
        self.asked = None

    def respond(self, items, previous_response_id):
        self.asked = json.loads(items[0]["content"])
        answer = copy.deepcopy(self.recording["responses"][0])
        notes = json.loads(answer["output"][0]["content"][0]["text"])
        notes["notes"][0]["claims"][0]["sentence"] = "The plan shows this activity as Pending Implementation."
        notes["notes"][0]["claims"][0]["numbers"] = []
        answer["output"][0]["content"][0]["text"] = json.dumps(notes)
        return {**answer, "usage": {"total_tokens": 900}}


def test_the_recording_command_re_records_each_writer_case_from_the_rows_its_workflow_reads(copied, fixture_db):
    """Ticket 35's writer cases (writers.toml) are re-recorded the same way: the workflow reads check_plan on
    the workspace, the live writer answers, and the diff shows what changed."""
    cases = load_cases(copied / "writers.toml")
    recording = json.loads((copied / "recorded" / "review-notes-nwwda-2026-10-09.json").read_text())
    writer = LiveWriter(recording)

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    report = record.record_writers(cases, lambda: writer, engine_for, Viewer(name="the env file's token"),
                                   today=dt.date(2026, 10, 23))

    [done] = report
    assert sorted(done.cases) == sorted(cases)
    assert [row["activity_reference_no"] for row in writer.asked["activities"]] == [
        "KE-NWWDA-541055-CW-RFB", "KE-NWWDA-229129-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]
    assert done.counts["sentences"] == {"written": 6, "kept": 6, "removed": 0}
    text = record.report_text(report, copied.parent)
    assert any(line.startswith("+") and "The plan shows this activity" in line for line in text.splitlines())
    written = json.loads((copied / "recorded" / "review-notes-nwwda-2026-10-09.json").read_text())
    assert (written["recorded"], written["agent"], written["question"]) == (
        True, {"name": "strata-review-notes-writer", "version": "3"}, recording["question"])
    for case in cases.values():
        assert ScriptedAgent(case).responses


class LiveReader:
    """Reads each sentence as its recording does, except that the ticket's sentence now guesses three lots, and
    keeps the message each call was given."""

    name, version = "strata-package-reader", "2"

    def __init__(self, recordings):
        self.recordings, self.asked = recordings, []

    def respond(self, items, previous_response_id):
        message = json.loads(items[0]["content"])
        self.asked.append(message)
        answer = copy.deepcopy(next(r for r in self.recordings if r["question"] == message["sentence"])["responses"][0])
        content = answer["output"][0]["content"][0]
        read = json.loads(content["text"])
        if "lots" in read.get("fields", {}):
            read["fields"]["lots"]["value"] = 3
        content["text"] = json.dumps(read)
        return {**answer, "usage": {"total_tokens": 300}}


def test_the_recording_command_re_records_each_package_reader_case_from_the_message_the_workflow_sends(copied, fixture_db):
    """Ticket 15's package reader cases (packages.toml): the live reader is sent each sentence with the package
    form's fields, as the plan-a-package workflow sends it, and the diff shows what it read differently."""
    cases = load_cases(copied / "packages.toml")
    recordings = [json.loads((copied / "recorded" / f"{case.recording}.json").read_text()) for case in cases.values()]
    reader = LiveReader(recordings)

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    report = record.record_packages(cases, lambda: reader, engine_for, Viewer(name="the env file's token"),
                                    today=dt.date(2026, 10, 24))

    assert sorted(case for done in report for case in done.cases) == sorted(cases)
    assert {message["sentence"] for message in reader.asked} == {case.question for case in cases.values()}
    assert {field["key"] for field in reader.asked[0]["fields"]} >= {"category", "description", "lots", "country"}
    assert "plan_months" not in {field["key"] for field in reader.asked[0]["fields"]}
    text = record.report_text(report, copied.parent)
    assert any(line.startswith("+") and '\\"lots\\": {\\"value\\": 3' in line for line in text.splitlines())
    written = json.loads((copied / "recorded" / "package-rural-roads-kenya.json").read_text())
    assert (written["recorded"], written["agent"]) == (True, {"name": "strata-package-reader", "version": "2"})
    for case in cases.values():
        assert ScriptedAgent(case).responses
