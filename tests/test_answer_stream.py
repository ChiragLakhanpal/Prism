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
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.agent.loop import answer_runner
from strata.agent.runs import RunLog
from strata.agent.scripted import ScriptedAgent, failed_stream_text, load_cases, stream_text
from strata.config import load_tools
from strata.harness.turn import Event, RunError, TraceIds
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine, EngineError
from strata.reader.passages import TABLE_SUMMARY
from strata.server.app import create_app
from strata.tools.check_plan import check_plan
from strata.tools.search_passages import search_passages

RECORDED = Path(__file__).parent / "fixtures" / "api"
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

        app = create_app(runner=answer_runner(agent_for, engine_for, today=lambda: today),
                         new_run_id=lambda: "run-0001", **app_options)

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
    assert json.loads(run["response_ids"]) == ["resp_p130164_rebidding_1", "resp_p130164_rebidding_2"]
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


def test_numbers_and_dates_the_agent_lists_but_does_not_write_are_checked_too():
    unwritten = {"sentence": "Bids took a while to open.", "kind": "summary", "evidence_ids": [],
                 "numbers": [], "dates": ["45", "March 3, 2015"], "quote": None}

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(unwritten), no_engine))))

    assert [reason["code"] for reason in of(parsed, "removed")[0]["reasons"]] == [
        "number_not_in_records", "date_not_in_records"]


def test_a_fiscal_year_is_a_number_a_record_must_hold():
    fiscal = {"sentence": "Most of the works were signed in FY2019.", "kind": "summary", "evidence_ids": [],
              "numbers": [], "dates": [], "quote": None}

    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(fiscal), no_engine))))

    assert [(reason["code"], reason["text"]) for reason in of(parsed, "removed")[0]["reasons"]] == [
        ("number_not_in_records", "FY2019")]


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

    assert [[(reason["code"], reason["text"]) for reason in item["reasons"]] for item in of(parsed, "removed")] == [
        [("number_not_in_records", "Six")], [("number_not_in_records", "one"), ("number_not_in_records", "37")],
        [("number_not_in_records", "One")], [("number_not_in_records", "one")], [("number_not_in_records", "One")],
        [("number_not_in_records", "Zero")], [("number_not_in_records", "one")], [("number_not_in_records", "half")],
        [("number_not_in_records", "one")], [("number_not_in_records", "FY2019")]]
    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        "No one said why.", "Each one was signed late.", "The works started in the first half of the year.",
        "The contractors' bids came late, and the World Bank's review followed.",
        "The works slowed in the second half."]
    # Apostrophes are not quote marks, so that sentence quotes nothing.
    assert of(parsed, "checks")[0]["quotes"] == {"total": 0, "found": 0}


def claim(sentence, **fields):
    return {"sentence": sentence, "kind": "summary", "evidence_ids": [], "numbers": [], "dates": [], "quote": None,
            **fields}


def removed_reasons(parsed):
    return [[(reason["code"], reason["text"]) for reason in item["reasons"]] for item in of(parsed, "removed")]


def test_a_number_joined_to_a_unit_or_a_range_or_written_as_a_word_above_nine_is_a_number_a_record_must_hold():
    """Every digit run is a number unless its whole token is an id: a project, a loan (four digits or
    more, as STEP writes it, "IDA / 60300"), a STEP reference (three parts or more, joined by hyphens or
    slashes, "KE/TAVEVO/82755/GO/RFQ"), a passage or a section label, so Q3-2020 and "IBRD 45 contracts"
    are read. "45-day", "US$1.2M", "300k" and "3x" are read as their digits, "10-15" and
    "2019/20" as two numbers each, and number words go past nine. "Half" and "a dozen" are numbers too."""
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
    ), no_engine))))

    assert removed_reasons(parsed) == [
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
    ]
    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        "The COVID-19 pause held up P130164, IDA-60290 and KE-NWWDA-541062-CW-RFQ under III.B and 10.b.",
        "IDA 51030KE paid for NWWDA-WSDP-03-2019-2020 and MWI-WSDP-001.",
        "It was financed by IDA / 60300.",
        "The bid KE/TAVEVO/82755/GO/RFQ was signed, and so was KALRO/HQTS/053/23-24.",
        "IDA \u2013 6030 KE paid for CF/RRSMP/11-15."]
    assert of(parsed, "checks")[0]["numbers"]["matched"] == 0


class CallsThenAnswers:
    """An agent that makes one round of tool calls, then answers with the claims answer() writes from
    the tool results it got back, as a list of each call's output."""

    name, version = "strata-orchestrator", None

    def __init__(self, calls, answer):
        self.calls, self.answer, self.round = calls, answer, 0

    def respond(self, items, previous_response_id):
        self.round += 1
        if self.round == 1:
            return {"id": "resp_1", "output": [
                {"type": "function_call", "call_id": f"call_{number}", "name": name, "arguments": json.dumps(arguments)}
                for number, (name, arguments) in enumerate(self.calls, 1)]}
        claims = self.answer([json.loads(item["output"]) for item in items])
        return Answers(*claims).respond(items, previous_response_id)


def with_adapter(name, adapter):
    """The tool registry with one tool's adapter replaced by a stand-in in this file."""
    tools = load_tools()
    return {**tools, name: dataclasses.replace(tools[name], adapter=f"test_answer_stream:{adapter}")}


def as_table_summaries(call, **arguments):
    """search_passages, with every passage it finds marked as a table's one summary passage."""
    result = search_passages(call, **arguments)
    for row in result["rows"]:
        row["parse_route"] = TABLE_SUMMARY
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


def ask_with_tools(fixture_db, agent, tools):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    return events(ask_with(create_app(runner=answer_runner(lambda turn: agent, engine_for, tools=tools,
                                                           today=lambda: TODAY))))


def test_a_number_quoted_from_a_table_summary_is_not_backed_by_it(fixture_db):
    """A table's summary passage is the reader's words for a table, not the report's, so even a number
    inside a quote from it must match a record (spec, check 1)."""
    rebidding = "108 of 328 cases had to go through rebidding"
    agent = CallsThenAnswers(
        [("search_passages", {"query": "works contracts advertised again rebidding", "project_id": "P130164",
                              "as_of": "2026-10-23"})],
        lambda outputs: [claim(f'The report said "{rebidding}".', kind="quote", evidence_ids=[ICR_54],
                               numbers=["108", "328"], quote={"text": rebidding, "passage_id": ICR_54})])

    parsed = ask_with_tools(fixture_db, agent, with_adapter("search_passages", "as_table_summaries"))

    assert removed_reasons(parsed) == [[("number_not_in_records", "108"), ("number_not_in_records", "328")]]


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

    parsed = ask_with_tools(fixture_db, agent, with_adapter("check_plan", "with_two_envelopes"))

    assert [sentence["text"] for sentence in of(parsed, "sentence")] == [
        'Its market approach was "Single Stage - Two Envelope".', "It went to market as Single Stage - Two Envelope."]
    # KE-NWWDA-541062-CW-RFQ holds a 1 only inside 541062, so a quoted "1" is not on the record.
    assert removed_reasons(parsed) == [
        [("number_not_in_records", "Thirty-seven")], [("number_not_in_records", "two")], [("quote_not_on_page", None)],
        [("quote_not_on_page", None)]]


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


@pytest.mark.parametrize("case_id, recorded", [("p130164-rebidding", "ask-p130164-rebidding.sse"),
                                               ("p130164-number-with-no-record", "ask-p130164-removed-number.sse"),
                                               ("p130164-nothing-found", "ask-p130164-nothing-found.sse"),
                                               ("p130164-before-the-icr", "ask-p130164-before-the-icr.sse")])
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
        r'(\w+): \{\s*item: "([^"]*)",\s*joined: "([^"]*)",?\s*\}', reasons)}
