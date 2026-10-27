"""The answer contract at seam 3: a question goes in over HTTP and a checked, cited answer streams back.

The scripted agent replays the Foundry agent's recorded answers (tests/fixtures/agent), and every tool
it asks for runs through the tool registry on the fixture database, as the viewer. The verifier runs in
the stream on every answer. Expected passages, numbers and quotes come from the ICR of October 10, 2019
(tests/ground_truth/values.toml, icr-para-54), never from the code under test.
"""

import asyncio
import dataclasses
import datetime as dt
import json
import re
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.agent.judge import Judgement
from strata.agent.loop import answer_runner
from strata.agent.runs import RunLog
from strata.agent.scripted import (RECORDED_STREAMS, ScriptedAgent, ScriptedJudge, failed_stream_text, load_cases,
                                   stream_text)
from strata.config import load_thresholds, load_tools
from strata.harness.turn import Event, RunError, TraceIds
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine, EngineError
from strata.reader.passages import TABLE_SUMMARY
from strata.server.app import create_app
from strata.tools.check_plan import check_plan
from strata.tools.estimate_time import estimate_time
from strata.tools.search_passages import search_passages

RECORDED = Path(__file__).parent / "fixtures" / "api"
TRUTH = tomllib.loads((Path(__file__).parent / "ground_truth" / "values.toml").read_text())
ICR_54 = "strata.gold.passage:31525018/v1/54"
TODAY = dt.date(2026, 10, 23)
ANA = {
    "X-Forwarded-Email": "ana.example@worldbank.org",
    "X-Forwarded-Preferred-Username": "Ana Example",
    "X-Forwarded-User": "4021@1984",
    "X-Forwarded-Access-Token": "token-for-ana-only",
}


def events(body):
    """The stream's (type, data) pairs, in order, without its keep-alive comments."""
    parsed = []
    for block in body.strip().split("\n\n"):
        kind, data = "message", None
        for line in block.splitlines():
            if line.startswith("event: "):
                kind = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if data is not None:
            parsed.append((kind, data))
    return parsed


def of(parsed, kind):
    return [data for found, data in parsed if found == kind]


@pytest.fixture
def ask_case(fixture_db):
    """Ask a scripted case's question over HTTP. Returns the stream's events and the scripted agent."""
    def ask(case_id, asof=None, today=TODAY, **app_options):
        case = load_cases()[case_id]
        agents = []

        def agent_for(turn):
            agents.append(ScriptedAgent(case))
            return agents[-1]

        @contextmanager
        def engine_for(viewer):
            with DuckDBEngine.open(fixture_db, read_only=True) as engine:
                yield engine

        app = create_app(runner=answer_runner(agent_for, engine_for, today=lambda: today), engine_for=engine_for,
                         judge=ScriptedJudge(case), new_run_id=lambda: "run-0001", **app_options)

        async def go():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                return await client.post("/api/ask", headers=ANA, json={
                    "question": case.question, "scope": case.scope, "asof": (asof or case.as_of).isoformat()})

        response = asyncio.run(go())
        assert response.status_code == 200
        return events(response.text), agents[0]
    return ask


def test_the_p130164_question_streams_steps_then_an_answer_citing_icr_paragraph_54(ask_case):
    parsed, _ = ask_case("p130164-rebidding")

    kinds = [kind for kind, _ in parsed]
    assert kinds[0] == "step" and kinds.index("sentence") > kinds.index("step")
    searched = [step for step in of(parsed, "step") if step.get("tool") == "search_passages"]
    assert [step["status"] for step in searched] == ["running", "done"]
    sentences = of(parsed, "sentence")
    citing_54 = [sentence for sentence in sentences if ICR_54 in sentence["evidence_ids"]]
    assert any("108 of 328" in sentence["text"] for sentence in citing_54)
    paragraph_54 = next(evidence for evidence in of(parsed, "evidence") if evidence["id"] == ICR_54)
    assert (paragraph_54["kind"], paragraph_54["row"]["pdf_page"], paragraph_54["row"]["paragraph"]) == (
        "passage", 23, "54")
    highlight = paragraph_54["highlights"][0]
    assert paragraph_54["row"]["text"][highlight["start"]:highlight["end"]] == (
        "108 of 328 cases had to go through rebidding")
    checks = of(parsed, "checks")[0]
    assert checks["numbers"]["total"] > 0 and checks["numbers"]["matched"] == checks["numbers"]["total"]
    assert checks["quotes"]["total"] > 0 and checks["quotes"]["found"] == checks["quotes"]["total"]
    assert of(parsed, "removed") == []
    assert kinds[-1] == "done"


def test_each_evidence_event_names_its_stratum_and_its_document_s_short_name(ask_case):
    """The evidence card's eyebrow ("Why · evaluation") and the drawer's source switcher ("ICR ¶54") read
    them from the stream, so the browser never decides which stratum a document belongs to."""
    parsed, _ = ask_case("p130164-rebidding")

    assert [(evidence["id"], evidence["stratum"], evidence["short_name"]) for evidence in of(parsed, "evidence")] == [
        (ICR_54, "Why", "ICR"), ("strata.gold.passage:31525018/v1/55", "Why", "ICR")]


def test_a_number_no_record_holds_is_removed_with_the_copy_files_reason(ask_case):
    parsed, _ = ask_case("p130164-number-with-no-record")

    removed = of(parsed, "removed")
    assert [(item["sentence"], item["reason"]) for item in removed] == [
        ("Bids were usually opened within 45 days.", "number_not_in_records")]
    assert copy_reasons()[removed[0]["reason"]] == {
        "item": "No record supports this number.", "joined": "no record supports that number"}
    assert "45 days" not in " ".join(sentence["text"] for sentence in of(parsed, "sentence"))
    checks = of(parsed, "checks")[0]
    # The base answer states 108 and 328, both on ICR paragraph 54; the planted sentence adds 45.
    assert checks["numbers"] == {"total": 3, "matched": 2}
    assert checks["sentences"] == {"written": 4, "kept": 3, "removed": 1}


def test_a_passage_s_page_and_paragraph_numbers_never_back_a_number(ask_case):
    parsed, _ = ask_case("p130164-page-number-as-a-number")

    # Paragraph 54 is on PDF page 23 (values.toml, icr-para-54); neither number is a count the report gave.
    [removed] = of(parsed, "removed")
    assert [(reason["code"], reason["text"]) for reason in removed["reasons"]] == [
        ("number_not_in_records", "23"), ("number_not_in_records", "54")]


def test_a_sentence_citing_a_source_no_tool_returned_this_turn_is_removed(ask_case):
    parsed, _ = ask_case("p130164-source-not-returned")

    removed = of(parsed, "removed")
    assert [(item["sentence"], item["reason"]) for item in removed] == [
        ("Some works started before the forest department gave its permission.", "id_not_returned")]
    assert removed[0]["reasons"][0]["text"] == "strata.gold.passage:31525018/v1/71"
    assert copy_reasons()["id_not_returned"]["item"] == "It cited a source I did not retrieve for this question."
    assert "strata.gold.passage:31525018/v1/71" not in [evidence["id"] for evidence in of(parsed, "evidence")]
    checks = of(parsed, "checks")[0]
    assert checks["sources"] == {"total": 3, "returned": 2}
    assert checks["sentences"] == {"written": 4, "kept": 3, "removed": 1}


def test_a_quote_that_is_not_word_for_word_on_its_page_is_removed(ask_case):
    parsed, _ = ask_case("p130164-misquote")

    removed = of(parsed, "removed")
    assert [(item["sentence"], item["reason"]) for item in removed] == [
        ('The report puts it plainly: "108 of 328 works contracts had to be bid again".', "quote_not_on_page")]
    assert [reason["code"] for reason in removed[0]["reasons"]] == ["quote_not_on_page"]
    assert copy_reasons()["quote_not_on_page"]["item"] == "The quote is not on the page it cites."
    checks = of(parsed, "checks")[0]
    assert checks["quotes"] == {"total": 3, "found": 2}
    # The misquote's two numbers are not backed by a quote that is on its page.
    assert checks["numbers"] == {"total": 4, "matched": 2}


def test_a_quote_whose_passage_did_not_come_back_is_never_counted_as_on_its_page(ask_case):
    """As of October 15, 2019 the ICR of October 10, 2019 was not yet public (from November 2, 2019), so
    no tool returned paragraphs 54 or 55. Neither quote was compared with any page, so the check line
    may not say they are on their pages."""
    parsed, _ = ask_case("p130164-rebidding", asof=dt.date(2019, 10, 15))

    checks = of(parsed, "checks")[0]
    assert checks["sources"] == {"total": 2, "returned": 0}
    assert checks["quotes"] == {"total": 2, "found": 0}
    assert checks["sentences"] == {"written": 3, "kept": 0, "removed": 3}


def test_the_words_a_sentence_puts_in_quote_marks_are_the_words_checked_on_the_page(ask_case):
    """Check 3 reads the quote the person reads: the words in the sentence's quote marks must be in its
    quote, and its quote on the page. A number gets its support from the quote only from inside them."""
    parsed, _ = ask_case("p130164-quote-marks-and-quote-disagree")

    assert [(item["sentence"], [(reason["code"], reason["text"]) for reason in item["reasons"]])
            for item in of(parsed, "removed")] == [
        ('The report said "the estimates were sound and no contract was bid again".',
         [("quote_not_on_page", ICR_54)]),
        ("In 108 districts the works ran late.",
         [("quote_not_in_sentence", ICR_54), ("number_not_in_records", "108")]),
        ('The ICR called the delay "avoidable".', [("quote_not_on_page", None)]),
        ("The ICR called the delay 'avoidable'.", [("quote_not_on_page", None)]),
        ("The ICR called the works \u2018late and costly\u2019.", [("quote_not_on_page", None)]),
        ("Le rapport dit que les contrats sont \u00ab jamais revus \u00bb.", [("quote_not_on_page", None)]),
    ]
    assert copy_reasons()["quote_not_in_sentence"] == {
        "item": "It cited a quote but did not show the quoted words.",
        "joined": "it cited a quote but did not show the quoted words"}
    checks = of(parsed, "checks")[0]
    # The base answer quotes twice, both on their pages; each planted sentence quotes, and none is found.
    assert checks["quotes"] == {"total": 8, "found": 2}
    assert checks["sentences"] == {"written": 9, "kept": 3, "removed": 6}


def test_a_quote_cut_from_inside_a_number_is_not_on_its_page(ask_case):
    """Paragraph 54 says "108 of 328" (values.toml, icr-para-54). A quoted "10" starts where 108 starts but
    ends inside it, so it is not word for word and backs no number, whatever the claim's quote holds."""
    parsed, _ = ask_case("p130164-quote-cut-from-a-number")

    assert [(item["sentence"], [(reason["code"], reason["text"]) for reason in item["reasons"]])
            for item in of(parsed, "removed")] == [
        ('The ICR said "10" works contracts were bid again.', [("quote_not_on_page", ICR_54)]),
        ('The ICR said "10" works contracts were bid again.', [("quote_not_on_page", ICR_54)]),
    ]
    checks = of(parsed, "checks")[0]
    assert checks["numbers"] == {"total": 4, "matched": 2}


ICR_REVIEW_COST = "strata.gold.passage:34056616/v2/2.e"
ICR_REVIEW_ROADS = "strata.gold.passage:34056616/v2/4/1"


def test_a_quote_cut_from_inside_a_number_with_a_decimal_point_or_a_comma_is_not_on_its_page(fixture_db):
    """The May 4, 2023 ICR Review says "The actual project cost was US$177.6 million" (item 2.e) and "The
    project constructed 2,334 km of roads" (item 4), as values.toml's icr-review-2023-item-2e-cost and
    icr-review-2023-item-4-roads record. A quote that stops at the decimal point of 177.6, or starts after
    the comma in 2,334, is not word for word, so it backs no number."""
    agent = CallsThenAnswers(
        [("search_passages", {"query": "actual project cost US$ million", "project_id": "P130164",
                              "as_of": "2026-10-23"}),
         ("search_passages", {"query": "project constructed km of roads", "project_id": "P130164",
                              "as_of": "2026-10-23"})],
        lambda outputs: [
            claim('The ICR Review said "The actual project cost was US$177".', kind="quote",
                  evidence_ids=[ICR_REVIEW_COST], numbers=["177"],
                  quote={"text": "The actual project cost was US$177", "passage_id": ICR_REVIEW_COST}),
            claim('The ICR Review said the project built "334 km of roads".', kind="quote",
                  evidence_ids=[ICR_REVIEW_ROADS], numbers=["334"],
                  quote={"text": "334 km of roads", "passage_id": ICR_REVIEW_ROADS})])

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert [(item["sentence"], [(reason["code"], reason["text"]) for reason in item["reasons"]])
            for item in of(parsed, "removed")] == [
        ('The ICR Review said "The actual project cost was US$177".', [("quote_not_on_page", ICR_REVIEW_COST)]),
        ('The ICR Review said the project built "334 km of roads".', [("quote_not_on_page", ICR_REVIEW_ROADS)]),
    ]
    checks = of(parsed, "checks")[0]
    # Both passages came back from the searches, so each sentence is removed for its quote alone.
    assert checks["sources"] == {"total": 2, "returned": 2}
    assert checks["numbers"] == {"total": 2, "matched": 0}


def in_lakhs(call, **arguments):
    """search_passages, with the ICR Review's "2,334 km" written in lakhs, as "12,50,000 km"."""
    result = search_passages(call, **arguments)
    for row in result["rows"]:
        row["text"] = row["text"].replace("2,334 km", "12,50,000 km")
    return result


def test_a_quote_cut_from_inside_a_number_grouped_in_lakhs_is_not_on_its_page(fixture_db):
    """Ticket 13's review round 5, P2: "12,50,000" is one number, so "50,000 km of roads" starts inside it and is not
    word for word, as "334 km of roads" is not in "2,334 km" (the test above)."""
    agent = CallsThenAnswers(
        [("search_passages", {"query": "project constructed km of roads", "project_id": "P130164",
                              "as_of": "2026-10-23"})],
        lambda outputs: [claim('The ICR Review said the project built "50,000 km of roads".', kind="quote",
                               evidence_ids=[ICR_REVIEW_ROADS], numbers=["50,000"],
                               quote={"text": "50,000 km of roads", "passage_id": ICR_REVIEW_ROADS})])

    parsed = ask_with_tools(fixture_db, agent, with_adapter("search_passages", "in_lakhs"))

    assert [[(reason["code"], reason["text"]) for reason in item["reasons"]] for item in of(parsed, "removed")] == [
        [("quote_not_on_page", ICR_REVIEW_ROADS)]]


def test_a_fourth_round_of_tool_calls_gets_no_results_and_the_answer_rests_on_the_first_three(ask_case):
    parsed, agent = ask_case("p130164-fourth-round")

    ran = [step for step in of(parsed, "step") if step["kind"] == "tool" and step["status"] == "done"]
    assert len(ran) == 3
    fourth = [json.loads(item["output"]) for item in agent.received[4]["input"]]
    assert fourth == [{"not_run": "round_limit", "tool_rounds": 3}]
    removed = of(parsed, "removed")
    assert [(item["reason"], item["reasons"][0]["text"]) for item in removed] == [
        ("id_not_returned", "strata.gold.passage:31525018/v1/88")]
    assert len(of(parsed, "sentence")) == 3


def test_the_agent_gets_no_date_after_its_as_of_date_from_a_tool_that_abstained(ask_case):
    parsed, agent = ask_case("p156634-plan-not-yet-public")

    asked = json.loads(agent.received[0]["input"][0]["content"])
    assert (asked["question"], asked["scope"], asked["as_of"]) == (
        "Check the Northern Water Works Development Agency's Procurement Plan of October 9, 2026 for P156634.",
        "P156634", "2026-10-01")
    result = agent.received[1]["input"][0]["output"]
    assert json.loads(result)["abstention"]["reason"] == "version_not_public"
    # The plan is dated, and became public, on October 9, 2026 (values.toml, plan_date of the demo plan).
    assert "2026-10-09" not in result
    assert [sentence["index"] for sentence in of(parsed, "sentence")] == [0]


def test_an_as_of_date_after_today_asks_as_of_today(ask_case):
    _, agent = ask_case("p130164-rebidding", asof=dt.date(2027, 3, 1), today=dt.date(2026, 10, 23))

    assert json.loads(agent.received[0]["input"][0]["content"])["as_of"] == "2026-10-23"
    assert json.loads(agent.received[1]["input"][0]["output"])["as_of"] == "2026-10-23"


TRACES = TraceIds(application_insights="4bf92f3577b34da6a3ce929d0e0e4736", mlflow="tr-0af7651916cd43dd8448eb211c80319c")


@pytest.fixture
def ops_db(tmp_path):
    """A writable database with the strata catalog's tables, for the run log."""
    path = tmp_path / "ops.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


def test_the_final_event_names_the_run_and_both_of_its_traces(ask_case):
    parsed, _ = ask_case("p130164-rebidding", trace_ids=lambda: TRACES)

    assert parsed[-1] == ("done", {"run_id": "run-0001", "trace_ids": {
        "application_insights": "4bf92f3577b34da6a3ce929d0e0e4736", "mlflow": "tr-0af7651916cd43dd8448eb211c80319c"}})


def test_the_run_s_application_insights_trace_is_the_request_s_own_trace(ask_case, ops_db):
    """Ticket 06 sends one trace per request to Application Insights; the done event and the run's row
    name that trace, so a run opens in Application Insights from either."""
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    parsed, _ = ask_case("p130164-rebidding", tracer_provider=provider, runs=RunLog(lambda: DuckDBEngine.open(ops_db)))

    [span] = [span for span in exporter.get_finished_spans() if span.name == "POST /api/ask"]
    trace_id = format(span.context.trace_id, "032x")
    assert parsed[-1][1]["trace_ids"]["application_insights"] == trace_id
    with DuckDBEngine.open(ops_db, read_only=True) as engine:
        assert list(engine.run("SELECT application_insights_trace_id FROM strata.ops.agent_runs").rows) == [(trace_id,)]



def test_the_run_is_logged_even_when_listing_the_sources_it_cited_fails(ask_case, ops_db, caplog):
    """Ticket 13 logs every run. The sources an answer cited (ticket 32) are written beside the run row, so a fault
    while listing them is logged and leaves the run row to be written."""
    from strata.knowledge.retrieval.reports import CitationLog, PassageReports
    from strata.config import load_roles

    class Faulty(PassageReports):
        def citation_rows(self, *args, **kwargs):
            raise TypeError("a fact's source is not a mapping")

    written = []
    ask_case("p130164-rebidding", runs=RunLog(lambda: DuckDBEngine.open(ops_db)), passage_reports=Faulty(load_roles()),
             citations=CitationLog(lambda: written.append("opened")))

    with DuckDBEngine.open(ops_db, read_only=True) as engine:
        assert list(engine.run("SELECT run_id FROM strata.ops.agent_runs").rows) == [("run-0001",)]
    assert written == []
    assert "Run run-0001 could not list its cited sources." in caplog.text

def test_every_run_is_logged_in_strata_ops_with_its_checks_and_trace(ask_case, ops_db):
    ask_case("p130164-number-with-no-record", trace_ids=lambda: TRACES,
             runs=RunLog(lambda: DuckDBEngine.open(ops_db)))

    with DuckDBEngine.open(ops_db, read_only=True) as engine:
        result = engine.run("SELECT * FROM strata.ops.agent_runs")
    runs = [dict(zip(result.columns, row)) for row in result.rows]
    assert len(runs) == 1
    run = runs[0]
    assert (run["run_id"], run["status"], run["viewer_id"], run["scope"], run["as_of"].isoformat()) == (
        "run-0001", "answered", "4021@1984", "P130164", "2026-10-23")
    assert (run["agent"], run["tool_rounds"], run["sentences_written"], run["sentences_removed"]) == (
        "strata-orchestrator", 1, 4, 1)
    assert (run["numbers_total"], run["numbers_matched"], run["quotes_total"], run["quotes_found"]) == (3, 2, 2, 2)
    assert json.loads(run["removed"]) == [
        {"sentence": "Bids were usually opened within 45 days.", "reason": "number_not_in_records"}]
    # The planted sentence fails check 1, so the loop asked the agent to rewrite once (ticket 109), and the scripted
    # agent, whose recording holds no rewrite, sent its answer again.
    assert json.loads(run["response_ids"]) == ["resp_p130164_rebidding_1", "resp_p130164_rebidding_2",
                                               "resp_p130164_rebidding_2_again_3"]
    assert run["application_insights_trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert "ana.example" not in json.dumps(run, default=str)


def test_a_runner_cannot_send_a_sentence_the_verifier_did_not_check():
    async def runner(turn):
        yield Event("sentence", {"text": "Bids were usually opened within 45 days.", "evidence_ids": []})

    parsed = events(ask_with(create_app(runner=runner, new_run_id=lambda: "run-0002")))

    assert parsed == [("error", {"code": "internal"}), ("done", {"run_id": "run-0002"})]


def test_an_answer_that_is_not_claims_as_json_ends_with_its_own_error():
    class Rambles:
        name, version = "strata-orchestrator", None

        def respond(self, items, previous_response_id):
            return {"id": "resp_1", "output": [{"type": "message", "role": "assistant", "content": [
                {"type": "output_text", "text": "Bids were usually opened within 45 days."}]}]}

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Rambles(), no_engine),
                                        new_run_id=lambda: "run-0003")))

    assert of(parsed, "sentence") == []
    assert parsed[-2:] == [("error", {"code": "agent_output"}), ("done", {"run_id": "run-0003"})]


class Answers:
    """An agent that answers at once with the claims it is given, calling no tool."""

    name, version = "strata-orchestrator", None

    def __init__(self, *claims):
        self.claims = list(claims)

    def respond(self, items, previous_response_id):
        return {"id": "resp_1", "output": [{"type": "message", "role": "assistant", "content": [
            {"type": "output_text", "text": json.dumps({"claims": self.claims})}]}]}


def check_1(parsed):
    """How check 1 read each sentence the agent wrote, in order: the reasons it gave for the sentences it failed, and
    the sentences it let through. These tests write summaries that cite nothing, and no tool abstained, so check 2
    removes every one of them too (no_source, ticket 24's verify F1): only check 1's reasons say how the numbers in a
    sentence were read."""
    written = sorted([(item["index"], item["text"], []) for item in of(parsed, "sentence")] + [
        (item["index"], item["sentence"], [(reason["code"], reason["text"]) for reason in item["reasons"]
                                           if reason["check"] == 1]) for item in of(parsed, "removed")])
    return [reasons for _, _, reasons in written if reasons], [text for _, text, reasons in written if not reasons]


def test_numbers_and_dates_the_agent_lists_but_does_not_write_are_checked_too():
    unwritten = {"sentence": "Bids took a while to open.", "kind": "summary", "evidence_ids": [],
                 "numbers": [], "dates": ["45", "March 3, 2015"], "quote": None}

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(unwritten), no_engine))))

    assert [[code for code, _ in reasons] for reasons in check_1(parsed)[0]] == [
        ["number_not_in_records", "date_not_in_records"]]


def test_a_fiscal_year_is_a_number_a_record_must_hold():
    fiscal = {"sentence": "Most of the works were signed in FY2019.", "kind": "summary", "evidence_ids": [],
              "numbers": [], "dates": [], "quote": None}

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(fiscal), no_engine))))

    assert check_1(parsed)[0] == [[("number_not_in_records", "FY2019")]]


def test_a_number_written_as_a_word_is_a_number_a_record_must_hold():
    """DESIGN.md section 7 writes one to nine in words, so "six" is checked like 6, and "zero" like 0. "One"
    is a number too ("one bid", "only one of the firms"), except where it stands for a thing named before
    ("no one", "each one", "one of the firms" with no count after it). "Half" after "first" or "second" is a
    time when nothing follows it or a time does ("the first half of the year"), and an amount when things
    do ("the first half of the packages")."""
    def claim(sentence):
        return {"sentence": sentence, "kind": "summary", "evidence_ids": [], "numbers": [], "dates": [], "quote": None}

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(
        claim("Six works contracts were bid again."), claim("It was one of 37 packages."),
        claim("One lesson was about estimates."), claim("Only one bid was received for the package."),
        claim("One firm bid for it."), claim("Zero bids came in."), claim("No one said why."),
        claim("Each one was signed late."), claim("The works started in the first half of the year."),
        claim("The contractors' bids came late, and the World Bank's review followed."),
        claim("Only one of the firms bid."), claim("The first half of the packages were late."),
        claim("Just one of its packages was signed."), claim("The second half of FY2019 was slow."),
        claim("The works slowed in the second half.")),
        no_engine))))

    failed, passed = check_1(parsed)
    assert failed == [
        [("number_not_in_records", "Six")], [("number_not_in_records", "one"), ("number_not_in_records", "37")],
        [("number_not_in_records", "One")], [("number_not_in_records", "one")], [("number_not_in_records", "One")],
        [("number_not_in_records", "Zero")], [("number_not_in_records", "one")], [("number_not_in_records", "half")],
        [("number_not_in_records", "one")], [("number_not_in_records", "FY2019")]]
    assert passed == [
        "No one said why.", "Each one was signed late.", "The works started in the first half of the year.",
        "The contractors' bids came late, and the World Bank's review followed.",
        "The works slowed in the second half."]
    # Apostrophes are not quote marks, so that sentence quotes nothing.
    assert of(parsed, "checks")[0]["quotes"] == {"total": 0, "found": 0}


def claim(sentence, **fields):
    return {"sentence": sentence, "kind": "summary", "evidence_ids": [], "numbers": [], "dates": [], "quote": None,
            **fields}


def test_the_middle_half_and_the_middle_one_name_parts_of_a_past_range_not_amounts():
    """Strata's own words for a past range (web/src/copy.ts, pastRange): "the middle half" is the band
    between the quarter and three-quarter points, and "the middle one" is the package at the middle, so
    neither is an amount a row must hold. "Half of the packages" and "one bid" still are."""
    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(
        claim("The middle half of these packages took a while."), claim("The middle one took longer."),
        claim("Half of the packages were late."), claim("Only one bid came in for the middle half.")),
        no_engine))))

    assert check_1(parsed) == ([[("number_not_in_records", "Half")], [("number_not_in_records", "one")]], [
        "The middle half of these packages took a while.", "The middle one took longer."])


def removed_reasons(parsed):
    return [[(reason["code"], reason["text"]) for reason in item["reasons"]] for item in of(parsed, "removed")]


def test_a_number_joined_to_a_unit_or_a_range_or_written_as_a_word_above_nine_is_a_number_a_record_must_hold():
    """Every digit run is a number unless its whole token is an id: a project, a loan (four digits or
    more, as STEP writes it, "IDA / 60300"), a STEP reference (three parts or more, joined by hyphens or
    slashes, "KE/TAVEVO/82755/GO/RFQ"), a passage or a section label, so Q3-2020 and "IBRD 45 contracts"
    are read. "45-day", "US$1.2M", "300k" and "3x" are read as their digits, "10-15" and
    "2019/20" as two numbers each, and number words go past nine. "Half" and "a dozen" are numbers too. A token that
    starts with FY, a quarter or a half is a period, so Q3/2020/21 and FY-2019-20 are read, not taken for ids;
    "12,50,000", grouped in lakhs as Indian reports write it, is one number; and "doubled", "tripled" and "halved"
    are amounts no row holds as written, as "double" is."""
    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(
        claim("Bids were opened within a 45-day period."),
        claim("The contracts totaled US$1.2M."),
        claim("Bids were opened in 10-15 days."),
        claim("About 300k people were reached, 3x the target."),
        claim("Most works were signed in 2019/20."),
        claim("Twelve packages were signed."),
        claim("Forty-five contracts were bid again."),
        claim("A dozen bids came in, and half were rejected."),
        claim("Bids took a while to open.", numbers=["45-day"]),
        claim("Most works were signed in Q3-2020."),
        claim("The IBRD 45 contracts were signed."),
        claim("The COVID-19 pause held up P130164, IDA-60290 and KE-NWWDA-541062-CW-RFQ under III.B and 10.b."),
        claim("IDA 51030KE paid for NWWDA-WSDP-03-2019-2020 and MWI-WSDP-001."),
        claim("It was financed by IDA / 60300."),
        claim("The bid KE/TAVEVO/82755/GO/RFQ was signed, and so was KALRO/HQTS/053/23-24."),
        claim("IDA \u2013 6030 KE paid for CF/RRSMP/11-15."),
        claim("The IDA 2019 funds came late."),
        claim("Most works were signed in Q3/2020/21."),
        claim("It slipped to FY-2019-20."),
        claim("The roads cost 12,50,000."),
        claim("Costs doubled, and the bids were halved."),
        claim("Its estimate tripled."),
    ), no_engine))))

    failed, passed = check_1(parsed)
    assert failed == [
        [("number_not_in_records", "45")],
        [("number_not_in_records", "1.2")],
        [("number_not_in_records", "10"), ("number_not_in_records", "15")],
        [("number_not_in_records", "300"), ("number_not_in_records", "3")],
        [("date_not_in_records", "2019"), ("number_not_in_records", "20")],
        [("number_not_in_records", "Twelve")],
        [("number_not_in_records", "Forty-five")],
        [("number_not_in_records", "A dozen"), ("number_not_in_records", "half")],
        [("number_not_in_records", "45")],
        [("number_not_in_records", "3"), ("date_not_in_records", "2020")],
        [("number_not_in_records", "45")],
        [("date_not_in_records", "2019")],
        # A period written in three parts is a period, not an id (ticket 13's review round 5, P1).
        [("number_not_in_records", "3"), ("date_not_in_records", "2020"), ("number_not_in_records", "21")],
        [("date_not_in_records", "2019"), ("number_not_in_records", "20")],
        # Digits grouped in lakhs are one number (P2), and "doubled" is an amount as "double" is (verify round 5, F2).
        [("number_not_in_records", "12,50,000")],
        [("number_not_in_records", "doubled"), ("number_not_in_records", "halved")],
        [("number_not_in_records", "tripled")],
    ]
    assert passed == [
        "The COVID-19 pause held up P130164, IDA-60290 and KE-NWWDA-541062-CW-RFQ under III.B and 10.b.",
        "IDA 51030KE paid for NWWDA-WSDP-03-2019-2020 and MWI-WSDP-001.",
        "It was financed by IDA / 60300.",
        "The bid KE/TAVEVO/82755/GO/RFQ was signed, and so was KALRO/HQTS/053/23-24.",
        "IDA \u2013 6030 KE paid for CF/RRSMP/11-15."]
    assert of(parsed, "checks")[0]["numbers"]["matched"] == 0


class CallsThenAnswers:
    """An agent that makes one round of tool calls, then answers with the claims answer() writes from
    the tool results it got back, as a list of each call's output. When the app asks it to rewrite (ticket 109), it
    answers with the claims rewrite() writes from the same outputs and the message's list, or with the same claims
    again. It keeps every message the app sent it."""

    name, version = "strata-orchestrator", None

    def __init__(self, calls, answer, rewrite=None):
        self.calls, self.answer, self.rewrite, self.round = calls, answer, rewrite, 0
        self.outputs, self.received = None, []

    def respond(self, items, previous_response_id):
        self.round += 1
        self.received.append(items)
        if self.round == 1:
            return {"id": "resp_1", "output": [
                {"type": "function_call", "call_id": f"call_{number}", "name": name, "arguments": json.dumps(arguments)}
                for number, (name, arguments) in enumerate(self.calls, 1)]}
        asked = [json.loads(item["content"])["rewrite"] for item in items if item.get("role") == "user"]
        if asked:
            claims = self.rewrite(self.outputs, asked[0]) if self.rewrite else self.answer(self.outputs)
        else:
            self.outputs = [json.loads(item["output"]) for item in items]
            claims = self.answer(self.outputs)
        return Answers(*claims).respond(items, previous_response_id)


def with_adapter(name, adapter):
    """The tool registry with one tool's adapter replaced by a stand-in in this file."""
    tools = load_tools()
    return {**tools, name: dataclasses.replace(tools[name], adapter=f"test_answer_stream:{adapter}")}


def as_table_summaries(call, **arguments):
    """search_passages, with every passage it finds marked as a table's one summary passage."""
    result = search_passages(call, **arguments)
    for row in result["rows"]:
        row["kind"] = TABLE_SUMMARY
    return result


def with_two_envelopes(call, **arguments):
    """check_plan, with KE-NWWDA-541062-CW-RFQ's market approach set to STEP's Single Stage - Two Envelope,
    and its description to one that names a number of items, as "Supply of Two Airside Fire Tenders" does."""
    result = check_plan(call, **arguments)
    for row in result["rows"]:
        if row["activity_reference_no"] == "KE-NWWDA-541062-CW-RFQ":
            row["market_approach"] = "Single Stage - Two Envelope"
            row["description"] = "Supply of Two Airside Fire Tenders"
    return result


def without_abstention(call, **arguments):
    """estimate_time as it answers once a model gives a time estimate: no abstention, so the agent gets its summary.
    The hand-made set trains no model, so the tool abstains with no rows, and the agent then gets no summary."""
    return {**estimate_time(call, **arguments), "abstention": None}


class EverySentenceFollows:
    """A judge for check 4 that finds every sentence follows from its sources, for the tests of checks 1 to 3,
    so check 4 never stands in their way. tests/test_six_checks.py tests check 4 with recorded judges."""

    name = "every sentence follows"

    def judge(self, questions):
        return [Judgement(question.index, True, "It follows.") for question in questions]


def ask_with_tools(fixture_db, agent, tools, judge=None, thresholds=None, **body):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    return events(ask_with(create_app(runner=answer_runner(lambda turn: agent, engine_for, tools=tools,
                                                           thresholds=thresholds, today=lambda: TODAY),
                                      engine_for=engine_for, judge=judge), **body))


def test_a_number_quoted_from_a_table_summary_is_not_backed_by_it(fixture_db):
    """A table's summary passage is the reader's words for a table, not the report's, so even a number
    inside a quote from it must match a record (spec, check 1), and the removed box says the number
    came only from the summary."""
    rebidding = "108 of 328 cases had to go through rebidding"
    agent = CallsThenAnswers(
        [("search_passages", {"query": "works contracts advertised again rebidding", "project_id": "P130164",
                              "as_of": "2026-10-23"})],
        lambda outputs: [claim(f'The report said "{rebidding}".', kind="quote", evidence_ids=[ICR_54],
                               numbers=["108", "328"], quote={"text": rebidding, "passage_id": ICR_54})])

    parsed = ask_with_tools(fixture_db, agent, with_adapter("search_passages", "as_table_summaries"))

    assert removed_reasons(parsed) == [[("number_only_in_table_summary", "108"),
                                        ("number_only_in_table_summary", "328")]]


def test_a_quote_with_straight_quote_marks_matches_a_page_with_curly_ones(fixture_db):
    """The PAD's Annex 3, paragraph 51 writes "the World Bank’s prior review" with a curly apostrophe
    (evals/shield_passages.toml). A model often writes a straight one; the quote is still word for word,
    and its highlight covers the page's own words."""
    annex = "strata.gold.passage:27348420/v1/annex3.51"
    words = "shall be subject to the World Bank's prior review"
    agent = CallsThenAnswers(
        [("search_passages", {"query": "contracts subject to the World Bank's prior review", "project_id": "P156634",
                              "as_of": "2026-10-23"})],
        lambda outputs: [claim(f'The PAD said some contracts "{words}".', kind="quote", evidence_ids=[annex],
                               quote={"text": words, "passage_id": annex})])

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert of(parsed, "removed") == []
    [evidence] = of(parsed, "evidence")
    [highlight] = evidence["highlights"]
    assert evidence["row"]["text"][highlight["start"]:highlight["end"]] == (
        "shall be subject to the World Bank\u2019s prior review")


def test_a_quote_that_starts_a_sentence_with_a_capital_matches_a_page_that_has_a_small_letter_there(fixture_db):
    """The ICR's paragraph 54 reads "...is that the works contract estimates should have been based on the market
    rate..." (tests/ground_truth/values.toml, icr-para-54). A quote that starts the reader's sentence takes a capital,
    as "[T]he" does in print, and the live agent wrote it so on October 27, 2026 (ticket 109): it is still word for
    word, and its highlight covers the page's own words. Any other change of letters is not: "108 OF 328 CASES" is
    removed."""
    words = "The works contract estimates should have been based on the market rate"
    shouted = "108 OF 328 CASES"
    agent = CallsThenAnswers(
        [("search_passages", {"query": "works contracts advertised again rebidding", "project_id": "P130164",
                              "as_of": "2026-10-23"})],
        lambda outputs: [claim(f'The ICR says "{words}".', kind="quote", evidence_ids=[ICR_54],
                               quote={"text": words, "passage_id": ICR_54}),
                         claim(f'The ICR says "{shouted}" had to go through rebidding.', kind="quote",
                               evidence_ids=[ICR_54], numbers=["108", "328"],
                               quote={"text": shouted, "passage_id": ICR_54})])

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [f'The ICR says "{words}".']
    assert removed_reasons(parsed) == [[("quote_not_on_page", ICR_54)]]
    [evidence] = of(parsed, "evidence")
    [highlight] = evidence["highlights"]
    assert (evidence["id"], evidence["row"]["paragraph"]) == (ICR_54, "54")
    assert evidence["row"]["text"][highlight["start"]:highlight["end"]] == (
        "the works contract estimates should have been based on the market rate")


# Ticket 109: what the live agent wrote on October 27, 2026, in its own words, and what the passage says word for word.
MARKET_RATE = "the works contract estimates should have been based on the market rate"
PARAPHRASED = "The ICR said the works contract estimates should have been based on the market rate."
QUOTED = f'The ICR said "{MARKET_RATE}".'


def rewrite_case(rewrite=None):
    """The agent searches P130164's passages, then writes ICR paragraph 54's words in its own sentence with no quote
    marks, which check 3 removes (quote_not_in_sentence). Asked to rewrite, it answers with what rewrite() writes."""
    return CallsThenAnswers(
        [("search_passages", {"query": "works contracts advertised again rebidding", "project_id": "P130164",
                              "as_of": "2026-10-23"})],
        lambda outputs: [claim(PARAPHRASED, kind="quote", evidence_ids=[ICR_54],
                               quote={"text": MARKET_RATE, "passage_id": ICR_54})],
        rewrite)


def test_a_sentence_checks_1_to_3_would_remove_goes_back_to_the_agent_once_and_the_rewrite_is_checked_in_full(
        fixture_db):
    """One rewrite round (ticket 109): the loop runs checks 1 to 3 on the first answer, sends the agent one data-only
    message that lists each sentence they would remove with its reasons, and takes the next answer as final. The
    stream's verifier then checks that answer in full, so a sentence it still fails is removed, and the first answer
    never reaches the screen."""
    agent = rewrite_case(lambda outputs, rewrite: [
        claim(QUOTED, kind="quote", evidence_ids=[ICR_54], quote={"text": MARKET_RATE, "passage_id": ICR_54}),
        claim("The ICR counted 99 cases of rebidding.", kind="record", evidence_ids=[ICR_54], numbers=["99"])])

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    [_, _, rewrite] = agent.received
    assert [json.loads(item["content"]) for item in rewrite] == [{"rewrite": [
        {"sentence": PARAPHRASED, "reasons": [{"code": "quote_not_in_sentence", "text": ICR_54}]}]}]
    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [QUOTED]
    assert removed_reasons(parsed) == [[("number_not_in_records", "99")]]
    assert of(parsed, "checks")[0]["sentences"] == {"written": 2, "kept": 1, "removed": 1}
    assert PARAPHRASED not in json.dumps(parsed)


def test_with_rewrite_rounds_0_the_agent_is_asked_once_and_its_first_answer_is_checked_as_it_was(fixture_db):
    """config/thresholds.toml's agent.rewrite_rounds is 1; 0 turns the round off."""
    limits = load_thresholds()
    off = dataclasses.replace(limits, values={**limits.values, "agent": {**limits.values["agent"], "rewrite_rounds": 0}})
    agent = rewrite_case(lambda outputs, rewrite: [claim(QUOTED, kind="quote", evidence_ids=[ICR_54],
                                                         quote={"text": MARKET_RATE, "passage_id": ICR_54})])

    parsed = ask_with_tools(fixture_db, agent, load_tools(), thresholds=off)

    assert limits.value("agent.rewrite_rounds") == 1
    assert len(agent.received) == 2
    assert of(parsed, "sentence") == []
    assert removed_reasons(parsed) == [[("quote_not_in_sentence", ICR_54)]]


def test_a_rewrite_that_is_not_an_answer_leaves_the_first_answer_which_the_verifier_checks_in_full(fixture_db):
    """An agent that answers the rewrite message with tool calls, or with text that is not claims as JSON, has not
    rewritten anything: the first answer stands, checked as it would have been without the round."""
    class AsksAgain(CallsThenAnswers):
        def respond(self, items, previous_response_id):
            if any(item.get("role") == "user" for item in items) and self.round:
                self.round += 1
                self.received.append(items)
                return {"id": "resp_3", "output": [{"type": "function_call", "call_id": "call_9", "name": "search_passages",
                                                    "arguments": "{}"}]}
            return super().respond(items, previous_response_id)

    agent = AsksAgain(rewrite_case().calls, rewrite_case().answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert len(agent.received) == 3
    assert of(parsed, "sentence") == []
    assert removed_reasons(parsed) == [[("quote_not_in_sentence", ICR_54)]]
    assert [kind for kind, _ in parsed][-1] == "done" and of(parsed, "error") == []


def test_a_number_word_inside_a_step_value_of_a_cited_row_is_part_of_its_name(fixture_db):
    """"Two" in STEP's market approach "Single Stage - Two Envelope" is a name, not a count, whether or not
    the sentence quotes it. A number word in lower case is a count even when a value holds it beside the
    same word ("of Two"). Words quoted from a record's text value must still be in it word for word."""
    def answer(outputs):
        [cited] = [row["evidence_id"] for row in outputs[0]["rows"]
                   if row["activity_reference_no"] == "KE-NWWDA-541062-CW-RFQ"]
        return [claim(sentence, kind="record", evidence_ids=[cited]) for sentence in (
            'Its market approach was "Single Stage - Two Envelope".',
            "It went to market as Single Stage - Two Envelope.",
            "Thirty-seven firms bid for it.",
            "Only a total of two firms bid.",
            'The plan called it "Equipping of boreholes, Lot 9".',
            'Its STEP reference held "1".')]

    agent = CallsThenAnswers([("check_plan", {
        "project_id": "P156634", "implementing_agency": "Northern Water Works Development Agency",
        "plan_date": "2026-10-09", "as_of": "2026-10-23"})], answer)

    parsed = ask_with_tools(fixture_db, agent, with_adapter("check_plan", "with_two_envelopes"), EverySentenceFollows())

    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        'Its market approach was "Single Stage - Two Envelope".', "It went to market as Single Stage - Two Envelope."]
    # KE-NWWDA-541062-CW-RFQ holds a 1 only inside 541062, so a quoted "1" is not on the record.
    assert removed_reasons(parsed) == [
        [("number_not_in_records", "Thirty-seven")], [("number_not_in_records", "two")], [("quote_not_on_page", None)],
        [("quote_not_on_page", None)]]


def test_a_past_range_the_agent_states_in_strata_s_words_is_backed_by_find_comparables_summary_record(fixture_db):
    """The past range, the plan's count, the numbers its frequency phrases state and the comparables' count
    are derived figures, so find_comparables returns them as one citable record beside its rows (CLAUDE.md
    rule 1). The agent can then say what the screen says (web/src/copy.ts, pastRange's title and summary)
    citing only that record, and a number the record does not hold is still removed. The values are
    tests/ground_truth/values.toml's past_range."""
    import tomllib

    truth = tomllib.loads((Path(__file__).parent / "ground_truth" / "values.toml").read_text())["past_range"]
    within = len(truth["signed_within_plan"])

    def answer(outputs):
        summary = outputs[0]["summary"]["evidence_id"]
        sentences = [
            f"The middle half of these packages took {truth['q25_months']} to {truth['q75_months']} months, and the "
            f"middle one took {truth['q50_months']}.",
            f"8 in 10 were signed within {truth['q80_months']} months.",
            f"{within} of {truth['comparables']} comparable packages, fewer than 1 in 10, were signed within the "
            f"plan's {truth['plan_months']} months.",
            f"The middle half of these packages took 3.4 to {truth['q75_months']} months, and the middle one took "
            f"{truth['q50_months']}.",
        ]
        return [claim(sentence, kind="record", evidence_ids=[summary]) for sentence in sentences]

    agent = CallsThenAnswers([("find_comparables", {"step_reference": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"})],
                             answer)

    # The page's as-of date is the one every tool call runs at (ticket 40): the past range's values are as of October 22.
    parsed = ask_with_tools(fixture_db, agent, load_tools(), asof="2026-10-22")

    assert [sentence["text"].split(" ")[:3] for sentence in of(parsed, "sentence")] == [
        ["The", "middle", "half"], ["8", "in", "10"], [str(within), "of", str(truth["comparables"])]]
    assert removed_reasons(parsed) == [[("number_not_in_records", "3.4")]]
    [evidence] = of(parsed, "evidence")
    assert evidence["id"] == "strata.tools.find_comparables:KE-NWWDA-541055-CW-RFB@2026-10-22"
    assert (evidence["tool"], evidence["row"]["public_from"]) == ("find_comparables", "2026-10-22")


def test_a_number_that_equals_a_value_of_another_unit_or_rounding_is_not_backed_by_it(fixture_db):
    """Ticket 12's verify V1: a number matched any value in a cited record, so "45 months" passed on the plan's
    45 days, "34 months" on a comparable's 34 days, and "8.0" on the 8 of "8 in 10". A number written with a
    unit no longer matches a value whose field names another unit, and a number written with decimals no
    longer matches a whole number. tests/ground_truth/values.toml's past_range gives the plan's 45 days and 1.5
    months and the middle half's 3.3 to 7.9 months; KE-WAJWASCO-372776-CW-RFB took 34 days, 1.1 months."""
    def answer(outputs):
        summary = outputs[0]["summary"]["evidence_id"]
        wajwasco = "strata.gold.package:KE-WAJWASCO-372776-CW-RFB"
        return [claim(sentence, kind="record", evidence_ids=[cited]) for sentence, cited in (
            ("The plan allows 45 months.", summary), ("KE-WAJWASCO-372776-CW-RFB took 34 months.", wajwasco),
            ("The middle half took 3.3 to 8.0 months.", summary), ("The plan allows 45 days, or 1.5 months.", summary),
            ("KE-WAJWASCO-372776-CW-RFB took 34 days.", wajwasco), ("The middle half took 3.3 to 7.9 months.", summary))]

    agent = CallsThenAnswers([("find_comparables", {"step_reference": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"})],
                             answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert removed_reasons(parsed) == [[("number_not_in_records", "45")], [("number_not_in_records", "34")],
                                       [("number_not_in_records", "8.0")]]
    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        "The plan allows 45 days, or 1.5 months.", "KE-WAJWASCO-372776-CW-RFB took 34 days.",
        "The middle half took 3.3 to 7.9 months."]


def test_a_natural_frequency_is_one_value_that_only_a_frequency_pair_backs(fixture_db):
    """Ticket 12's review P3 and verify V1: find_comparables' summary holds the pairs [8, 10] and [1, 10] that "8 in
    10 were signed within" and "fewer than 1 in 10" state, and they used to back any 8, 10 or 1 a sentence wrote.
    "N in 10", with "about", "fewer than" or "more than" before it, is now one value, which only a pair with the same
    words backs, and the pairs back nothing else. A count field backs no number written with a time unit. The truth
    is tests/ground_truth/values.toml's past_range: 2 of 49 were signed within the plan's 1.5 months, fewer than 1 in
    10, and 8 in 10 within 9.1 months."""
    truth = TRUTH["past_range"]
    within, total = len(truth["signed_within_plan"]), truth["comparables"]

    def answer(outputs):
        summary = outputs[0]["summary"]["evidence_id"]
        return [claim(sentence, kind="record", evidence_ids=[summary]) for sentence in (
            f"8 in 10 were signed within {truth['q80_months']} months.",
            f"{within} of {total} comparable packages, fewer than 1 in 10, were signed within the plan's "
            f"{truth['plan_months']} months.",
            f"8 of {total} comparable packages were signed within the plan's {truth['plan_months']} months.",
            f"About 1 in 10 were signed within the plan's {truth['plan_months']} months.",
            f"More than 9 in 10 were signed within {truth['q80_months']} months.",
            f"The plan allows {total} months.")]

    agent = CallsThenAnswers([("find_comparables", {"step_reference": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"})],
                             answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools(), asof="2026-10-22")

    assert [sentence["text"].split(" ")[:3] for sentence in of(parsed, "sentence")] == [
        ["8", "in", "10"], [str(within), "of", str(total)]]
    assert removed_reasons(parsed) == [[("number_not_in_records", "8")], [("number_not_in_records", "About 1 in 10")],
                                       [("number_not_in_records", "More than 9 in 10")],
                                       [("number_not_in_records", str(total))]]


def test_a_model_s_frequency_needs_a_value_named_in10_and_none_is_held_when_the_model_is_not_shown(fixture_db):
    """Ticket 28's verify F2: with rebidding_risk's model not shown (model.shown false, in10 null), the copy file's
    sentence for a shown model (rebid.model) was kept, because 3 matched n and 10 a coverage count. "About 3 in 10"
    is one value, which only a field named in10 can back."""
    def answer(outputs):
        assert outputs[0]["summary"]["model"]["shown"] is False
        return [claim("My model estimates that about 3 in 10 packages like this one are advertised again.",
                      kind="summary", evidence_ids=[outputs[0]["summary"]["evidence_id"]])]

    agent = CallsThenAnswers([("rebidding_risk", {"step_reference": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"})],
                             answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools(), EverySentenceFollows(), asof="2026-10-22")

    assert removed_reasons(parsed) == [[("number_not_in_records", "about 3 in 10")]]


def test_a_reason_quoted_word_for_word_from_rebidding_risk_s_record_passes_checks_1_to_3(fixture_db):
    """Ticket 28's verify F1: rebidding_risk's row keeps a notice's reason as quote.text, and the verifier skipped
    every field named text, so a true quote of it was removed. A record's own text is quotable at any depth; only a
    passage's text is its page. The judge is not connected, so a sentence stands only when checks 1 to 3 prove it. The
    reason is KE-KIMAWASCO-149448-CW-RFB's cancellation notice OP00083890 (data/fixture/recorded/api)."""
    notice = "strata.silver.notices:OP00083890"
    said = "The Request for Bids has been cancelled."

    def answer(outputs):
        [row] = [row for row in outputs[0]["rows"] if row["evidence_id"] == notice]
        assert row["quote"]["text"] == said
        return [claim(f'KE-KIMAWASCO-149448-CW-RFB\'s notice said "{said}"', kind="quote", evidence_ids=[notice]),
                claim(f'Its notice said "{said}"', kind="quote", evidence_ids=[notice],
                      quote={"text": said, "passage_id": notice}),
                claim('Its notice said "The Request for Bids has been delayed."', kind="quote", evidence_ids=[notice])]

    agent = CallsThenAnswers([("rebidding_risk", {"step_reference": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"})],
                             answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools(), asof="2026-10-22")

    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        f'KE-KIMAWASCO-149448-CW-RFB\'s notice said "{said}"', f'Its notice said "{said}"']
    assert removed_reasons(parsed) == [[("quote_not_on_page", None)]]
    checks = of(parsed, "checks")[0]
    assert (checks["shown"]["proven"], checks["judge"]["called"]) == (2, False)


class NothingFollows:
    """A judge for check 4 that finds no sentence follows, and keeps every sentence it was asked about."""

    name = "nothing follows"

    def __init__(self):
        self.asked = []

    def judge(self, questions):
        self.asked += [question.sentence for question in questions]
        return [Judgement(question.index, False, "It does not follow.") for question in questions]


def test_a_quote_of_only_an_identifier_goes_to_the_judge_as_a_quote_of_only_a_number_does(fixture_db):
    """Ticket 24's review round 3, follow-up 9: a quoted STEP reference is on its record, so the sentence counted as
    proven, though only the judge can check "still open". A quote that is a whole identifier of the cited row, or
    reads as an id, proves nothing about the sentence around it. KE-ICTA-571738-CW-RFB is one of the comparable
    packages still open (values.toml past_range)."""
    package = "strata.gold.package:KE-ICTA-571738-CW-RFB"
    judge = NothingFollows()

    def answer(outputs):
        assert package in [row["evidence_id"] for row in outputs[0]["rows"]]
        return [claim('Another, "KE-ICTA-571738-CW-RFB", was still open too.', kind="record", evidence_ids=[package])]

    agent = CallsThenAnswers([("find_comparables", {"step_reference": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"})],
                             answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools(), judge, asof="2026-10-22")

    assert judge.asked == ['Another, "KE-ICTA-571738-CW-RFB", was still open too.']
    assert [item["reason"] for item in of(parsed, "removed")] == ["not_supported"]


class FindsAdvice:
    """A judge for check 4 that finds every sentence follows, and that each sentence starting "You should" gives
    advice."""

    name = "finds advice"

    def judge(self, questions):
        return [Judgement(question.index, True, "It follows.", advises=question.sentence.startswith("You should"))
                for question in questions]


def test_advice_labelled_as_another_kind_is_held_to_check_5_when_the_judge_says_it_advises(fixture_db):
    """Ticket 24's verify round 3, O1: advice labelled record or summary skipped check 5, since check 5 trusts the
    kind the agent sets. The judge now says whether each sentence tells the reader what to do, in the same call, and
    a sentence that advises without citing a lesson or a comparable is removed with check 5's reason. ICR paragraph
    54 is a passage, which backs no advice (config/tools.toml, backs_advice)."""
    def answer(outputs):
        return [claim("You should base your works estimates on market rates.", kind=kind, evidence_ids=[ICR_54])
                for kind in ("record", "summary")] + [
            claim("The completion report discussed works estimates.", kind="summary", evidence_ids=[ICR_54])]

    agent = CallsThenAnswers([("search_passages", {"query": "works contracts advertised again rebidding",
                                                   "project_id": "P130164", "as_of": "2026-10-23"})], answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools(), FindsAdvice())

    assert [(item["sentence"], item["kind"], item["reason"], item["reasons"][0]["check"])
            for item in of(parsed, "removed")] == [
        ("You should base your works estimates on market rates.", "record", "advice_without_lesson_or_comparable", 5),
        ("You should base your works estimates on market rates.", "summary", "advice_without_lesson_or_comparable", 5)]
    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        "The completion report discussed works estimates."]
    assert of(parsed, "checks")[0]["advice"] == {"total": 2, "cited": 0}


def test_a_count_of_packages_is_not_backed_by_one_comparable_s_days(tmp_path):
    """Ticket 27's verify finding 1: estimate_time's summary holds every comparable's days at every step, so "ran
    longest in 17 of 25" was kept on the hand-made set because one comparable's stage took 17 days; the tool says 15
    of 25 (values.toml [step_dates], longest_n and longest_m). A value under a days field backs only a number written
    in days."""
    import step_set

    step_set.build(tmp_path / "set.duckdb").close()
    known = TRUTH["step_dates"]

    def answer(outputs):
        summary = outputs[0]["summary"]["evidence_id"]
        days = [entry["days"] for step in outputs[0]["step_dates"]["steps"] for entry in step["comparables"]]
        assert 17 in days and known["longest_n"] != 17
        return [claim(f"Bid evaluation ran longest in {n} of {known['longest_m']} comparable packages.", kind="record",
                      evidence_ids=[summary]) for n in (17, known["longest_n"])]

    agent = CallsThenAnswers([("estimate_time", {"step_reference": known["target"],
                                                 "as_of": known["as_of"].isoformat()})], answer)

    parsed = ask_with_tools(tmp_path / "set.duckdb", agent, with_adapter("estimate_time", "without_abstention"),
                            asof=known["as_of"].isoformat())

    assert removed_reasons(parsed) == [[("number_not_in_records", "17")]]
    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        f"Bid evaluation ran longest in {known['longest_n']} of {known['longest_m']} comparable packages."]


def test_an_answer_can_quote_each_side_of_a_disagreement_and_state_the_trajectory_and_the_rejected_count(fixture_db):
    """get_disagreements returns each side of a disagreement as a record of its own, under the evidence id
    ticket 11 or 18 issued for it, and its trajectories and rejected count as one citable summary record
    (CLAUDE.md rules 1 and 2). So the agent can quote the ICR's paragraph 78 from its side, state ISR 7's
    rating and date, and say how the ISRs' ratings ran, and a number no record holds is still removed. The
    values are tests/ground_truth/values.toml's."""
    truth = {entry["id"]: entry for entry in TRUTH["value"]}
    words = truth["icr-para-78"]["value"]
    isr_7_date = truth["isr-7-date"]["value"]

    def answer(outputs):
        [result] = outputs
        [row] = [row for row in result["rows"] if row["attribute"] == "pdo_progress"]
        isr_7, paragraph = row["sides"]
        summary = result["summary"]["evidence_id"]
        return [
            claim(f'The ICR said "{words}".', kind="quote", evidence_ids=[paragraph["evidence_id"]],
                  quote={"text": words, "passage_id": paragraph["evidence_id"]}),
            claim(f"ISR 7 rated progress towards the PDO Satisfactory on {isr_7_date:%B} {isr_7_date.day}, "
                  f"{isr_7_date.year}.", kind="record", evidence_ids=[isr_7["evidence_id"], row["evidence_id"]]),
            claim("ISRs 1 to 9 rated it Satisfactory and ISRs 12 and 13 rated it Moderately Unsatisfactory.",
                  kind="record", evidence_ids=[summary]),
            claim("I left out 1 assertion read from the project's reports.", kind="record", evidence_ids=[summary]),
            claim("ISRs 1 to 14 rated it Satisfactory.", kind="record", evidence_ids=[summary]),
            # A side that rests on a passage backs only its dates and its quote, so ISR 7's sequence needs the row
            # cited too, as get_disagreements' description says (ticket 20's review round 3, F2).
            claim(f"ISR 7 rated progress towards the PDO Satisfactory on {isr_7_date:%B} {isr_7_date.day}, "
                  f"{isr_7_date.year}.", kind="record", evidence_ids=[isr_7["evidence_id"]]),
        ]

    agent = CallsThenAnswers([("get_disagreements", {"subject_id": "P130164", "as_of": "2026-10-23"})], answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert [sentence["text"].split(" ")[:2] for sentence in of(parsed, "sentence")] == [
        ["The", "ICR"], ["ISR", "7"], ["ISRs", "1"], ["I", "left"]]
    assert removed_reasons(parsed) == [[("number_not_in_records", "14")], [("number_not_in_records", "7")]]
    evidence = {item["id"]: item for item in of(parsed, "evidence")}
    side = evidence["strata.gold.passage:31525018/v1/78"]
    assert (side["kind"], side["tool"]) == ("passage", "get_disagreements")
    [highlight] = side["highlights"]
    assert side["row"]["text"][highlight["start"]:highlight["end"]] == words
    assert of(parsed, "checks")[0]["quotes"] == {"total": 1, "found": 1}


def test_a_search_after_get_disagreements_keeps_the_side_s_own_values_under_its_id(fixture_db):
    """Ticket 20's review round 3, F7: a later search_passages row replaced the side get_disagreements returned under
    the same id, so the side's own values, such as the mid-term review's date that ICR paragraph 78 is about (its
    period), could no longer back a sentence citing it. Every record that came back under one id is kept."""
    paragraph = "strata.gold.passage:31525018/v1/78"

    def answer(outputs):
        assert paragraph in [row["evidence_id"] for row in outputs[1]["rows"]]
        return [claim("The ICR said the mid-term review of May 16, 2016 found part of the PDO compromised.",
                      kind="record", evidence_ids=[paragraph])]

    agent = CallsThenAnswers([
        ("get_disagreements", {"subject_id": "P130164", "as_of": "2026-10-23"}),
        ("search_passages", {"query": "clearly identified at the MTR that the achievement of part of the PDO was "
                                      "compromised", "project_id": "P130164", "as_of": "2026-10-23"})], answer)

    parsed = ask_with_tools(fixture_db, agent, load_tools())

    assert removed_reasons(parsed) == []
    [sentence] = of(parsed, "sentence")
    assert sentence["dates"] == [{"text": "May 16, 2016", "evidence_id": paragraph}]


def logged_runs(ops_db):
    with DuckDBEngine.open(ops_db, read_only=True) as engine:
        result = engine.run("SELECT * FROM strata.ops.agent_runs")
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def test_the_run_names_the_agent_version_that_answered(ops_db):
    """The Foundry agent learns its version from its first response, so the run reads it afterwards."""
    class Versioned(Answers):
        def respond(self, items, previous_response_id):
            self.version = "7"
            return super().respond(items, previous_response_id)

    ask_with(create_app(runner=answer_runner(lambda turn: Versioned(claim("No one said why.")), no_engine),
                        runs=RunLog(lambda: DuckDBEngine.open(ops_db))))

    assert [run["agent_version"] for run in logged_runs(ops_db)] == ["7"]


def test_a_run_that_never_reached_its_tools_logs_no_as_of_date_after_its_own_day(ops_db):
    ask_with(create_app(runs=RunLog(lambda: DuckDBEngine.open(ops_db))), asof="2027-03-01")

    [run] = logged_runs(ops_db)
    assert (run["error_code"], run["as_of"]) == ("no_agent", run["finished_at"].date())


def test_a_data_service_that_fails_during_a_tool_call_ends_the_answer_with_its_own_error():
    @contextmanager
    def down(viewer):
        raise EngineError("The SQL warehouse did not answer in time.")
        yield

    agent = CallsThenAnswers([("search_passages", {"query": "rebidding", "as_of": "2026-10-23"})], lambda outputs: [])

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: agent, down), new_run_id=lambda: "run-0004")))

    assert parsed[-2:] == [("error", {"code": "data_service"}), ("done", {"run_id": "run-0004"})]


def test_a_run_log_that_cannot_write_leaves_the_answer_as_it_was(ask_case, tmp_path):
    parsed, _ = ask_case("p130164-rebidding", runs=RunLog(lambda: DuckDBEngine.open(tmp_path / "no-tables.duckdb")))

    assert len(of(parsed, "sentence")) == 3 and parsed[-1][0] == "done"


@contextmanager
def no_engine(viewer):
    raise AssertionError("This run calls no tool.")
    yield


def ask_with(app, question="Why were works contracts in P130164 advertised again?", **body):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.post("/api/ask", headers=ANA, json={"question": question, **body})
    return asyncio.run(go()).text


@pytest.mark.parametrize("case_id, recorded", sorted(RECORDED_STREAMS.items()))
def test_the_server_sends_the_streams_the_screen_tests_serve(fixture_db, case_id, recorded):
    sent = stream_text(load_cases()[case_id], fixture_db)

    assert sent == (RECORDED / recorded).read_text(), (
        f"Check the change, then write the file again: uv run --frozen python -m strata.agent.scripted {case_id} "
        f"> tests/fixtures/api/{recorded}")


@pytest.mark.parametrize("code, recorded", [("agent_unavailable", "ask-agent-unavailable.sse"),
                                            ("content_filter", "ask-content-filter.sse")])
def test_the_server_sends_the_failed_streams_the_screen_tests_serve(code, recorded):
    sent = failed_stream_text(code)

    assert events(sent) == [("error", {"code": code}), ("done", {"run_id": "run-0001", "trace_ids": {
        "application_insights": "4bf92f3577b34da6a3ce929d0e0e4736", "mlflow": "tr-0af7651916cd43dd8448eb211c80319c"}})]
    assert sent == (RECORDED / recorded).read_text(), (
        f"Check the change, then write the file again: uv run --frozen python -m strata.agent.scripted --error {code} "
        f"> tests/fixtures/api/{recorded}")


def test_a_number_matched_to_an_isr_section_sits_inside_the_highlight_of_the_quote_that_backs_it(ask_case):
    """A passage backs a number only inside quoted words (check 1), so a number the verifier matched to an
    ISR's section is always inside that quote, and the quote's highlight shows it in the evidence card and
    drawer. A second source the sentence cites but does not quote gets no highlight."""
    isr, annex = "strata.gold.passage:19095337/v1/s4", "strata.gold.passage:31525018/v1/s38"
    parsed, _ = ask_case("p130164-isr-section")

    [quoting] = [sentence for sentence in of(parsed, "sentence") if isr in sentence["evidence_ids"]]
    assert quoting["evidence_ids"] == [isr, annex]
    assert quoting["numbers"] == [{"text": "67.00", "evidence_id": isr}, {"text": "67.00", "evidence_id": isr},
                                  {"text": "80.00", "evidence_id": isr}]
    sources = {evidence["id"]: evidence for evidence in of(parsed, "evidence")}
    [highlight] = sources[isr]["highlights"]
    assert highlight["sentence"] == quoting["index"]
    # values.toml, isr-1-rural-access-end-target.
    assert sources[isr]["row"]["text"][highlight["start"]:highlight["end"]] == "Percentage Value 67.00 67.00 80.00"
    assert sources[annex]["highlights"] == []
    assert (sources[isr]["row"]["paragraph_numbered"], sources[annex]["row"]["paragraph_numbered"]) == (False, False)
    assert of(parsed, "removed") == []


def test_an_agent_that_finds_nothing_to_cite_writes_no_sentence_and_the_checks_count_none(ask_case):
    parsed, _ = ask_case("p130164-nothing-found")

    assert of(parsed, "sentence") == [] and of(parsed, "removed") == []
    assert of(parsed, "checks")[0]["sentences"] == {"written": 0, "kept": 0, "removed": 0}
    assert parsed[-1][0] == "done"


def test_every_reason_the_verifier_gives_has_its_sentence_in_the_copy_file():
    from strata.agent.verifier import REASONS

    sentences = copy_reasons()
    assert [code for code in REASONS if not (sentences.get(code) or {}).get("item")
            or not sentences[code].get("joined")] == []


def test_every_error_the_answer_stream_can_send_has_its_sentence_in_the_copy_file():
    from strata.harness.turn import ERROR_CODES

    sentences = copy_errors()
    assert [code for code in ERROR_CODES if not sentences.get(code)] == []
    # Each code a run raises by name is one the stream may send.
    source = Path(__file__).resolve().parents[1] / "src" / "strata"
    raised = {code for path in source.rglob("*.py")
              for code in re.findall(r'(?:AgentError|RunError)\(\s*"(\w+)"', path.read_text())}
    assert raised and raised - set(ERROR_CODES) == set()


def test_an_error_code_the_copy_file_has_no_sentence_for_goes_out_as_internal():
    async def runner(turn):
        raise RunError("made_up_code", "No sentence anywhere says this.")
        yield

    parsed = events(ask_with(create_app(runner=runner, new_run_id=lambda: "run-0005")))

    assert parsed == [("error", {"code": "internal"}), ("done", {"run_id": "run-0005"})]


def copy_errors():
    """The answer's error sentences, read from the copy file (web/src/copy.ts, answer.errors)."""
    text = (Path(__file__).resolve().parents[1] / "web" / "src" / "copy.ts").read_text()
    answer = re.search(r"\n  answer: \{(.*?)\n  \},", text, re.S).group(1)
    errors = re.search(r"errors: \{(.*?)\n    \}", answer, re.S).group(1)
    return dict(re.findall(r'(\w+):\s*"([^"]*)"', errors))


def copy_reasons():
    """The removed box's reasons, read from the copy file (web/src/copy.ts, removed.reasons): each code's
    list item ("No record supports this number.") and its clause ("no record supports that number")."""
    text = (Path(__file__).resolve().parents[1] / "web" / "src" / "copy.ts").read_text()
    removed = re.search(r"\n  removed: \{(.*?)\n  \},", text, re.S).group(1)
    reasons = re.search(r"reasons: \{(.*?)\n    \}", removed, re.S).group(1)
    return {code: {"item": item, "joined": joined} for code, item, joined in re.findall(
        r'(\w+): \{\s*item: "([^"]*)",\s*joined: "([^"]*)",?[^}]*\}', reasons)}


def test_a_claim_whose_number_rests_only_on_a_table_summary_passage_is_removed_with_its_own_reason(ask_case):
    """Ticket 18, criterion 7, through the answer contract with the scripted agent: the PAD's risk annex
    has one summary passage, which names its eight risks (tests/ground_truth/values.toml,
    stress_shelf.pad_risk_annex). The number is in the summary and in no row the sentence cites, so the
    sentence is removed, and the removed box gets the summary's reason, not "no record supports this
    number". The other sentences stand."""
    annex = TRUTH["stress_shelf"]["pad_risk_annex"]
    summary = f"strata.gold.passage:{annex['document_id']}/v1/table{annex['first_pdf_page']}"
    parsed, _ = ask_case("p130164-number-from-a-table-summary")

    [removed] = of(parsed, "removed")
    assert removed["sentence"] == "The appraisal document's risk annex rated 8 risks."
    assert removed["reason"] == "number_only_in_table_summary"
    assert removed["reasons"] == [{"check": 1, "code": "number_only_in_table_summary", "text": "8"}]
    assert str(annex["risks"]) == "8"
    assert [sentence["index"] for sentence in of(parsed, "sentence")] == [0, 1, 2]
    assert summary not in {evidence["id"] for evidence in of(parsed, "evidence")}
