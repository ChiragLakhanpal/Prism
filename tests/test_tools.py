"""The tool registry and its tools at seam 2, the tool contract.

The registry, config/tools.toml, is the one place a tool is defined (spec, "Ten single places",
item 2): its name, description, parameters, adapter and result shape. Every tool takes an
optional as-of date (ADR 0002), and the agent's tool list is generated from the file.

check_plan is called by name through the registry, on the fixture database. Expected marks and
values come from tests/ground_truth/values.toml, which quotes the October 9, 2026 plan with its
page and gives the mark the blueprint's Check a plan wireframe draws for each row, and from the
ticket. They are never computed the way the tool computes them.
"""

import dataclasses
import datetime as dt
import re
import shutil
import tomllib
from pathlib import Path

import pytest

from strata import config
from strata.config import ConfigError
from strata.dbx import Viewer
from strata.evals import benchmark
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
BENCHMARK = {"questions": benchmark.load()}
NWWDA = "Northern Water Works Development Agency"
ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
WIREFRAME_MARKS = {"Needs a look": ["needs_a_look"], "Watch": ["watch"], "Data note": ["data_note"], "No signals": []}


def value(key: str):
    return next(entry for entry in TRUTH["value"] if entry["id"] == key)["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def check_plan(engine, thresholds=None, **arguments):
    """check_plan on the NWWDA plans for P156634, called by name through the registry as Ana."""
    context = registry.Context(engine=engine, viewer=ANA, **({"thresholds": thresholds} if thresholds else {}))
    return registry.call("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA, **arguments}, context)


def marks(result) -> dict[str, list[str]]:
    return {row["activity_reference_no"]: [mark["mark"] for mark in row["marks"]] for row in result["rows"]}


def reasons(result, reference: str) -> dict[str, dict]:
    [row] = [row for row in result["rows"] if row["activity_reference_no"] == reference]
    return {reason["code"]: reason for mark in row["marks"] for reason in mark["reasons"]}


def copy_registry(tmp_path, old=None, new=None):
    """A copy of the tool registry, with one piece of text replaced."""
    target = tmp_path / "tools.toml"
    shutil.copy(ROOT / "config" / "tools.toml", target)
    if old is not None:
        text = target.read_text()
        assert old in text, f"{old!r} is not in config/tools.toml"
        target.write_text(text.replace(old, new, 1))
    return target


# ── The registry ─────────────────────────────────────────────────────────

def test_every_tool_in_the_registry_takes_an_optional_as_of_date_and_declares_its_result_shape():
    tools = config.load_tools()

    assert "check_plan" in tools
    for tool in tools.values():
        as_of = tool.parameter("as_of")
        assert (as_of.type, as_of.required) == ("date", False), f"{tool.name} lacks an optional as_of date"
        assert tool.result.row, f"{tool.name} does not say what one row is"
        assert {"evidence_id", "public_from", "source"} <= set(tool.result.row_fields), (
            f"{tool.name}'s rows do not carry an evidence id, a public date and a source line")
        assert tool.result.source_fields, f"{tool.name} does not name its source-line fields"


@pytest.mark.parametrize("old, new, says", [
    ('name = "as_of"', 'name = "on_date"', "needs an optional as_of parameter"),
    ("[tools.check_plan.result]", "[tools.check_plan.output]", "has no result shape"),
    ('row_fields = ["evidence_id", "public_from", "source", ', 'row_fields = [', "lacks evidence_id"),
    ("max_output_chars = 200000", "max_output_chars = 0", "max_output_chars must be a whole number of characters"),
], ids=["no-as-of-date", "no-result-shape", "rows-without-an-evidence-id", "a-cap-of-no-characters"])
def test_a_tool_without_an_as_of_date_or_a_result_shape_is_refused(tmp_path, old, new, says):
    path = copy_registry(tmp_path, old, new)

    with pytest.raises(ConfigError, match=says):
        config.load_tools(path)


def test_the_agents_tool_list_is_generated_from_the_registry_and_holds_exactly_its_tools():
    tools = config.load_tools()

    listed = registry.agent_tools()

    assert [tool["name"] for tool in listed] == list(tools)
    for tool in listed:
        assert tool["type"] == "function"
        # The registry's description, with each value of the thresholds file it names in braces filled in.
        assert tool["description"] == registry._filled(tools[tool["name"]].description, config.load_thresholds())
        assert tool["parameters"]["properties"]["as_of"] == {
            "type": "string", "format": "date", "description": tools[tool["name"]].parameter("as_of").description}
        assert "as_of" not in tool["parameters"]["required"]


def tool_list_texts() -> list[str]:
    """Every text the agent's tool list holds: each tool's description, then each parameter's."""
    listed = registry.agent_tools()
    return [tool["description"] for tool in listed] + [
        parameter["description"] for tool in listed for parameter in tool["parameters"]["properties"].values()]


def test_the_agents_limit_description_takes_its_numbers_from_the_thresholds_file(tmp_path):
    """The prompt and the tool use the same numbers, so changing the thresholds file changes both."""
    text = (ROOT / "config" / "thresholds.toml").read_text()
    path = tmp_path / "thresholds.toml"
    path.write_text(text.replace("\nmax_results = 20\n", "\nmax_results = 15\n"))

    def limit(thresholds=None) -> str:
        [tool] = [tool for tool in registry.agent_tools(thresholds=thresholds) if tool["name"] == "search_passages"]
        return tool["parameters"]["properties"]["limit"]["description"]

    assert limit() == "How many passages to return, from 1 to 20. Leave it out for 10."
    assert limit(config.load_thresholds(path)) == "How many passages to return, from 1 to 15. Leave it out for 10."
    assert [text for text in tool_list_texts() if "{" in text] == []


def test_the_sector_parameter_names_the_slice_file_s_sectors(monkeypatch):
    """Ticket 11's review round 2, P3: the sector parameter's description named the slice's sectors by hand, so a
    sector added to config/slice.toml never reached the agent's prompt. The tool list fills {slice.sectors} from the
    slice file, the one place the sectors are listed (CLAUDE.md rules 4 and 9), joined as a reader lists them: a
    comma between each, and "or" before the last when there are three or more (ticket 61's review, F7)."""
    def sector_line() -> str:
        [tool] = [tool for tool in registry.agent_tools() if tool["name"] == "search_passages"]
        return tool["parameters"]["properties"]["sector"]["description"]

    assert sector_line() == "Only passages of projects in this sector of the pilot slice: water or transport."
    assert any("{slice.sectors}" in parameter.description
               for parameter in config.load_tools()["search_passages"].parameters)
    three = dataclasses.replace(config.load_slice(), sectors=("water", "transport", "energy"))
    monkeypatch.setattr(registry, "load_slice", lambda: three)
    assert sector_line() == "Only passages of projects in this sector of the pilot slice: water, transport, or energy."


def test_the_descriptions_say_what_the_agent_needs_to_know_in_plain_sentences():
    """The tools' descriptions are the agent's prompt (CLAUDE.md rule 4): check_plan's rule for which packages it
    checks in two plain sentences (ticket 09's review round 2, R2-P6), every reason search_passages leaves a passage
    out (ticket 11's review round 2, P2), and that a number on a side of a disagreement needs its row cited (ticket
    20's review round 3, F2)."""
    tools = {tool["name"]: tool["description"] for tool in registry.agent_tools()}

    assert ("For a package with no signed contract, it checks whether the planned completion date has passed. It skips "
            "a package estimated below the amount in the result's thresholds, and checks one that has no estimate."
            ) in tools["check_plan"]
    assert "the coverage line says how many. So is a passage that has no Prompt Shields result yet." in (
        tools["search_passages"])
    assert ("For a number on a side, such as ISR 7's sequence or the months after the mid-term review, cite the row as "
            "well.") in tools["get_disagreements"]


def never_written() -> list[str]:
    """DESIGN.md section 7, rule 19's list of words Prism never writes, read from the file, as the
    copy lint (web/lint/copy.ts) reads it."""
    import re

    [rule] = re.findall(r"\n19\. Never write: ([^\n]+)", (ROOT / "DESIGN.md").read_text())
    listed = re.sub(r"\([^)]*\)", "", rule[:re.search(r"\.\s+[A-Z]", rule).start()])
    return [word.strip() for word in re.split(r"[;,]", listed) if word.strip()]


def test_the_agents_tool_list_uses_no_word_design_md_says_strata_never_writes():
    """The agent reads each description as its prompt and may repeat its words in an answer."""
    import re

    words = never_written()
    texts = tool_list_texts()

    def forms(word: str) -> str:
        """Every form of the word: approve, approves, approved, approving; flag, flags, flagged, flagging."""
        *first, last = word.split()
        ending = (re.escape(last[:-1]) + "(?:e|es|ed|ing)" if last.endswith("e")
                  else re.escape(last) + f"(?:s|es|ed|ing|{last[-1]}ed|{last[-1]}ing)?")
        return r"\b" + r"\s+".join([*map(re.escape, first), ending]) + r"\b"

    found = [(word, text) for text in texts for word in words if re.search(forms(word), text, re.I)]
    assert "flag" in words and "approve" in words
    assert found == []
    assert [text for text in texts if "\u2014" in text or "!" in text] == []


def test_every_tool_names_its_benchmark_question_and_reads_only_registered_sources():
    questions = {question["id"]: question for question in BENCHMARK["questions"]}
    sources = config.load_sources()

    for tool in config.load_tools().values():
        assert tool.benchmark in questions, f"{tool.name}'s question {tool.benchmark} is not in evals/benchmark.yaml"
        assert questions[tool.benchmark]["tool"] == tool.name
        assert set(tool.sources) <= set(sources), f"{tool.name} reads a source the source registry lacks"


def test_each_tool_that_answers_a_kind_of_question_names_it_and_the_readiness_rows_it_draws_on():
    """The 16 brief, section 5.1: a kind of question appears on the Data readiness page only when its
    tool is in the registry, and the tool's entry names its kind and the source rows it reads."""
    rows = {row.id for source in config.load_sources().values() for row in source.readiness}
    tools = config.load_tools()

    kinds = {name: tool.readiness.kind for name, tool in tools.items() if tool.readiness}
    assert kinds == {"check_plan": "plan_check", "search_passages": "document_search", "get_lessons": "lessons",
                     "find_comparables": "past_range"}  # ticket 63 added the past range
    for name in kinds:
        readiness = tools[name].readiness
        assert set(readiness.draws_on) <= rows, name
        assert readiness.ready_for_row in readiness.draws_on, name


from strata.evals.answers import ANSWERS, answered, expected  # noqa: E402,F401


def tool_questions():
    return [question for question in BENCHMARK["questions"] if "tool" in question]


def test_each_tool_with_a_benchmark_question_has_a_way_to_read_its_answer():
    assert {question["tool"] for question in tool_questions()} <= set(ANSWERS)


@pytest.fixture(scope="module")
def library(fixture_db, tmp_path_factory):
    """The fixture with its three proposed lessons decided, for a question that needs decided lessons: the
    library holds a lesson only after two people decide it (tests/lesson_scenario.py). It also holds the deep
    research run seeded for P156634 on November 5, 2026, for a question that needs a research run (ticket 148)."""
    import lesson_scenario as scenario
    from research_world import seed_run
    from strata.research.store import ResearchStore

    database = scenario.copy_of(fixture_db, tmp_path_factory.mktemp("benchmark-library"))
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(database, passage, dt.date(2026, 10, 27))
    with DuckDBEngine.open(database) as engine:
        ResearchStore(lambda: engine.cursor()).save(*seed_run(fixture_db))
    with DuckDBEngine.open(database, read_only=True) as opened:
        yield opened


def engine_for(question, engine, library):
    return library if question.get("needs") in ("decided_lessons", "research_run") else engine


def arguments_of(question, engine, library) -> dict:
    """The question's arguments (strata.evals.answers.arguments_of), on the engine the question needs."""
    from strata.evals.answers import arguments_of as question_arguments

    return question_arguments(question, engine_for(question, engine, library), ANA)


def test_each_tool_answers_its_benchmark_question_on_the_fixture_as_expected(engine, library):
    from strata.evals.scoring import returned

    for question in tool_questions():
        result = registry.call(question["tool"], arguments_of(question, engine, library),
                               registry.Context(engine=engine_for(question, engine, library), viewer=ANA))

        assert answered(result, question) == expected(question)
        # Each evidence id the answer must cite is one the tool returned, so the full gate can ask for it.
        assert set(question.get("cites") or ()) <= returned(result), question["id"]


def test_without_an_as_of_date_each_tool_answers_as_of_today(engine, library, monkeypatch):
    """The benchmark question's date stands in for today, so the expected answer still holds."""
    for question in tool_questions():
        today = dt.date.fromisoformat(question["arguments"]["as_of"])
        monkeypatch.setattr(registry, "today", lambda: today)
        arguments = {name: given for name, given in arguments_of(question, engine, library).items() if name != "as_of"}

        result = registry.call(question["tool"], arguments,
                               registry.Context(engine=engine_for(question, engine, library), viewer=ANA))

        assert result["as_of"] == today.isoformat()
        assert answered(result, question) == expected(question)


@pytest.mark.parametrize("view", ["piu"])
def test_each_tool_answers_under_each_view(engine, library, view):
    """The implementing agency view gets the World Bank staff result for every benchmark question. The public view
    leaves signals, time estimates and disagreements out on a project still under way (ticket 40), which
    tests/test_public_view.py proves."""
    for question in tool_questions():
        result = registry.call(question["tool"], arguments_of(question, engine, library),
                               registry.Context(engine=engine_for(question, engine, library), viewer=ANA, view=view))

        assert result["view"] == view
        assert answered(result, question) == expected(question)


def test_the_ground_truth_sql_uses_the_thresholds_file_s_plan_check_values():
    """The ground-truth SQL writes each threshold as a parameter, so it must change when the file does."""
    from strata.lakehouse import ground_truth

    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "check_plan_nwwda_2026_10_09.sql")
    plan_check = config.load_thresholds().values["plan_check"]

    assert {name: float(case.params[name]) for name in plan_check} == {
        name: float(number) for name, number in plan_check.items()}


def test_adding_a_tool_is_one_entry_and_the_agents_tool_list_grows_with_it(tmp_path):
    import re

    path = copy_registry(tmp_path)
    text = path.read_text()
    start = text.index("[tools.check_plan]")
    following = re.compile(r"^\[tools\.(?!check_plan[.\]])", re.M).search(text, start + 1)
    entry = text[start:following.start() if following else len(text)]
    path.write_text(text + "\n" + entry.replace("tools.check_plan", "tools.check_plan_again"))

    listed = registry.agent_tools(config.load_tools(path))

    assert [tool["name"] for tool in listed] == [*config.load_tools(), "check_plan_again"]


# ── check_plan on the NWWDA plan of October 9, 2026 ──────────────────────

# Ticket 132: the wireframe marks the plan's two Pending Implementation activities as if no contract were signed, but
# the contract awards say each was signed before the plan's date (values.toml, award-541055-signed and
# award-541062-signed). The records have moved past the plan, so each is moved on since the plan instead.
MOVED_ON = {"KE-NWWDA-541055-CW-RFB": "award-541055-signed", "KE-NWWDA-541062-CW-RFQ": "award-541062-signed"}


def test_check_plan_marks_each_activity_of_the_october_9_plan_as_the_wireframe_does(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    expected = {row["reference"]: WIREFRAME_MARKS[row["wireframe_mark"]] for row in TRUTH["plan_row"]}
    # The plan lists a ninth activity the wireframe leaves out. The tool checks every activity.
    expected |= {reference: [] for reference in TRUTH["plan"]["also_lists"]}
    expected |= {reference: ["moved_on"] for reference in MOVED_ON}
    assert marks(result) == expected
    # The screen shows the marked rows and folds the rest, so the counts say how many of each there are.
    # "signal" counts the activities that need a look or are worth watching, the rows "Draft review
    # notes (1 row)" drafts a note on (ticket 35). The two moved on since the plan are counted apart.
    assert result["counts"] == {"activities": 9, "checked": 9, "not_fully_checked": 0, "needs_a_look": 0, "watch": 1,
                                "moved_on": 2, "data_note": 3, "signal": 1, "marked": 6, "unmarked": 3}
    assert result["plan"]["plan_date"] == "2026-10-09"
    assert result["abstention"] is None


def test_ke_nwwda_541055_moved_on_since_the_plan_because_the_contract_awards_say_it_was_signed(engine):
    """Ticket 132, criterion 1: the plan still says Pending Implementation, and the contract awards say the contract
    was signed on June 22, 2026. The row is moved on since the plan, not still pending, and its reason cites the
    plan row, the disagreement between the two records and the contract record."""
    from strata.tools import get_disagreements

    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    found = reasons(result, "KE-NWWDA-541055-CW-RFB")
    assert set(found) == {"moved_on_since_plan"}  # no longer "passed with no signed contract"
    reason = found["moved_on_since_plan"]
    assert reason["mark"] == "moved_on"
    assert reason["process_status"] == value("plan-541055-status")
    assert (reason["signed_on"], reason["record"]) == (value("award-541055-signed").isoformat(), "contract_awards")
    held = registry.call("get_disagreements", {"subject_id": "KE-NWWDA-541055-CW-RFB", "as_of": "2026-10-22"},
                         registry.Context(engine=engine, viewer=ANA))
    [disagreement] = [row for row in held["rows"]
                      if "strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB" in row["source"]["evidence_ids"]]
    assert reason["disagreement_id"] == disagreement["disagreement_id"]
    assert reason["evidence_ids"] == ["strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB",
                                      f"{get_disagreements.TABLE}:{disagreement['disagreement_id']}",
                                      "strata.gold.contract:1903781"]


def test_a_pending_activity_with_no_later_step_done_from_another_record_stays_still_pending(engine):
    """Ticket 132, criterion 1: in the plan of March 5, 2026, KE-NWWDA-541061-CW-RFQ is Pending Implementation, and
    no contract record or award notice says it was signed (only the agency's later plan does), so as of October 22,
    2026 it is still pending 9 days before the project closes. In the same plan, the two activities the contract
    awards say were signed before the agency's next plan replaced it are moved on since the plan, counted apart."""
    result = check_plan(engine, plan_date="2026-03-05", as_of="2026-10-22")

    pending = reasons(result, "KE-NWWDA-541061-CW-RFQ")
    assert set(pending) == {"pending_near_closing"}
    assert (pending["pending_near_closing"]["mark"], pending["pending_near_closing"]["days_to_close"]) == ("watch", 9)
    assert {reference: marks(result)[reference] for reference in MOVED_ON} == {
        reference: ["moved_on"] for reference in MOVED_ON}
    for reference, signed in MOVED_ON.items():
        assert reasons(result, reference)["moved_on_since_plan"]["signed_on"] == value(signed).isoformat()
    # Worth watching: KE-NWWDA-541061-CW-RFQ, still pending, and KE-NWWDA-229129-CW-RFB, signed over its estimate.
    assert (result["counts"]["watch"], result["counts"]["moved_on"]) == (2, 2)


def test_before_the_award_was_public_the_plan_check_does_not_know_the_activity_moved_on(engine):
    """ADR 0002: the contract awards made KE-NWWDA-541055-CW-RFB's signing public on June 22, 2026, so a check of
    the plan of March 5, 2026 as of June 1 cannot know it; KE-NWWDA-541062-CW-RFQ's signing of May 11 it can."""
    result = check_plan(engine, plan_date="2026-03-05", as_of="2026-06-01")

    assert "moved_on" not in marks(result)["KE-NWWDA-541055-CW-RFB"]
    assert marks(result)["KE-NWWDA-541062-CW-RFQ"] == ["moved_on"]
    assert result["counts"]["moved_on"] == 1


def test_ke_nwwda_229129_is_worth_watching_signed_186_days_late_at_about_4_times_its_estimate(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    reason = reasons(result, "KE-NWWDA-229129-CW-RFB")["signed_late_over_estimate"]
    assert reason["mark"] == "watch"
    assert reason["signed_on"] == value("plan-229129-signed").isoformat()
    assert reason["days_late"] == value("plan-229129-days-late")
    assert reason["planned_signing_on"] == value("plan-229129-first-planned-signing").isoformat()
    assert reason["actual_amount_usd"] == "1245092.76"
    assert reason["estimated_amount_usd"] == "300000.00"
    assert (reason["ratio"], reason["ratio_exact"]) == (4, "4.15")  # 1,245,092.76 / 300,000.00 = 4.1503


def test_the_three_data_notes_say_what_is_weak_in_each_record(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    method = reasons(result, "KE-NWWDA-199461-GO-RFB")["method_differs_from_reference"]
    assert (method["reference_method_code"], method["method"]) == (
        value("plan-199461-reference-method"), value("plan-199461-method-column"))
    for reference, status in (("KE-NWWDA-503455-CW-RFQ", "Signed"), ("KE-NWWDA-541061-CW-RFQ", "Completed")):
        zero = reasons(result, reference)["actual_amount_zero"]
        assert (zero["mark"], zero["process_status"], zero["actual_amount_usd"]) == ("data_note", status, "0.00")


def test_every_row_carries_an_evidence_id_a_public_date_and_its_source_line(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    for row in result["rows"]:
        reference = row["activity_reference_no"]
        assert row["evidence_id"] == f"strata.silver.plan_rows:{result['plan']['document_id']}/{reference}"
        assert row["public_from"] == "2026-10-09"
        assert row["source"] | {"pdf_page": None} == {
            "document_type": "Procurement Plan", "project_id": "P156634", "implementing_agency": NWWDA,
            "plan_date": "2026-10-09", "document_id": result["plan"]["document_id"], "pdf_page": None}
        assert row["source"]["pdf_page"] >= 1
        for mark in row["marks"]:
            for reason in mark["reasons"]:
                assert row["evidence_id"] in reason["evidence_ids"]
    assert result["plan"]["evidence_id"] == f"strata.silver.plan_versions:{result['plan']['document_id']}"
    assert result["project"]["evidence_id"] == "strata.gold.project:P156634"


def test_each_row_gives_its_estimate_in_us_millions_to_two_decimals_as_home_writes_it(engine):
    """Ticket 41: Home's first line writes "US$1.23 million of works", a derived figure, so the tool returns it."""
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    millions = {row["activity_reference_no"]: row["estimated_millions"] for row in result["rows"]}
    # values.toml, plan-541055-estimated: US$1,230,000.00. Trailing zeros are dropped, as a sentence writes them.
    assert millions["KE-NWWDA-541055-CW-RFB"] == "1.23"
    assert millions["NWWDA-WSDP-03-2019-2020"] == "2"
    assert millions["KE-NWWDA-229129-CW-RFB"] == "0.3"


def leak_a_later_row(call, **arguments):
    """check_plan with its first row dated the day after the as-of date: the registry must refuse it."""
    from strata.tools.check_plan import check_plan as adapter
    result = adapter(call, **arguments)
    result["rows"][0]["public_from"] = (call.as_of + dt.timedelta(days=1)).isoformat()
    return result


def drop_an_evidence_id(call, **arguments):
    """check_plan with no evidence id on its first row: the registry must refuse it."""
    from strata.tools.check_plan import check_plan as adapter
    result = adapter(call, **arguments)
    del result["rows"][0]["evidence_id"]
    return result


def rename_a_reason(call, **arguments):
    """check_plan with a reason code the registry does not list, which the screen's copy has no
    sentence for: the registry must refuse it."""
    from strata.tools.check_plan import check_plan as adapter
    result = adapter(call, **arguments)
    marked = next(row for row in result["rows"] if row["marks"])
    marked["marks"][0]["reasons"][0]["code"] = "planned_completion_passed"
    return result


def invent_an_abstention(call, **arguments):
    """check_plan abstaining for a reason the registry does not list: the registry must refuse it."""
    from strata.tools.check_plan import check_plan as adapter
    return {**adapter(call, **arguments), "rows": [], "abstention": {"reason": "plan_not_ready"}}


def invent_a_coverage_reason(call, **arguments):
    """check_plan saying it left a row out for a reason the registry does not list, which the coverage
    line's copy has no sentence for: the registry must refuse it."""
    from strata.tools.check_plan import check_plan as adapter
    result = adapter(call, **arguments)
    result["coverage"]["not_used"].append({"reason": "row_skipped", "count": 1,
                                           "evidence_ids": [result["rows"][0]["evidence_id"]]})
    return result


@pytest.mark.parametrize("adapter", ["leak_a_later_row", "drop_an_evidence_id", "rename_a_reason",
                                     "invent_an_abstention", "invent_a_coverage_reason"])
def test_the_registry_refuses_a_result_that_breaks_the_tool_contract(engine, tmp_path, adapter):
    path = copy_registry(tmp_path, '"strata.tools.check_plan:check_plan"', f'"test_tools:{adapter}"')
    context = registry.Context(engine=engine, viewer=ANA)

    with pytest.raises(registry.ToolContractError):
        registry.call("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA, "as_of": "2026-10-22"},
                      context, tools=config.load_tools(path))


def test_changing_days_before_closing_in_the_thresholds_file_changes_ke_nwwda_541061s_mark(engine, tmp_path):
    """KE-NWWDA-541061-CW-RFQ is still pending in the plan of March 5, 2026 (ticket 132 moved the October 9 plan's
    pending activities on, so this check uses the plan before it)."""
    path = tmp_path / "thresholds.toml"
    text = (ROOT / "config" / "thresholds.toml").read_text()
    [line] = [line for line in text.splitlines() if line.startswith("days_before_closing = ")]
    path.write_text(text.replace(line, "days_before_closing = 5"))  # 9 days are left on October 22

    result = check_plan(engine, thresholds=config.load_thresholds(path), plan_date="2026-03-05", as_of="2026-10-22")

    assert result["thresholds"]["days_before_closing"] == 5
    assert marks(result)["KE-NWWDA-541061-CW-RFQ"] == []
    assert marks(result)["KE-NWWDA-541055-CW-RFB"] == ["moved_on"]
    assert result["counts"]["watch"] == 1


@pytest.mark.parametrize("key, setting, plan_date, reference, marked", [
    # KE-NWWDA-229129-CW-RFB was signed at US$1,245,092.76 against US$300,000.00, about 4.15 times its estimate.
    ("actual_to_estimate_ratio", "5", "2026-10-09", "KE-NWWDA-229129-CW-RFB", []),
    # NWWDA-WSDP-03-2019-2020 is estimated at US$2,000,000.00 and still Under Implementation in the agency's plan of
    # April 21, 2021, whose planned completion passed; below the amount it is still pending 9 days before closing.
    # (Ticket 132 moved on the October 9, 2026 plan's KE-NWWDA-541055-CW-RFB, which this case once used.)
    ("completion_passed_min_estimated_usd", "3_000_000", "2021-04-21", "NWWDA-WSDP-03-2019-2020", ["watch"]),
], ids=["ratio", "amount"])
def test_each_plan_check_threshold_comes_from_the_thresholds_file(engine, tmp_path, key, setting, plan_date, reference,
                                                                  marked):
    """Ticket 09's verification round 2, V3: each of [plan_check]'s three values moves a mark when the file changes,
    so none is held in code (CLAUDE.md rule 9). days_before_closing is the test above."""
    path = tmp_path / "thresholds.toml"
    text = (ROOT / "config" / "thresholds.toml").read_text()
    [line] = [line for line in text.splitlines() if line.startswith(f"{key} = ")]
    path.write_text(text.replace(line, f"{key} = {setting}"))

    before = check_plan(engine, plan_date=plan_date, as_of="2026-10-22")
    after = check_plan(engine, thresholds=config.load_thresholds(path), plan_date=plan_date, as_of="2026-10-22")

    assert marks(before)[reference] != marked
    assert marks(after)[reference] == marked


# ── Abstentions and refused calls ────────────────────────────────────────

def test_an_agency_with_no_plan_gets_an_abstention_that_lists_the_agencies_with_plans(engine):
    result = check_plan(engine, implementing_agency="Wajir Water and Sewerage Company", as_of="2026-10-22")

    assert result["rows"] == [] and result["abstention"]["reason"] == "no_plan_from_agency"
    agencies = {agency["implementing_agency"]: agency for agency in result["abstention"]["agencies"]}
    assert agencies[NWWDA] == {"implementing_agency": NWWDA, "agency_id": "northern-water-works-development-agency",
                               "latest_plan_date": "2026-10-09"}


def test_an_agency_with_no_plan_named_by_its_id_is_named_in_full_when_the_project_record_names_it(engine):
    # The screen's empty state names the agency ("I don't have a Procurement Plan from ... yet."),
    # and the projects API's record for P156634 lists Wajir Water and Sewerage Company.
    result = check_plan(engine, implementing_agency="wajir-water-and-sewerage-company", as_of="2026-10-22")
    unknown = check_plan(engine, implementing_agency="no-such-agency", as_of="2026-10-22")

    assert result["abstention"]["agency_name"] == "Wajir Water and Sewerage Company"
    assert unknown["abstention"]["agency_name"] is None


def test_an_agency_can_be_named_by_its_id_from_an_earlier_result(engine):
    result = check_plan(engine, implementing_agency="northern-water-works-development-agency", as_of="2026-10-22")

    assert (result["plan"]["implementing_agency"], result["plan"]["plan_date"]) == (NWWDA, "2026-10-09")


def test_a_version_the_agency_never_published_gets_an_abstention_that_names_its_latest(engine):
    result = check_plan(engine, plan_date="2026-10-10", as_of="2026-10-22")

    assert result["rows"] == []
    assert (result["abstention"]["reason"], result["abstention"]["latest_plan_date"]) == (
        "version_not_found", "2026-10-09")


@pytest.fixture
def fresh():
    from strata.lakehouse import catalog

    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def test_an_activity_whose_plan_lacks_a_date_or_an_estimate_is_not_fully_checked_and_says_why(fresh, monkeypatch):
    """A made-up plan with two activities no recorded plan has: one pending, estimated at
    US$2,000,000.00, with no planned Contract Completion, and one signed at US$50,000.00 with no
    Estimated Amount. The project closes June 30, 2027."""
    from strata.lakehouse.plans import insert

    insert(fresh, "strata.gold.project", ("project_id", "project_name", "closing_date", "public_from"),
           [("P000001", "A made-up project", dt.date(2027, 6, 30), dt.date(2020, 1, 1))])
    insert(fresh, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "series_order", "is_latest", "pdf_pages",
            "route_b_pages", "text_url", "pdf_url", "public_from"),
           [("made-up", "P000001", "A Made-Up Agency", dt.date(2026, 1, 15), 1, True, 1, 1, "plan.txt", "plan.pdf",
             dt.date(2026, 1, 15))])
    insert(fresh, "strata.silver.plan_rows",
           ("document_id", "project_id", "section", "activity_reference_no", "estimated_amount_usd",
            "actual_amount_usd", "process_status", "pdf_page", "parser", "public_from"),
           [("made-up", "P000001", "WORKS", "XX-MADE-1-CW-RFB", 2000000, 0, "Pending Implementation", 3, "made up",
             dt.date(2026, 1, 15)),
            ("made-up", "P000001", "GOODS", "XX-MADE-2-GO-RFQ", None, 50000, "Signed", 3, "made up",
             dt.date(2026, 1, 15))])
    context = registry.Context(engine=fresh, viewer=ANA)
    arguments = {"project_id": "P000001", "implementing_agency": "A Made-Up Agency"}

    result = registry.call("check_plan", {**arguments, "as_of": "2026-10-22"}, context)

    assert marks(result) == {"XX-MADE-1-CW-RFB": ["data_note"], "XX-MADE-2-GO-RFQ": ["data_note"]}
    assert set(reasons(result, "XX-MADE-1-CW-RFB")) == {"no_planned_date"}
    assert set(reasons(result, "XX-MADE-2-GO-RFQ")) == {"no_estimate"}
    assert (result["counts"]["checked"], result["counts"]["not_fully_checked"]) == (0, 2)
    assert (result["coverage"]["matched"], result["coverage"]["used"]) == (2, 0)
    assert {(item["reason"], item["count"]) for item in result["coverage"]["not_used"]} == {
        ("no_planned_date", 1), ("no_estimate", 1)}

    monkeypatch.setattr(registry, "today", lambda: dt.date(2027, 7, 15))  # a date after today is read as today
    after_closing = registry.call("check_plan", {**arguments, "as_of": "2027-07-15"}, context)

    assert marks(after_closing)["XX-MADE-1-CW-RFB"] == ["watch", "data_note"]
    assert reasons(after_closing, "XX-MADE-1-CW-RFB")["pending_after_closing"]["days_to_close"] == -15


def test_the_latest_version_is_chosen_by_date_when_the_agency_s_name_is_spelled_two_ways(fresh):
    """A made-up agency whose later plan, of February 1, 2026, writes its name in capitals."""
    from strata.lakehouse.plans import insert

    insert(fresh, "strata.gold.project", ("project_id", "project_name", "closing_date", "public_from"),
           [("P000003", "A made-up project", dt.date(2027, 6, 30), dt.date(2020, 1, 1))])
    insert(fresh, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "series_order", "is_latest", "pdf_pages",
            "route_b_pages", "text_url", "pdf_url", "public_from"),
           [("capitals", "P000003", "A MADE-UP AGENCY", dt.date(2026, 2, 1), 1, True, 1, 1, "c.txt", "c.pdf",
             dt.date(2026, 2, 1)),
            ("mixed", "P000003", "A Made-Up Agency", dt.date(2026, 1, 15), 1, True, 1, 1, "m.txt", "m.pdf",
             dt.date(2026, 1, 15))])

    result = registry.call("check_plan", {"project_id": "P000003", "implementing_agency": "a-made-up-agency",
                                          "as_of": "2026-10-22"}, registry.Context(engine=fresh, viewer=ANA))

    assert (result["plan"]["document_id"], result["plan"]["plan_date"]) == ("capitals", "2026-02-01")
    # An agency with no plan lists each agency with a plan once, by its id, as its latest plan spells it (ticket 09's
    # review round 2, R2-P5).
    other = registry.call("check_plan", {"project_id": "P000003", "implementing_agency": "Another Agency",
                                         "as_of": "2026-10-22"}, registry.Context(engine=fresh, viewer=ANA))
    assert other["abstention"]["agencies"] == [{"implementing_agency": "A MADE-UP AGENCY",
                                                "agency_id": "a-made-up-agency", "latest_plan_date": "2026-02-01"}]


def test_a_plan_disclosed_before_an_older_one_is_checked_on_its_own_dates_until_the_older_one_is_public(fresh):
    """A made-up agency's two plans, the older disclosed after the newer (ticket 08's verification,
    F2). The plan of April 21, 2021 was disclosed on December 15, 2021 and first lists both
    activities. The plan of December 1, 2021 was disclosed that day. In it, XX-1-CW-RFB, estimated at
    US$2,000,000.00, is still pending and plans Contract Completion for November 1, 2021, and
    XX-2-GO-RFQ was signed on November 20, 2021 at US$500,000.00 against US$100,000.00. The project
    closes June 30, 2023. As of December 10, 2021, only the December 1 plan is public."""
    from strata.lakehouse import plans
    from strata.lakehouse.plans import insert

    agency, project, older, newer = "A Made-Up Agency", "P000002", dt.date(2021, 4, 21), dt.date(2021, 12, 1)
    older_public = dt.date(2021, 12, 15)
    insert(fresh, "strata.gold.project", ("project_id", "project_name", "closing_date", "public_from"),
           [(project, "A made-up project", dt.date(2023, 6, 30), dt.date(2020, 1, 1))])
    insert(fresh, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "series_order", "is_latest", "pdf_pages",
            "route_b_pages", "text_url", "pdf_url", "public_from"),
           [("older", project, agency, older, 1, False, 1, 1, "older.txt", "older.pdf", older_public),
            ("newer", project, agency, newer, 2, True, 1, 1, "newer.txt", "newer.pdf", newer)])
    insert(fresh, "strata.silver.plan_rows",
           ("document_id", "project_id", "section", "activity_reference_no", "estimated_amount_usd",
            "actual_amount_usd", "process_status", "pdf_page", "parser", "public_from"),
           [(document, project, section, reference, estimated, actual, status, 1, "made up", public_from)
            for document, public_from, statuses in (("older", older_public, ("Pending Implementation",) * 2),
                                                    ("newer", newer, ("Pending Implementation", "Signed")))
            for (section, reference, estimated, actual), status in zip(
                (("WORKS", "XX-1-CW-RFB", 2000000, None), ("GOODS", "XX-2-GO-RFQ", 100000, 500000)), statuses)])
    insert(fresh, "strata.silver.plan_listings",
           ("document_id", "project_id", "activity_reference_no", "is_first_listing", "first_listing_confirmed",
            "public_from"),
           [(document, project, reference, document == "older", True, public_from)
            for document, public_from in (("older", older_public), ("newer", newer))
            for reference in ("XX-1-CW-RFB", "XX-2-GO-RFQ")])
    insert(fresh, "strata.silver.plan_steps",
           ("document_id", "project_id", "activity_reference_no", "step", "step_order", "planned_on", "actual_on",
            "public_from"),
           [("older", project, "XX-1-CW-RFB", "Contract Completion", 2, dt.date(2021, 9, 30), None, older_public),
            ("older", project, "XX-2-GO-RFQ", "Signed Contract", 1, dt.date(2021, 8, 1), None, older_public),
            ("newer", project, "XX-1-CW-RFB", "Contract Completion", 2, dt.date(2021, 11, 1), None, newer),
            ("newer", project, "XX-2-GO-RFQ", "Signed Contract", 1, dt.date(2021, 8, 1), dt.date(2021, 11, 20),
             newer)])
    fresh.run(plans._sql("plan_step_delays.sql"), {"project_id": project})
    context = registry.Context(engine=fresh, viewer=ANA)

    result = registry.call("check_plan", {"project_id": project, "implementing_agency": agency,
                                          "as_of": "2021-12-10"}, context)

    assert result["plan"]["plan_date"] == "2021-12-01"
    pending = next(row for row in result["rows"] if row["activity_reference_no"] == "XX-1-CW-RFB")
    assert (pending["planned_completion_on"], pending["planned_completion_plan_date"]) == ("2021-11-01", "2021-12-01")
    assert marks(result)["XX-1-CW-RFB"] == ["needs_a_look"]
    assert "no_planned_date" not in reasons(result, "XX-1-CW-RFB")
    signed = reasons(result, "XX-2-GO-RFQ")["signed_over_estimate"]
    assert (signed["signed_on"], signed["days_late"]) == ("2021-11-20", None)  # the delay rests on the older plan
    assert all(row["public_from"] <= "2021-12-10" for row in result["rows"])

    once_both_are_public = registry.call("check_plan", {"project_id": project, "implementing_agency": agency,
                                                        "as_of": "2021-12-20"}, context)

    assert reasons(once_both_are_public, "XX-1-CW-RFB")["completion_passed_no_contract"][
        "planned_completion_on"] == "2021-09-30"  # the first published planned date
    assert reasons(once_both_are_public, "XX-2-GO-RFQ")["signed_late_over_estimate"]["days_late"] == 111
    # Each delay cites the row that gave its first published planned date, the older plan's, beside the row checked
    # (ticket 09's verification round 2, V2), so a later plan that moves the date never leaves a true delay uncited.
    # As of December 10 the planned completion was the newer plan's own, so only its row is cited.
    assert reasons(once_both_are_public, "XX-1-CW-RFB")["completion_passed_no_contract"]["evidence_ids"] == [
        "strata.silver.plan_rows:newer/XX-1-CW-RFB", "strata.silver.plan_rows:older/XX-1-CW-RFB",
        f"strata.gold.project:{project}"]
    assert reasons(once_both_are_public, "XX-2-GO-RFQ")["signed_late_over_estimate"]["evidence_ids"] == [
        "strata.silver.plan_rows:newer/XX-2-GO-RFQ", "strata.silver.plan_rows:older/XX-2-GO-RFQ"]
    assert reasons(result, "XX-1-CW-RFB")["completion_passed_no_contract"]["evidence_ids"] == [
        "strata.silver.plan_rows:newer/XX-1-CW-RFB", f"strata.gold.project:{project}"]


def test_a_named_version_public_on_the_as_of_date_is_chosen_over_a_later_one_of_the_same_date(fresh):
    """Two made-up plans of one agency, both dated January 15, 2026 (ticket 09's review round 2, R2-P1): the first
    disclosed on January 20, the second, a re-issue, on March 1. As of February 1 a call for that plan date checks
    the first, which was public, and does not say the version is not public. From March 1 it checks the re-issue."""
    from strata.lakehouse.plans import insert

    insert(fresh, "strata.gold.project", ("project_id", "project_name", "closing_date", "public_from"),
           [("P000004", "A made-up project", dt.date(2028, 6, 30), dt.date(2020, 1, 1))])
    insert(fresh, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "series_order", "is_latest", "pdf_pages",
            "route_b_pages", "text_url", "pdf_url", "public_from"),
           [("first", "P000004", "A Made-Up Agency", dt.date(2026, 1, 15), 1, False, 1, 1, "f.txt", "f.pdf",
             dt.date(2026, 1, 20)),
            ("reissued", "P000004", "A Made-Up Agency", dt.date(2026, 1, 15), 2, True, 1, 1, "r.txt", "r.pdf",
             dt.date(2026, 3, 1))])
    context = registry.Context(engine=fresh, viewer=ANA)
    arguments = {"project_id": "P000004", "implementing_agency": "A Made-Up Agency", "plan_date": "2026-01-15"}

    before_the_reissue = registry.call("check_plan", {**arguments, "as_of": "2026-02-01"}, context)
    after_it = registry.call("check_plan", {**arguments, "as_of": "2026-03-10"}, context)
    before_both = registry.call("check_plan", {**arguments, "as_of": "2026-01-16"}, context)

    assert before_the_reissue["abstention"] == {"reason": "no_activities", "plan_date": "2026-01-15"}
    assert (before_the_reissue["plan"]["document_id"], before_the_reissue["plan"]["is_latest"]) == ("first", True)
    assert (after_it["plan"]["document_id"], after_it["plan"]["is_latest"]) == ("reissued", True)
    assert before_both["abstention"]["reason"] == "version_not_public"


def test_an_as_of_date_after_today_is_read_as_today(engine, monkeypatch):
    """Ticket 09's verification round 2, V1: as of 2030-01-01 the tool counted days that had not passed, a
    days_to_close of -1158. A call's date after today is read as today (ADR 0002); a page's date is the route's to
    keep to its own today (tests/test_app_clock.py)."""
    monkeypatch.setattr(registry, "today", lambda: dt.date(2026, 10, 22))

    result = check_plan(engine, plan_date="2026-03-05", as_of="2030-01-01")

    assert result["as_of"] == "2026-10-22"
    assert reasons(result, "KE-NWWDA-541061-CW-RFQ")["pending_near_closing"]["days_to_close"] == 9
    assert result["project"]["days_to_close"] == 9


@pytest.mark.parametrize("name, arguments, says", [
    ("check_plans", {}, "There is no tool check_plans"),
    ("check_plan", {"project_id": "P156634"}, "needs implementing_agency"),
    ("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA, "as_of": "October 22"}, "a date"),
    ("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA, "agency": NWWDA}, "no parameter agency"),
])
def test_the_registry_refuses_a_call_its_tools_do_not_take(engine, name, arguments, says):
    with pytest.raises(registry.ToolError, match=says):
        registry.call(name, arguments, registry.Context(engine=engine, viewer=ANA))


# ── As of a past date (ADR 0002) ─────────────────────────────────────────

def test_as_of_july_1_2026_ke_nwwda_541055_has_not_passed_its_planned_completion(engine):
    result = check_plan(engine, as_of="2026-07-01")

    # The latest NWWDA plan public on July 1 is the first to list the activity, of March 5, 2026.
    assert result["plan"]["plan_date"] == value("plan-541055-first-listed").isoformat()
    assert "completion_passed_no_contract" not in reasons(result, "KE-NWWDA-541055-CW-RFB")
    assert all(row["public_from"] <= "2026-07-01" for row in result["rows"])


def test_as_of_october_1_2026_the_october_9_plan_is_not_used(engine):
    latest = check_plan(engine, as_of="2026-10-01")
    named = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-01")

    assert latest["plan"]["plan_date"] == value("plan-541055-first-listed").isoformat()
    assert latest["plan"]["is_latest"] is True
    assert named["rows"] == [] and named["plan"] is None
    assert named["abstention"] == {
        "reason": "version_not_public", "plan_date": "2026-10-09", "public_from": "2026-10-09",
        "implementing_agency": NWWDA, "agency_id": "northern-water-works-development-agency",
        "latest_plan_date": value("plan-541055-first-listed").isoformat()}


def test_the_page_as_of_date_applies_to_every_call_and_the_earlier_date_wins(engine):
    context = registry.Context(engine=engine, viewer=ANA, as_of=dt.date(2026, 10, 1))

    result = registry.call("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA,
                                          "as_of": "2026-10-22"}, context)

    assert result["as_of"] == "2026-10-01"
    assert result["plan"]["plan_date"] == value("plan-541055-first-listed").isoformat()


def test_before_the_project_record_was_last_updated_its_closing_date_is_not_used(engine):
    """The projects API record of P156634 was last updated on April 24, 2024 (silver.projects,
    last_updated_on). A closing date read from it was not known to be public before then."""
    result = check_plan(engine, implementing_agency="Ministry of Water and Irrigation", as_of="2020-12-31")

    assert result["project"]["closing_date"] is None
    assert "closing_date" not in result["checks_run"]
    assert not any(reason.get("closing_date") for row in result["rows"] for mark in row["marks"]
                   for reason in mark["reasons"])


def test_every_reason_code_check_plan_may_return_has_a_sentence_in_the_screen_s_copy_file():
    """A code added to the registry without a copy sentence would show a badge with no reason."""
    copy = (Path(__file__).resolve().parents[1] / "web" / "src" / "copy.ts").read_text()
    check_plan = copy[copy.index("\n  checkPlan: {"):]  # the screen's words, not pages.checkPlan's title
    reasons = check_plan[check_plan.index("\n    reason: {"):]
    reasons = reasons[:reasons.index("\n    },")]
    sentences = set(re.findall(r"^ {6}(\w+):", reasons, flags=re.MULTILINE))

    codes = config.load_tools()["check_plan"].result.reasons
    assert codes
    assert set(codes) - sentences == set()


def data_notes_written(sql: str) -> set[str]:
    """The name of each note plan_data_notes.sql writes."""
    return set(re.findall(r"r\.activity_reference_no, '([a-z_]+)'", sql))


def test_every_data_note_the_plan_reader_writes_is_a_reason_check_plan_lists():
    """Ticket 09's review, R2-P2, for the change drill: plan_data_notes.sql is the one definition of each note, and
    check_plan passes each note's name through as a reason code. A note added there without the same name in
    check_plan's reasons in config/tools.toml would make the registry refuse the result, HTTP 500 tool_contract, on
    every plan with that note. This fails the gate first, whether or not a fixture row gets the note."""
    sql = (ROOT / "src" / "strata" / "lakehouse" / "sql" / "plans" / "plan_data_notes.sql").read_text()
    reasons = set(config.load_tools()["check_plan"].result.reasons)

    assert {"method_differs_from_reference", "actual_amount_zero", "method_unknown"} <= data_notes_written(sql)
    assert data_notes_written(sql) <= reasons
    planted = sql + "\nUNION ALL\nSELECT r.document_id, r.project_id, r.activity_reference_no, 'lot_count_differs'"
    assert data_notes_written(planted) - reasons == {"lot_count_differs"}


def test_a_method_name_the_registry_does_not_list_is_a_data_note_on_the_plan_check(fresh):
    """Ticket 49's review round 2, follow-up 1: a Method cell the method-name registry does not list gets the plan
    reader's method_unknown note (ticket 42), and the plan check shows it with the plan's own words, where it once
    answered HTTP 500 tool_contract. A made-up plan of one activity whose Method cell reads "Reverse auction"."""
    from strata.lakehouse.plans import insert

    insert(fresh, "strata.gold.project", ("project_id", "project_name", "closing_date", "public_from"),
           [("P000005", "A made-up project", dt.date(2028, 6, 30), dt.date(2020, 1, 1))])
    insert(fresh, "strata.silver.plan_versions",
           ("document_id", "project_id", "implementing_agency", "plan_date", "series_order", "is_latest", "pdf_pages",
            "route_b_pages", "text_url", "pdf_url", "public_from"),
           [("auction", "P000005", "A Made-Up Agency", dt.date(2026, 1, 15), 1, True, 1, 1, "a.txt", "a.pdf",
             dt.date(2026, 1, 15))])
    insert(fresh, "strata.silver.plan_rows",
           ("document_id", "project_id", "section", "activity_reference_no", "method", "estimated_amount_usd",
            "actual_amount_usd", "process_status", "pdf_page", "parser", "public_from"),
           [("auction", "P000005", "GOODS", "XX-MADE-5-GO-RFQ", "Reverse auction", 50000, 0, "Pending Implementation",
             2, "made up", dt.date(2026, 1, 15))])
    insert(fresh, "strata.silver.plan_data_notes",
           ("document_id", "project_id", "activity_reference_no", "note", "method", "process_status",
            "actual_amount_usd", "public_from"),
           [("auction", "P000005", "XX-MADE-5-GO-RFQ", "method_unknown", "Reverse auction", "Pending Implementation", 0,
             dt.date(2026, 1, 15))])

    result = registry.call("check_plan", {"project_id": "P000005", "implementing_agency": "A Made-Up Agency",
                                          "as_of": "2026-10-22"}, registry.Context(engine=fresh, viewer=ANA))

    note = reasons(result, "XX-MADE-5-GO-RFQ")["method_unknown"]
    assert (note["mark"], note["method"]) == ("data_note", "Reverse auction")
