"""The tool registry and its tools at seam 2, the tool contract.

The registry, config/tools.toml, is the one place a tool is defined (spec, "Ten single places",
item 2): its name, description, parameters, adapter and result shape. Every tool takes an
optional as-of date (ADR 0002), and the agent's tool list is generated from the file.

check_plan is called by name through the registry, on the fixture database. Expected marks and
values come from tests/ground_truth/values.toml, which quotes the October 9, 2026 plan with its
page and gives the mark the blueprint's Check a plan wireframe draws for each row, and from the
ticket. They are never computed the way the tool computes them.
"""

import datetime as dt
import shutil
import tomllib
from pathlib import Path

import pytest
import yaml

from strata import config
from strata.config import ConfigError
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
BENCHMARK = yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())
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
], ids=["no-as-of-date", "no-result-shape", "rows-without-an-evidence-id"])
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
        assert tool["description"] == tools[tool["name"]].description
        assert tool["parameters"]["properties"]["as_of"] == {
            "type": "string", "format": "date", "description": tools[tool["name"]].parameter("as_of").description}
        assert "as_of" not in tool["parameters"]["required"]


def test_every_tool_names_its_benchmark_question_and_reads_only_registered_sources():
    questions = {question["id"]: question for question in BENCHMARK["questions"]}
    sources = config.load_sources()

    for tool in config.load_tools().values():
        assert tool.benchmark in questions, f"{tool.name}'s question {tool.benchmark} is not in evals/benchmark.yaml"
        assert questions[tool.benchmark]["tool"] == tool.name
        assert set(tool.sources) <= set(sources), f"{tool.name} reads a source the source registry lacks"


def test_each_tool_answers_its_benchmark_question_on_the_fixture_as_expected(engine):
    for question in BENCHMARK["questions"]:
        if "tool" not in question:
            continue
        result = registry.call(question["tool"], question["arguments"], registry.Context(engine=engine, viewer=ANA))

        answered = {"unmarked": sorted(ref for ref, found in marks(result).items() if not found)}
        for mark in ("needs_a_look", "watch", "data_note"):
            answered[mark] = sorted(ref for ref, found in marks(result).items() if mark in found)
        assert answered == {mark: sorted(refs) for mark, refs in question["expected"].items()}


def test_the_ground_truth_sql_uses_the_thresholds_file_s_plan_check_values():
    """The ground-truth SQL writes each threshold as a parameter, so it must change when the file does."""
    from strata.lakehouse import ground_truth

    case = ground_truth.read(ROOT / "tests" / "ground_truth" / "check_plan_nwwda_2026_10_09.sql")
    plan_check = config.load_thresholds().values["plan_check"]

    assert {name: float(case.params[name]) for name in plan_check} == {
        name: float(number) for name, number in plan_check.items()}


def test_adding_a_tool_is_one_entry_and_the_agents_tool_list_grows_with_it(tmp_path):
    path = copy_registry(tmp_path)
    text = path.read_text()
    start = text.index("[tools.check_plan]")
    path.write_text(text + "\n" + text[start:].replace("tools.check_plan", "tools.check_plan_again"))

    listed = registry.agent_tools(config.load_tools(path))

    assert [tool["name"] for tool in listed] == ["check_plan", "check_plan_again"]


# ── check_plan on the NWWDA plan of October 9, 2026 ──────────────────────

def test_check_plan_marks_each_activity_of_the_october_9_plan_as_the_wireframe_does(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    expected = {row["reference"]: WIREFRAME_MARKS[row["wireframe_mark"]] for row in TRUTH["plan_row"]}
    # The plan lists a ninth activity the wireframe leaves out. The tool checks every activity.
    expected |= {reference: [] for reference in TRUTH["plan"]["also_lists"]}
    assert marks(result) == expected
    assert result["counts"] == {"activities": 9, "checked": 9, "needs_a_look": 1, "watch": 2, "data_note": 3,
                                "unmarked": 3}
    assert result["plan"]["plan_date"] == "2026-10-09"
    assert result["abstention"] is None


def test_ke_nwwda_541055_needs_a_look_because_its_planned_completion_passed_with_no_signed_contract(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    reason = reasons(result, "KE-NWWDA-541055-CW-RFB")["completion_passed_no_contract"]
    assert reason["mark"] == "needs_a_look"
    assert reason["planned_completion_on"] == value("plan-541055-planned-completion").isoformat()
    assert reason["closing_date"] == value("closing-date-p156634").isoformat()
    assert reason["days_to_close"] == 9


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


def test_ke_nwwda_541062_is_worth_watching_still_pending_9_days_before_the_project_closes(engine):
    result = check_plan(engine, plan_date="2026-10-09", as_of="2026-10-22")

    reason = reasons(result, "KE-NWWDA-541062-CW-RFQ")["pending_near_closing"]
    assert reason["mark"] == "watch"
    assert (reason["days_to_close"], reason["closing_date"]) == (9, value("closing-date-p156634").isoformat())


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


@pytest.mark.parametrize("adapter", ["leak_a_later_row", "drop_an_evidence_id"])
def test_the_registry_refuses_a_result_that_breaks_the_tool_contract(engine, tmp_path, adapter):
    path = copy_registry(tmp_path, '"strata.tools.check_plan:check_plan"', f'"test_tools:{adapter}"')
    context = registry.Context(engine=engine, viewer=ANA)

    with pytest.raises(registry.ToolContractError):
        registry.call("check_plan", {"project_id": "P156634", "implementing_agency": NWWDA, "as_of": "2026-10-22"},
                      context, tools=config.load_tools(path))


def test_changing_days_before_closing_in_the_thresholds_file_changes_ke_nwwda_541062s_mark(engine, tmp_path):
    path = tmp_path / "thresholds.toml"
    text = (ROOT / "config" / "thresholds.toml").read_text()
    [line] = [line for line in text.splitlines() if line.startswith("days_before_closing = ")]
    path.write_text(text.replace(line, "days_before_closing = 5"))  # 9 days are left on October 22

    result = check_plan(engine, thresholds=config.load_thresholds(path), plan_date="2026-10-09", as_of="2026-10-22")

    assert result["thresholds"]["days_before_closing"] == 5
    assert marks(result)["KE-NWWDA-541062-CW-RFQ"] == []
    assert marks(result)["KE-NWWDA-541055-CW-RFB"] == ["needs_a_look"]
    assert result["counts"]["watch"] == 1


# ── Abstentions and refused calls ────────────────────────────────────────

def test_an_agency_with_no_plan_gets_an_abstention_that_lists_the_agencies_with_plans(engine):
    result = check_plan(engine, implementing_agency="Wajir Water and Sewerage Company", as_of="2026-10-22")

    assert result["rows"] == [] and result["abstention"]["reason"] == "no_plan_from_agency"
    agencies = {agency["implementing_agency"]: agency for agency in result["abstention"]["agencies"]}
    assert agencies[NWWDA] == {"implementing_agency": NWWDA, "agency_id": "northern-water-works-development-agency",
                               "latest_plan_date": "2026-10-09"}


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


def test_an_activity_whose_plan_lacks_a_date_or_an_estimate_is_not_fully_checked_and_says_why(fresh):
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
    assert result["counts"]["checked"] == 0
    assert (result["coverage"]["matched"], result["coverage"]["used"]) == (2, 0)
    assert {(item["reason"], item["count"]) for item in result["coverage"]["not_used"]} == {
        ("no_planned_date", 1), ("no_estimate", 1)}

    after_closing = registry.call("check_plan", {**arguments, "as_of": "2027-07-15"}, context)

    assert marks(after_closing)["XX-MADE-1-CW-RFB"] == ["watch", "data_note"]
    assert reasons(after_closing, "XX-MADE-1-CW-RFB")["pending_after_closing"]["days_to_close"] == -15


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
