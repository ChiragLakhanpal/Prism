"""Data readiness at seams 1 and 2: the measures the fixture's runs write, and data_readiness_for, the
tool the Data readiness page and the agent call (ticket 16; the 16 design brief).

Expected values come from the measures themselves, read with a direct query on strata.ops, from
tests/ground_truth/values.toml, or from hand-made catalogs whose rows each test writes, never from
the way the tool computes them.
"""

import datetime as dt
import json
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "tests" / "fixtures" / "api"
# The day the fixture's sources were recorded, which the data-freshness stamp shows.
RECORDED_ON = dt.date.fromisoformat(json.loads((RECORDED / "freshness.json").read_text())["data_through"])


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def query(engine, sql, **params):
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


# ── Seam 1: the measures the fixture's runs write ─────────────────────────

def test_the_fixture_takes_every_measure_on_the_day_its_sources_were_recorded(engine):
    """So a page or a tool call pinned to that day reads the same measures whatever day the gate runs."""
    days = query(engine, "SELECT DISTINCT CAST(measured_at AS DATE) AS day, public_from FROM strata.ops.data_readiness")

    assert days == [{"day": RECORDED_ON, "public_from": RECORDED_ON}]


# ── Seam 2: data_readiness_for on the fixture ─────────────────────────────

import tomllib  # noqa: E402

from strata import config  # noqa: E402
from strata.dbx import Viewer  # noqa: E402
from strata.tools import registry  # noqa: E402

ANA = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
KENYA = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["counts"]["kenya"]
COLUMNS = ("coverage", "linked", "read_well", "fresh")


def readiness(engine, context=None, **arguments):
    """data_readiness_for, called by name through the registry as Ana, on the day the fixture was recorded."""
    return registry.call("data_readiness_for", {"as_of": RECORDED_ON.isoformat(), **arguments},
                         context or registry.Context(engine=engine, viewer=ANA))


def latest(engine, source, measure):
    """The page's reading rule, as a direct query: for each subject the newest measured_at; the whole
    source's row (subject all) when there is one, else every subject's row."""
    rows = query(engine, """
        SELECT subject, count, denominator, as_of FROM strata.ops.data_readiness AS d
        WHERE source = :source AND measure = :measure
          AND measured_at = (SELECT max(measured_at) FROM strata.ops.data_readiness AS n
                             WHERE n.source = d.source AND n.subject = d.subject AND n.measure = d.measure)
        ORDER BY subject""", source=source, measure=measure)
    whole = [row for row in rows if row["subject"] == "all"]
    return whole or rows


def measured_rows(result):
    return [row for row in result["sources"] if row["type"] == "measured"]


def test_every_number_in_the_sources_table_is_the_latest_measure_behind_its_cell(engine):
    result = readiness(engine)

    for row in measured_rows(result):
        for column in COLUMNS:
            cell = row["cells"][column]
            if cell.get("row") is None:
                continue
            shown = result["rows"][cell["row"]]
            stored = latest(engine, row["source_key"], cell["measure"])
            assert stored, (row["id"], column)
            if column == "fresh":
                days = [entry["as_of"] for entry in stored]
                assert dt.date.fromisoformat(shown["as_of"]) in days, (row["id"], column)
            else:
                assert (shown["count"], shown["denominator"]) == (
                    sum(entry["count"] for entry in stored), sum(entry["denominator"] for entry in stored)), (row["id"], column)


def test_the_awards_row_shows_kenya_s_award_rows_and_its_step_reference_link_rate(engine):
    """values.toml counts Kenya's rows from the recorded award files, apart from Strata's code."""
    result = readiness(engine)
    [awards] = [row for row in result["sources"] if row["id"] == "awards"]

    coverage, linked = (result["rows"][awards["cells"][column]["row"]] for column in ("coverage", "linked"))
    assert coverage["count"] == KENYA["award_rows"]
    assert (linked["count"], linked["denominator"], linked["share_percent"]) == (
        KENYA["with_step_reference"], KENYA["contracts"], 88)  # 528 of 603 is 87.6 percent


def test_the_rows_follow_the_registry_with_the_fiscal_2017_to_2019_awards_as_a_gap_under_the_awards(engine):
    result = readiness(engine)

    order = [(row["type"], row["id"]) for row in result["sources"]]
    registry_rows = [row.id for source in config.load_sources().values() for row in source.readiness]
    assert [entry for entry in order if entry[0] == "measured"] == [("measured", row) for row in registry_rows]
    assert order[:2] == [("measured", "awards"), ("gap", "fy2017_2019")]
    gap = result["sources"][1]
    assert (gap["first_fiscal_year"], gap["last_fiscal_year"]) == (2017, 2019)
    assert gap["note"].startswith("No World Bank dataset publishes contract awards for these years.")


def test_only_cells_that_fall_short_get_a_status_and_each_is_partial(engine):
    """Expected from the fixture's measures and the thresholds file: linked and read-well shares under
    90 percent, and the limits two sources declare. Every source was fetched on the day it was
    measured, so none is late."""
    result = readiness(engine)

    statuses = {(row["id"], column): row["cells"][column]["status"]
                for row in measured_rows(result) for column in COLUMNS if row["cells"][column].get("status")}
    assert statuses == {
        ("awards", "linked"): "partial",  # 528 of 603
        ("awards_fy2001_2016", "coverage"): "partial",  # prior-review contracts only
        ("awards_fy2001_2016", "linked"): "partial",  # 7 of 62 have their project record
        ("ibrd_loans", "linked"): "partial",  # 0 of 1
        ("ibrd_loan_history", "linked"): "partial",  # 0 of 1
        ("cpia", "coverage"): "partial",  # IDA countries only
    }
    # Ticket 18: the reports' Read well is the pages read well across both routes, over 90 percent. The
    # body pages whose paragraph numbers I could not find are one of the row's checks, a gap below.
    [cpia] = [row for row in result["sources"] if row["id"] == "cpia"]
    assert cpia["cells"]["coverage"]["note"] == "IDA countries only"


def test_a_published_table_needs_no_reading_and_a_row_without_a_freshness_measure_says_so(engine):
    result = readiness(engine)
    rows = {row["id"]: row for row in measured_rows(result)}

    assert rows["awards"]["cells"]["read_well"] == {"published_as_table": True}
    assert rows["plans"]["cells"]["fresh"]["row"] is None
    assert rows["reports"]["cells"]["fresh"]["schedule"] == "as published"


def test_each_kind_of_question_is_partial_because_of_a_gap_in_the_rows_it_draws_on(engine):
    """The plan check reads plans whose confirmed first listing was read for none of the activities of
    the latest versions: the demo plan project's 46 (ticket 08's verifier) and the 212 of the stress
    shelf's plan (values.toml, stress_shelf.long_plan); document search reads reports in which some body
    pages show no paragraph numbers."""
    long_plan = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["stress_shelf"]["long_plan"]
    latest = 46 + long_plan["activity_references"]
    result = readiness(engine)

    kinds = {kind["kind"]: kind for kind in result["kinds"]}
    assert {name: kind["status"] for name, kind in kinds.items()} == {"plan_check": "partial", "document_search": "partial"}
    plan_check = kinds["plan_check"]
    assert result["rows"][plan_check["ready_for"]]["count"] == latest
    held = registry_text(plan_check["holds_back"][0])
    # The measure counts an activity once in each latest version that lists it (ticket 08's verifier, F3).
    # Design r3 N2: when every entry falls short, the sentence says so rather than compare 258 with 258.
    assert held == (f"None of the {latest} activity entries in the latest plan versions has a first listing I "
                    "could confirm.")
    # Design r4 P3: in that form the whole is also what falls short, so it opens its measure as the
    # missing records and says what they lack.
    [whole] = [segment for segment in plan_check["holds_back"][0] if "number" in segment]
    assert (whole["number"], whole["role"], whole["lack"]) == (latest, "missing", "a first listing I could confirm")


def registry_text(segments):
    from strata.tools.data_readiness_for import text_of

    return text_of(segments)


def test_the_headline_counts_the_kinds_by_status_and_names_the_two_gaps_that_reach_the_most_projects(engine):
    """Three projects' reports have body pages with no paragraph numbers (P130164's, P156634's and the
    French report's P127203), two projects have a contract with no STEP reference, and two have fiscal
    2017 to 2019 contracts in local currency. Ties go in registry order."""
    result = readiness(engine)
    numbering = latest(engine, "documents", "document_pages_paragraph_numbering_found")
    found, pages = sum(row["count"] for row in numbering), sum(row["denominator"] for row in numbering)

    # Design r3 N1: one status for every kind reads as one clause, not "Of the two ..., two in part".
    assert result["headline"]["text"] == (
        f"I can answer each of the two kinds of question below in part. The biggest gaps are the {pages - found} "
        f"of {pages} body pages that lack paragraph numbers I could find and the 75 of 603 contracts that lack a "
        "reference from Systematic Tracking of Exchanges in Procurement (STEP).")
    numbers = [segment["number"] for segment in result["headline"]["segments"] if "number" in segment][:1]
    assert numbers == [len(result["kinds"])]


def test_the_headline_s_first_clause_counts_each_status_only_when_the_kinds_differ():
    """Design r3 N1. A catalog where every kind is a Gap needs all 13 sources measured, so the sentence
    is checked on its own here."""
    from strata.tools.data_readiness_for import _kinds_sentence

    assert registry_text(_kinds_sentence([{"status": "gap"}, {"status": "gap"}])) == (
        "I can't answer any of the two kinds of question below yet.")
    assert registry_text(_kinds_sentence([{"status": "ready"}, {"status": "partial"}, {"status": "gap"}])) == (
        "Of the three kinds of question below, I can answer one in full, one in part and one not at all.")


def test_the_fixes_are_ranked_by_the_projects_each_would_add_evidence_to(engine):
    result = readiness(engine)

    ranked = [(fix["rank"], fix["gap"], fix["projects"]) for fix in result["fixes"]]
    # Ticket 18: the reports of three projects now fall short of paragraph numbers, and the plans of two
    # (the demo plan's project and the stress shelf's P161305) have unconfirmed first listings.
    assert ranked == [(1, "reports/document_pages_paragraph_numbering_found", 3), (2, "awards/linked", 2),
                      (3, "fy2017_2019", 2), (4, "plans/latest_activities_with_confirmed_first_listing_read", 2)]
    assert registry_text(result["fixes"][2]["sentence"]).startswith(
        "Convert the seven contracts in award notices for fiscal 2017 to 2019 from local currency")
    # The measure counts activity entries: one activity sits in two agencies' latest plans (ticket 08, F3).
    assert registry_text(result["fixes"][3]["sentence"]) == (
        "Read the older plan versions named in each project's document list, so I can confirm the first listing "
        "of each of the 258 activity entries.")


def test_every_number_with_a_row_says_what_it_counts_and_a_fix_s_projects_open_only_their_own_measure(engine):
    """Design review B1: a tooltip never reads "2 . Measured", and a project count that no measure
    counted opens no other measure's window."""
    result = readiness(engine)
    sentences = [result["headline"]["segments"], *(fix["sentence"] for fix in result["fixes"]),
                 *(sentence for kind in result["kinds"] for sentence in kind["holds_back"])]

    numbers = [segment for sentence in sentences for segment in sentence if "number" in segment]
    assert numbers and all(segment["noun"] for segment in numbers if segment["row"] is not None)
    for fix in result["fixes"]:
        if fix["projects_from"] == "subjects":
            assert fix["projects_row"] is None
        else:
            assert result["rows"][fix["projects_row"]]["count"] == fix["projects"]
    [awards_fix] = [fix for fix in result["fixes"] if fix["gap"] == "awards/linked"]
    [missing] = [segment for segment in awards_fix["sentence"] if segment.get("role") == "missing"]
    assert (missing["number"], missing["noun"]) == (KENYA["contracts"] - KENYA["with_step_reference"], "contracts")


def test_a_fix_s_numbers_name_the_table_they_were_counted_in(engine):
    """Design r3 N4: a fix's window names its table, as every other measure window does. Both awards
    fixes count contracts and their projects in gold."""
    result = readiness(engine)
    fixes = {fix["gap"]: fix for fix in result["fixes"]}

    for gap in ("awards/linked", "fy2017_2019"):
        fix = fixes[gap]
        assert result["rows"][fix["row"]]["source"]["counted_in"] == "strata.gold.contract", gap
        assert result["rows"][fix["projects_row"]]["source"]["counted_in"] == "strata.gold.contract", gap


def test_every_row_behind_a_number_names_the_table_it_was_counted_in_on_every_view(engine):
    """Review r7 B1: every number's window names the table it was counted in. The document search's
    Ready for row named none, because the tool used its measure with no table. The views are the full
    page, each kind's own view and each source alone, so a row a filtered view adds first is checked."""
    views = [{}, *({"from_tool": name} for name, tool in config.load_tools().items() if tool.readiness),
             *({"sources": key} for key in config.load_sources())]

    for arguments in views:
        result = readiness(engine, **arguments)
        assert [(row["source_key"], row["measure"]) for row in result["rows"]
                if not row["source"]["counted_in"]] == [], arguments
    result = readiness(engine)
    [search] = [kind for kind in result["kinds"] if kind["kind"] == "document_search"]
    assert result["rows"][search["ready_for"]]["source"]["counted_in"] == "strata.gold.passage"


def test_each_measure_in_a_column_is_written_with_that_column_as_its_kind(engine):
    """Review r7 P1: a number inside a sentence opens the window of its measure's kind, so every
    measure the registry puts in a column, and each coverage column's years, is written with that
    column as its kind. The plans' Activity Reference No. link was written as read_well."""
    wrong = []
    for key, source in config.load_sources().items():
        for row in source.readiness:
            for column in COLUMNS:
                given = getattr(row, column)
                for measure in (given.measure, given.years) if given else ():
                    if measure is None:
                        continue
                    kinds = [found["kind"] for found in query(
                        engine, "SELECT DISTINCT kind FROM strata.ops.data_readiness "
                                "WHERE source = :source AND measure = :measure", source=key, measure=measure)]
                    if kinds != [column]:
                        wrong.append((row.id, column, measure, kinds))
    assert wrong == []


def test_a_shortfall_says_what_its_records_lack_so_its_tooltip_can_name_them(engine):
    """Design r3, low polish: the headline's 75 says these are the contracts that lack a reference."""
    result = readiness(engine)

    [missing] = [segment for segment in result["headline"]["segments"] if segment.get("role") == "missing"
                 and "STEP" in (segment.get("lack") or "")]
    assert (missing["number"], missing["lack"]) == (
        KENYA["contracts"] - KENYA["with_step_reference"],
        "a reference from Systematic Tracking of Exchanges in Procurement (STEP)")


def test_the_plan_pages_each_reading_route_read_well_are_tool_rows_with_their_shares(engine):
    """Review B3: the dashboard's chart of pages read well by route reads these rows, so each share
    has its evidence row and one definition. The plan reader measures each project's routes."""
    result = readiness(engine)

    routes = {route["measure"]: result["rows"][route["row"]] for route in result["routes"]}
    # Ticket 18: the reports' routes too, the published text and the layout parser.
    assert list(routes) == ["pages_read_route_a", "pages_read_route_b", "document_pages_read_route_a",
                            "document_pages_read_route_b"]
    for measure, row in routes.items():
        stored = latest(engine, "documents", measure)
        assert (row["count"], row["denominator"]) == (
            sum(entry["count"] for entry in stored), sum(entry["denominator"] for entry in stored)), measure
        assert row["evidence_id"].startswith("strata.ops.data_readiness:documents/")
    assert [route["label"] for route in result["routes"]] == [
        "Published text (Route A)", "Layout parser (Route B)", "Report pages, published text (Route A)",
        "Report pages, layout parser (Route B)"]


def test_opened_from_a_coverage_line_it_shows_only_the_sources_behind_it(engine):
    result = readiness(engine, sources="awards,notices", from_tool="find_comparables")

    assert [row["id"] for row in result["sources"]] == ["awards", "fy2017_2019", "notices"]
    assert result["filter"] == {"sources": ["awards", "notices"], "unknown": 0, "from": "find_comparables",
                                "shown": 2, "total": 14}
    assert result["kinds"] == []  # neither tool in the registry reads awards or notices yet
    assert result["headline"]["text"].startswith("Two sources are behind the past range. The biggest gaps are ")


def test_opened_from_the_plan_check_it_shows_only_the_rows_the_plan_check_draws_on(engine):
    """The documents source has two rows, and the plan check reads only its Procurement Plans
    (config/tools.toml, check_plan's draws_on), so the reports' gaps stay out of this view."""
    result = readiness(engine, sources="documents,projects", from_tool="check_plan")

    assert [row["id"] for row in result["sources"]] == ["projects", "plans"]  # in registry order
    assert (result["filter"]["shown"], result["filter"]["total"]) == (2, 14)
    # Review r4 P3: when every entry falls short, the headline's gap says so rather than "258 of 258".
    assert result["headline"]["text"] == (
        "Two sources are behind the plan check. The biggest gap is the 258 activity entries in the latest plan "
        "versions, none of which has a first listing I could confirm.")
    assert all(gap["row_id"] in ("plans", "projects") for gap in result["gaps"])
    assert [kind["kind"] for kind in result["kinds"]] == ["plan_check"]
    assert "body pages" not in result["headline"]["text"]

    one = readiness(engine, sources="documents", from_tool="check_plan")
    assert [row["id"] for row in one["sources"]] == ["plans"]
    assert one["filter"]["shown"] == 1
    assert one["headline"]["text"].startswith("One source is behind the plan check.")


def test_a_kind_s_count_spells_step_out_only_where_the_headline_above_it_does_not(engine):
    """Design r4 P1: DESIGN.md section 7, rule 10 spells an abbreviation out once per screen. The full
    view's headline names the contracts that lack a STEP reference, spelled out; the plan check's view
    names no STEP gap, so its count is the first STEP there."""
    full = readiness(engine)
    assert "Systematic Tracking of Exchanges in Procurement (STEP)" in full["headline"]["text"]
    assert [kind["spell_out"] for kind in full["kinds"]] == [False, False]

    plan_check = readiness(engine, sources="documents,projects", from_tool="check_plan")
    assert "(STEP)" not in plan_check["headline"]["text"]
    assert [kind["spell_out"] for kind in plan_check["kinds"]] == [True]


def test_a_filtered_view_counts_the_rows_it_shows(engine):
    """The count line, the alert and the headline count the Sources table's rows, never the keys
    in the link: the documents source alone fills three rows (ticket 18 added its notices' text)."""
    result = readiness(engine, sources="documents,projects", from_tool="find_comparables")

    assert [row["id"] for row in result["sources"]] == ["projects", "plans", "reports", "notice_text"]
    assert result["filter"]["shown"] == 4
    assert result["headline"]["text"].startswith("Four sources are behind the past range.")


def test_a_link_never_puts_its_own_words_in_the_headline_and_unknown_keys_are_only_counted(engine):
    result = readiness(engine, sources="awards,<b>made up</b>", from_tool="say anything")

    assert result["filter"]["unknown"] == 1
    assert result["filter"]["from"] == "unknown"
    assert result["headline"]["text"].startswith("One source is behind the coverage line you opened.")
    assert "made up" not in json.dumps(result) and "say anything" not in json.dumps(result)


def test_a_link_that_names_no_known_source_abstains(engine):
    result = readiness(engine, sources="nothing,here")

    assert result["abstention"] == {"reason": "unknown_sources"}
    assert result["rows"] == [] and result["filter"]["unknown"] == 2


def test_a_link_whose_sources_its_tool_never_draws_on_abstains_rather_than_show_no_sources(engine):
    """Review r3 P1: the plan check draws on neither awards row, so a hand-edited link for the awards
    from the plan check shows "I couldn't find the sources this link names", never "0 sources"."""
    result = readiness(engine, sources="awards", from_tool="check_plan")

    assert result["abstention"] == {"reason": "unknown_sources"}
    assert result["headline"] is None and result["sources"] == []


def test_a_date_before_the_first_measure_abstains_and_says_when_the_measures_start(engine):
    result = readiness(engine, as_of="2026-10-22")

    assert result["abstention"] == {"reason": "before_first_measure", "first_measured_on": RECORDED_ON.isoformat()}
    assert result["rows"] == [] and result["headline"] is None


# ── Seam 2: data_readiness_for on catalogs each test writes ───────────────

from strata.config import Thresholds  # noqa: E402
from strata.lakehouse import catalog  # noqa: E402

MEASURE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                   "measured_at", "public_from")
DAY = dt.date(2026, 10, 23)


def at(day: dt.date, hour: int = 9) -> dt.datetime:
    return dt.datetime.combine(day, dt.time(hour), dt.UTC)


@pytest.fixture(scope="module")
def empty_catalog(tmp_path_factory):
    """Every table and no rows, as a first deploy leaves the catalog. Each test copies it."""
    path = tmp_path_factory.mktemp("catalog") / "strata.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def written(empty_catalog, tmp_path):
    """A copy of the empty catalog, and a function that writes measures into it: (source, subject,
    measure, kind, count, denominator, as_of, measured_at, run_id)."""
    import shutil

    path = tmp_path / "strata.duckdb"
    shutil.copy(empty_catalog, path)

    def write(*rows, failures=()):
        with DuckDBEngine.open(path) as engine:
            engine.insert_rows("strata.ops.data_readiness", MEASURE_COLUMNS, [
                (run_id, source, subject, measure, kind, count, denominator, as_of, None, when, when.date())
                for source, subject, measure, kind, count, denominator, as_of, when, run_id in rows])
            if failures:
                engine.insert_rows("strata.ops.parse_failures", (
                    "run_id", "project_id", "document_id", "pdf_page", "page_hash", "parser", "error", "failed_at",
                    "public_from"), [("run-1", project, document, page, "hash", "parser", "unreadable", when, when.date())
                                     for project, document, page, when in failures])
        return path
    return write


def call_on(path, as_of=DAY, thresholds=None, **arguments):
    with DuckDBEngine.open(path, read_only=True) as engine:
        context = registry.Context(engine=engine, viewer=ANA, **({"thresholds": thresholds} if thresholds else {}))
        return registry.call("data_readiness_for", {"as_of": as_of.isoformat(), **arguments}, context)


def awards(linked=(528, 603), fetched=DAY, when=at(DAY), run="run-1"):
    return [("awards", "all", "coverage_rows", "coverage", 632, 632, None, when, run),
            ("awards", "all", "linked_step_reference", "linked", *linked, None, when, run),
            ("awards", "all", "fresh_fetched", "fresh", None, None, fetched, when, run)]


def cell(result, row_id, column):
    [row] = [row for row in result["sources"] if row["id"] == row_id]
    return row["cells"][column]


def test_with_no_measures_yet_the_tool_abstains(written):
    result = call_on(written())

    assert result["abstention"] == {"reason": "no_measures"}
    assert result["sources"] == [] and result["headline"] is None


def test_the_newest_measured_at_picks_the_run_whatever_the_as_of_dates_say(written):
    """The orchestrator's reading rule: coverage and linked rows carry no as_of, so only measured_at
    tells one run from the next; an older run with a later as_of loses."""
    path = written(*awards(linked=(500, 603), fetched=DAY, when=at(DAY, 5), run="run-early"),
                   *awards(linked=(560, 603), fetched=DAY - dt.timedelta(days=1), when=at(DAY, 9), run="run-late"))

    result = call_on(path, sources="awards")

    linked = result["rows"][cell(result, "awards", "linked")["row"]]
    assert (linked["count"], linked["run_ids"]) == (560, ["run-late"])


def test_a_share_at_the_threshold_is_not_partial_and_one_under_it_is(written):
    limits = config.load_thresholds()
    assert limits.value("data_readiness.linked_min_share") == 0.9

    at_threshold = call_on(written(*awards(linked=(90, 100))), sources="awards")
    assert cell(at_threshold, "awards", "linked")["status"] is None


def test_a_share_one_under_the_threshold_is_partial_and_the_threshold_is_one_line_to_change(written):
    path = written(*awards(linked=(89, 100)))
    assert cell(call_on(path, sources="awards"), "awards", "linked")["status"] == "partial"

    values = json.loads(json.dumps(config.load_thresholds().values))
    values["data_readiness"]["linked_min_share"] = 0.85
    lowered = Thresholds(config.load_thresholds().path, values)
    assert cell(call_on(path, sources="awards", thresholds=lowered), "awards", "linked")["status"] is None


def test_a_daily_source_two_days_old_is_one_day_late_and_one_day_old_is_on_time(written):
    """The 16 brief: "daily" means newer than two days."""
    yesterday = DAY - dt.timedelta(days=1)
    path = written(*awards(linked=(600, 603), fetched=DAY - dt.timedelta(days=2), when=at(yesterday)))

    on_time = cell(call_on(path, as_of=yesterday, sources="awards"), "awards", "fresh")
    late = call_on(path, as_of=DAY, sources="awards")

    assert (on_time["status"], on_time["late_days"]) == (None, None)
    assert (cell(late, "awards", "fresh")["status"], cell(late, "awards", "fresh")["late_days"]) == ("partial", 1)
    assert registry_text(late["gaps"][0]["phrase"]) == (
        "the contract awards since fiscal 2020, last fetched October 21, one day behind their daily update")


def test_a_source_with_no_measures_leaves_the_headline_out_and_says_how_many(written):
    result = call_on(written(*awards()))

    assert result["headline"] is None
    assert result["headline_abstention"] == {"reason": "unmeasured", "unmeasured": 13, "sources": 14}
    [notices] = [row for row in result["sources"] if row["id"] == "notices"]
    assert notices["type"] == "unmeasured"


def test_a_measure_whose_latest_row_is_zero_of_zero_shows_without_a_status(written):
    """Ticket 11: contact_details_removed reads 0 of 0 on every run after the first. A 0 of 0 share is
    not a failure."""
    path = written(*awards(linked=(0, 0)))

    linked = cell(call_on(path, sources="awards"), "awards", "linked")
    assert linked["status"] is None


def test_a_shortfall_of_one_agrees_with_its_verb(written):
    """Review r3 P2: the agent reads the gap phrases, so one contract "lacks", never "lack"."""
    result = call_on(written(*awards(linked=(8, 9))), sources="awards")

    assert ("The biggest gaps are the one of nine contracts that lacks a reference from Systematic Tracking of "
            "Exchanges in Procurement (STEP) and ") in registry_text(result["headline"]["segments"])


def test_a_shortfall_of_the_only_record_names_it_in_the_singular(engine):
    """Review r3 P2: the fixture holds one IBRD loan, and it lacks a project record, so the gap is
    "the one loan that lacks", never "the one of one loans that lack"."""
    result = readiness(engine, sources="ibrd_loans")

    assert [registry_text(gap["phrase"]) for gap in result["gaps"]] == [
        "the one loan that lacks a project record I hold"]


def test_the_plan_pages_the_layout_parser_could_not_read_are_listed(written):
    path = written(*awards(), failures=[("P156634", "doc-1", 4, at(DAY))])

    result = call_on(path, sources="documents")

    assert result["parse_failures"] == [
        {"project_id": "P156634", "document_id": "doc-1", "pdf_page": 4, "failed_on": DAY.isoformat()}]
    assert call_on(path, sources="awards")["parse_failures"] is None  # the plans' row is out of view


def test_the_share_rule_agrees_with_the_number_formatter():
    """One rule, two homes until ticket 12: the thresholds file and web/src/lib/format.ts."""
    import re

    formatter = (ROOT / "web" / "src" / "lib" / "format.ts").read_text()
    fewest = int(re.search(r"FEWEST_FOR_A_FREQUENCY = (\d+)", formatter).group(1))
    percentage = int(re.search(r"FEWEST_FOR_A_PERCENTAGE = (\d+)", formatter).group(1))
    limits = config.load_thresholds()
    assert limits.value("data_readiness.fewest_for_a_share") == fewest
    assert limits.value("data_readiness.fewest_for_a_percentage") == percentage


SHARE = ("share_percent", "share_bound", "in_ten", "in_ten_exact")


@pytest.mark.parametrize("linked, expected", [
    ((29, 200), (15, None, None, None)),  # 14.5 rounds half up to 15; JavaScript's Math.round gives 14
    ((528, 603), (88, None, None, None)),
    ((995, 1000), (100, "over", None, None)),  # more than 99 percent, never 100 for a part
    ((3, 1000), (0, "under", None, None)),  # less than 1 percent, never 0 for a part
    ((1000, 1000), (100, None, None, None)),
    ((31, 37), (None, None, 8, False)),  # DESIGN.md section 7, rule 15: about 8 in 10, under 50 rows
    ((10, 20), (None, None, 5, True)),  # exactly 5 in 10
    ((1, 40), (None, "under", 0, False)),  # fewer than 1 in 10
    ((20, 20), (None, None, None, None)),  # all of them: the count says it
    ((6, 12), (None, None, None, None)),  # under 20 rows: the count alone
])
def test_the_tool_gives_each_share_as_the_page_and_the_dashboard_show_it(written, linked, expected):
    """Review B2: the share is worked out once, in the tool, at its rounding, so the browser divides
    nothing and the app and the dashboard cannot disagree."""
    result = call_on(written(*awards(linked=linked)), sources="awards")

    row = result["rows"][cell(result, "awards", "linked")["row"]]
    assert tuple(row[name] for name in SHARE) == expected
