"""The hindsight test at seam 5 (ticket 34): Prism frozen at a closed project's approval date, its top risks per
package against the risks the completion report later blamed.

The replay harness (src/strata/estimates/harness.py) freezes Prism at each project's approval date, runs the
risk-table builder (ticket 30) for the main packages of the project's first Procurement Plan, and stores what it
showed beside the risks two coders found the ICR blamed. These tests run it two ways:

- On a copy of the fixture database, for the showcase project P130164, with the fixture's three proposed lessons
  decided by two people (tests/lesson_scenario.py). The fixture records none of P130164's Procurement Plans, so a
  hand-made first plan with three works packages stands in for it. ICR paragraphs 54 and 55 are its blamed risks
  (values.toml icr-para-54 and icr-para-55). These tests prove the freeze: nothing public after the approval date
  (values.toml approval-p130164) reaches the frozen risk tables, and the same items do reach them from a later
  cutoff.
- On a small hand-made set of pilot projects in an in-memory database, whose answers are known, for the coding
  tool, the gate set, the report sentence and the release gate. Statistical expectations (the 95 percent interval
  and McNemar's test) were computed once with SciPy and are stored as literals in values.toml's [hindsight].
"""

import datetime as dt
import json
import tomllib
from pathlib import Path

import pytest

import lesson_scenario as scenario
from strata.estimates import harness, hindsight
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
VALUES = {value["id"]: value for value in TRUTH["value"]}
APPROVED = VALUES["approval-p130164"]["value"]
# The day after the re-issued ICR Review (values.toml icr-review-reissue-date): the ICR and both ICR Reviews are
# public by then, and no lesson had been decided yet.
LATER = VALUES["icr-review-reissue-date"]["value"] + dt.timedelta(days=1)
DECIDED = dt.date(2026, 10, 24)  # after the fixture's proposals (October 23, 2026)
RAN_AT = dt.datetime(2026, 10, 26, 6, tzinfo=dt.UTC)
SHOWCASE = "P130164"
PAD = "18381488"  # values.toml pad-disclosed: public on November 6, 2013, a week after approval
ICR_54 = "strata.gold.passage:31525018/v1/54"
ICR_55 = "strata.gold.passage:31525018/v1/55"
ICR_REVIEW_10B = "strata.gold.passage:34056616/v2/10.b"
# A hand-made first plan for P130164: three works packages under Request for Bids and one smaller goods package.
FIRST_PLAN = "900130164"
PACKAGES = [("IN-HANDMADE-1-CW-RFB", "WORKS", "Upgrading of state highway works", "Request for Bids", "30000000.00"),
            ("IN-HANDMADE-2-CW-RFB", "WORKS", "Road widening works", "Request for Bids", "20000000.00"),
            ("IN-HANDMADE-3-CW-RFB", "WORKS", "Bridge and culvert works", "Request for Bids", "10000000.00"),
            ("IN-HANDMADE-4-GO-RFQ", "GOODS", "Office equipment", "Request for Quotations", "50000.00")]


def insert(engine, table, rows):
    columns = tuple(rows[0])
    engine.insert_rows(table, columns, [tuple(row[column] for column in columns) for row in rows])


def first_plan(engine, project_id, document_id, plan_date, packages):
    insert(engine, "strata.silver.plan_versions", [{
        "document_id": document_id, "project_id": project_id, "implementing_agency": "Hand-made agency",
        "plan_date": plan_date, "disclosed_on": plan_date, "series_order": 1, "previous_document_id": None,
        "is_latest": False, "pdf_pages": 1, "route_b_pages": 0, "text_url": f"https://example.org/{document_id}.txt",
        "pdf_url": f"https://example.org/{document_id}.pdf", "public_from": plan_date}])
    insert(engine, "strata.silver.plan_rows", [{
        "document_id": document_id, "project_id": project_id, "section": section, "activity_reference_no": reference,
        "description": description, "method": method, "estimated_amount_usd": amount, "process_status": "Signed",
        "pdf_page": 1, "parser": "hand-made", "public_from": plan_date}
        for reference, section, description, method, amount in packages])


def expose(engine, step_reference, shown_at):
    """A past range the server showed for one of a project's packages in the staff view, written by the exposure log
    as the package's comparables route writes it (ticket 44): the project is read from the package's plan row."""
    from strata.estimates.exposures import ExposureLog, Shown

    past_range = {"q25": 4.0, "q50": 6.1, "q75": 8.3, "q80": 9.0, "days": {"q25": 122, "q50": 186, "q75": 253, "q80": 274}}
    shown = Shown("find_comparables", {"abstention": None, "past_range": past_range}, step_reference, "staff",
                  shown_at.date(), "/api/packages/{step_reference}/comparables", "4021@1984", None)
    assert ExposureLog(engine.cursor, now=lambda: shown_at).record(engine, shown)


@pytest.fixture(scope="module")
def showcase(fixture_db, tmp_path_factory):
    """A copy of the fixture with the rebidding, permits and IEG lessons decided, and P130164's hand-made first plan."""
    database = scenario.copy_of(fixture_db, tmp_path_factory.mktemp("hindsight-showcase"))
    for passage in (scenario.REBIDDING, scenario.PERMITS, scenario.IEG_LESSON):
        scenario.decide(database, passage, DECIDED)
    with DuckDBEngine.open(database) as engine:
        first_plan(engine, SHOWCASE, FIRST_PLAN, dt.date(2017, 2, 8), PACKAGES)
    return database


def replay_showcase(database, cutoff, builder=None):
    """One replay of P130164, frozen at cutoff, with its blamed risks from ICR paragraphs 54 and 55."""
    case = hindsight.Case(SHOWCASE, cutoff, "transport", blamed=("cost_estimates", "permits_before_award"), checklist=())
    scorer = hindsight.HindsightScorer({SHOWCASE: case}, **({"builder": builder} if builder else {}))
    window = harness.Window(cutoff, RAN_AT.date(), "project", SHOWCASE)
    with DuckDBEngine.open(database) as engine:
        run_id = harness.new_run_id(scorer.name, RAN_AT)
        harness.replay(engine, scorer, window, OfflineTracker(), run_id, RAN_AT)
        return harness.segments(harness.run_rows(engine, run_id))[("project", SHOWCASE)]


def test_frozen_at_approval_no_passage_lesson_or_record_public_later_reaches_the_risk_tables(showcase):
    frozen = replay_showcase(showcase, APPROVED)
    packages = json.loads(frozen["package_tables"])

    # The three largest packages of the first plan, by estimated amount, each with its own risk table.
    assert [package["step_reference"] for package in packages] == [reference for reference, *_ in PACKAGES[:3]]
    assert dt.date.fromisoformat(frozen["inputs_through"]) <= APPROVED
    every_source = [source for package in packages for row in package["rows"] for source in row["sources"]]
    assert all(dt.date.fromisoformat(source["public_from"]) <= APPROVED for source in every_source)
    assert not any(PAD in source["evidence_id"] for source in every_source)
    assert (frozen["blamed"], frozen["covered"], frozen["shown"]) == (2, 0, 0)

    later = replay_showcase(showcase, LATER)
    shown_later = json.loads(later["package_tables"])
    sources = {source["evidence_id"] for package in shown_later for row in package["rows"] for source in row["sources"]}

    # The same items do reach the tables from a later cutoff, so the freeze is what kept them out: the ICR, public on
    # November 2, 2019 (values.toml icr-disclosed), and the re-issued ICR Review.
    assert {ICR_54, ICR_55, ICR_REVIEW_10B} <= sources
    assert VALUES["icr-disclosed"]["value"].isoformat() in {
        source["public_from"] for package in shown_later for row in package["rows"] for source in row["sources"]}
    assert json.loads(later["shown_keys"]) == ["cost_estimates", "permits_before_award"]
    assert (later["blamed"], later["covered"], later["shown"]) == (2, 2, 2)


def test_a_row_public_after_the_cutoff_stops_the_replay(showcase):
    """A builder that let a later row through would be caught by the harness's frozen reader."""
    from strata.harness.facts import Facts
    from strata.packages.risks import RiskTable

    def leaking(engine, viewer, *, as_of, criteria, words=None, thresholds=None, decided_by=None):
        facts = Facts()
        facts.record(ICR_54, {"evidence_id": ICR_54, "public_from": VALUES["icr-disclosed"]["value"].isoformat()})
        return RiskTable({"rows": [], "empty_reason": "no_lessons", "verifier": None}, facts, None)

    with pytest.raises(harness.LeakageError):
        replay_showcase(showcase, APPROVED, builder=leaking)


# ── The hand-made set ────────────────────────────────────────────────────
#
# Pilot projects (Kenya, Bangladesh, Vietnam and Pakistan; water and transport; approved in fiscal 2014 to 2018),
# each with an ICR that Prism read, and a first Procurement Plan whose descriptions name the project, so the fake
# builders below know whose package they were asked about. HAND_MADE gives each gate-set project's approval date,
# sector and the risks its ICR blamed.

HAND_MADE = {
    "P900001": ("KE", "water", dt.date(2014, 3, 3), ("cost_estimates", "permits_before_award", "evaluation_delays")),
    "P900002": ("KE", "water", dt.date(2014, 9, 1), ("cost_estimates", "procurement_capacity", "designs_and_specifications")),
    "P900003": ("KE", "transport", dt.date(2015, 2, 2), ("permits_before_award", "market_response", "contract_management")),
    "P900004": ("BD", "water", dt.date(2016, 8, 1), ("cost_estimates", "evaluation_delays", "contractor_performance")),
    "P900005": ("BD", "transport", dt.date(2016, 10, 3), ("procurement_capacity", "designs_and_specifications", "coordination")),
    "P900006": ("VN", "water", dt.date(2017, 3, 1), ("cost_estimates", "permits_before_award", "market_response")),
    "P900007": ("PK", "transport", dt.date(2017, 6, 1), ("contract_management", "evaluation_delays", "permits_before_award")),
    "P900008": ("PK", "water", dt.date(2018, 1, 2), ("cost_estimates", "procurement_capacity", "contractor_performance")),
}
EXAMPLE, EXPOSED, NOT_CODED, NO_PLAN, NOT_READ, OUTSIDE = "P900009", "P900010", "P900011", "P900012", "P900013", "P900014"
ANA = ("ana.coder@worldbank.example", "Ana Coder")
BEN = ("ben.coder@worldbank.example", "Ben Coder")
CARLA = ("carla.coder@worldbank.example", "Carla Coder")
CODED_AT = dt.datetime(2026, 10, 25, 9, tzinfo=dt.UTC)


def project_row(project_id, country, sector, approved):
    fiscal = approved.year + (1 if approved.month >= 7 else 0)
    return {"project_id": project_id, "project_name": f"Hand-made project {project_id}", "country_code": country,
            "region": "Hand-made region", "status": "Closed", "approval_date": approved, "approval_fiscal_year": fiscal,
            "closing_date": approved.replace(year=approved.year + 6), "sector": sector, "sector_name": sector.title(),
            "public_from": approved - dt.timedelta(days=200)}


def document_row(project_id, document_id, document_type, dated, version=1, replaced_on=None):
    return {"document_id": document_id, "project_id": project_id, "document_type": document_type,
            "report_number": f"R{document_id}", "version": version, "document_date": dated, "disclosed_on": dated,
            "language": "en", "title": f"{document_type} for {project_id}", "pdf_pages": 40, "text_paged": True,
            "text_url": f"https://example.org/{document_id}.txt", "pdf_url": f"https://example.org/{document_id}.pdf",
            "replaced_on": replaced_on, "doc_key": f"{project_id}-{document_id}", "parse_parts": 1, "public_from": dated}


def passage_row(project_id, country, sector, document_id, document_type, dated, paragraph, text):
    return {"passage_id": f"{document_id}/v1/{paragraph}", "document_id": document_id, "project_id": project_id,
            "project_name": f"Hand-made project {project_id}", "country_code": country, "country_name": country,
            "sector": sector, "document_type": document_type, "document_date": dated, "report_number": f"R{document_id}",
            "version": 1, "section_path": "III", "paragraph": paragraph, "paragraph_numbered": True, "part": 1,
            "parts": 1, "pdf_page": 12, "last_pdf_page": 12, "pdf_pages": 40, "printed_page": "12", "language": "en",
            "parse_route": "A", "kind": "paragraph", "scanned": False, "table_title": None, "table_row": None,
            "cells": None, "header": f"ICR, {project_id}, ¶{paragraph}, p.12", "text": text, "tokens": 12,
            "pdf_url": f"https://example.org/{document_id}.pdf", "doc_key": f"{project_id}-{document_id}",
            "embedding": [0.0], "embedding_model": "hand-made", "shield": None, "attack_detected": False,
            "replaced_on": None, "public_day": 0, "replaced_day": 0, "public_from": dated}


ICR_TYPE = "Implementation Completion and Results Report"
REVIEW_TYPE = "Implementation Completion Report Review"


def hand_made_records(engine):
    """Every record the hand-made set needs, before anyone codes it."""
    from strata.lakehouse import catalog

    catalog.build(engine)
    projects = {**{project: (country, sector, approved) for project, (country, sector, approved, _) in HAND_MADE.items()},
                EXAMPLE: ("KE", "water", dt.date(2015, 5, 4)), EXPOSED: ("BD", "water", dt.date(2015, 6, 1)),
                NOT_CODED: ("VN", "transport", dt.date(2016, 1, 4)), NO_PLAN: ("PK", "water", dt.date(2016, 2, 1)),
                NOT_READ: ("KE", "transport", dt.date(2016, 3, 1)), OUTSIDE: ("IN", "transport", dt.date(2015, 1, 5))}
    insert(engine, "strata.gold.country", [{"country_code": code, "country_name": code, "region": "Hand-made region",
                                             "public_from": dt.date(2000, 1, 1)} for code in ("KE", "BD", "VN", "PK", "IN")])
    insert(engine, "strata.gold.project", [project_row(project, *row) for project, row in projects.items()])
    documents, passages = [], []
    for number, (project, (country, sector, approved)) in enumerate(projects.items(), 1):
        icr, review = f"91{number:04d}", f"92{number:04d}"
        closed = approved.replace(year=approved.year + 7)
        documents.append(document_row(project, icr, ICR_TYPE, closed))
        if project not in ("P900003", NOT_CODED):  # these two have no ICR Review
            documents.append(document_row(project, review, REVIEW_TYPE, closed + dt.timedelta(days=161)))
        if project != NOT_READ:
            passages.append(passage_row(project, country, sector, icr, ICR_TYPE, closed, "41", "Lessons learned."))
    insert(engine, "strata.silver.documents", documents)
    insert(engine, "strata.gold.passage", passages)
    return engine


@pytest.fixture(scope="module")
def records(tmp_path_factory):
    """The hand-made records in a DuckDB file, built once; each test works on its own copy."""
    path = tmp_path_factory.mktemp("hindsight-hand-made") / "records.duckdb"
    with DuckDBEngine.open(path) as engine:
        hand_made_records(engine)
    return path


def copy(path, tmp_path):
    import shutil

    target = tmp_path / path.name
    shutil.copy(path, target)
    return target


def command(name):
    """One of the hindsight test's commands under ops/hindsight, loaded from its file."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(name, ROOT / "ops" / "hindsight" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def code(database, project, coder, blamed, *, review=False, at=CODED_AT):
    arguments = ["--database", str(database), "--now", at.isoformat(), "review" if review else "code",
                 "--project", project, "--coder", coder[0], "--name", coder[1], "--blamed", ",".join(blamed)]
    return command("code").main(arguments)


def test_the_coding_tool_keeps_two_codings_and_the_reconciled_risks_with_the_icr_review_settling_differences(
        records, tmp_path, monkeypatch, capsys):
    """Agreement, worked by hand over the closed list's nine risk factors on each of the three projects both coders
    read: they both blamed three (one on each project), only Ana blamed two, only Ben blamed one, and neither blamed
    the other 21. Observed agreement is 24/27; chance agreement is (5/27)(4/27) + (22/27)(23/27) = 526/729, so
    Cohen's kappa is (648 - 526)/(729 - 526) = 122/203 = 0.60."""
    from strata.estimates import hindsight_coding

    monkeypatch.setattr("sys.path", list(__import__("sys").path))
    database = copy(records, tmp_path)
    # P900002: both coders blamed the same risk.
    assert code(database, "P900002", ANA, ["procurement_capacity"]) == 0
    assert code(database, "P900002", BEN, ["procurement_capacity"]) == 0
    assert command("code").main(["--database", str(database), "--now", CODED_AT.isoformat(), "reconcile"]) == 0
    with DuckDBEngine.open(database, read_only=True) as engine:
        [pair] = hindsight_coding.agreement(engine)
        # Nine pairs so far, under retrieval.min_pairs: the statistic is withheld.
        assert (pair["coder_a"], pair["coder_b"], pair["projects"], pair["pairs"], pair["kappa"]) == (
            ANA[0], BEN[0], 1, 9, None)

    # P900001: they differ on two risks, and the ICR Review's reading settles both.
    code(database, "P900001", ANA, ["cost_estimates", "permits_before_award"])
    code(database, "P900001", BEN, ["cost_estimates", "market_response"])
    # A third coder is refused, and the project keeps its two codings.
    assert code(database, "P900001", CARLA, ["coordination"]) == 2
    assert "two coders" in capsys.readouterr().out
    code(database, "P900001", ANA, ["permits_before_award"], review=True)
    # P900003 has no ICR Review: where the coders differ, only what both blamed is kept (a parked rule).
    code(database, "P900003", ANA, ["contract_management", "evaluation_delays"])
    code(database, "P900003", BEN, ["contract_management"])
    later = CODED_AT + dt.timedelta(hours=2)
    assert command("code").main(["--database", str(database), "--now", later.isoformat(), "reconcile"]) == 0

    with DuckDBEngine.open(database, read_only=True) as engine:
        codings = hindsight_coding.codings(engine, "P900001")
        reconciled = hindsight_coding.reconciled(engine)
        [pair] = hindsight_coding.agreement(engine)
    assert {(coding["coder"], coding["reading"]): coding["blamed"] for coding in codings} == {
        (ANA[0], "icr"): ["cost_estimates", "permits_before_award"],
        (BEN[0], "icr"): ["cost_estimates", "market_response"],
        (ANA[0], "icr_review"): ["permits_before_award"]}
    assert {project: (row["blamed"], row["rule"]) for project, row in reconciled.items()} == {
        "P900001": (["cost_estimates", "permits_before_award"], "icr_review"),
        "P900002": (["procurement_capacity"], "agreed"),
        "P900003": (["contract_management"], "no_icr_review")}
    assert reconciled["P900001"]["settled"] == {"market_response": False, "permits_before_award": True}
    assert (pair["projects"], pair["pairs"], pair["agree"], pair["kappa"]) == (3, 27, 24, 0.6)


# ── The gate set, coded ──────────────────────────────────────────────────
#
# Every hand-made project but NOT_CODED is coded by Ana and Ben, who agree. The library holds seven lessons, one per
# risk factor, each resting on one ICR paragraph: five from an ICR public on January 15, 2013, before every approval
# date, and two (evaluation_delays and designs_and_specifications) from an ICR public on June 1, 2016. No lesson covers
# contractor_performance or coordination. So, by hand, a lesson covered 19 of the 24 blamed risks at approval:
# P900001 2, P900002 2, P900003 3, P900004 2, P900005 2, P900006 3, P900007 3 and P900008 2.

EARLY = ("cost_estimates", "permits_before_award", "procurement_capacity", "market_response", "contract_management")
LATE = ("evaluation_delays", "designs_and_specifications")
EARLY_ICR, LATE_ICR = dt.date(2013, 1, 15), dt.date(2016, 6, 1)
LESSONS_DECIDED = dt.date(2026, 10, 20)
EXTRA_BLAMED = {EXAMPLE: ("cost_estimates",), EXPOSED: ("cost_estimates",), NO_PLAN: ("cost_estimates",)}


def library(engine):
    """Seven lessons in the library, decided in October 2026, each on one ICR paragraph."""
    insert(engine, "strata.gold.project", [project_row("P800001", "KE", "transport", dt.date(2005, 3, 1)),
                                            project_row("P800002", "BD", "water", dt.date(2008, 3, 3))])
    versions, sources, evidence = [], [], []
    for number, key in enumerate(EARLY + LATE, 1):
        project, published = ("P800001", EARLY_ICR) if key in EARLY else ("P800002", LATE_ICR)
        lesson, proposal, document = f"lesson-{number:010d}", f"8000{number}/v1/{number}#1", f"8000{number}"
        versions.append({
            "lesson_id": lesson, "version": 1, "statement": f"Plan for {key.replace('_', ' ')}",
            "risk_factors": json.dumps([key]), "stage": "procurement_planning", "kind": "did_not_work",
            "edition_key": None, "project_id": project, "state": "current", "change_kind": "added", "was": None,
            "now": None, "reason": "Two people read it.", "item_id": f"item-{number}", "decided_on": LESSONS_DECIDED,
            "decided_by": "lead@worldbank.example", "decided_by_name": "A lead", "recommended_by": "acc@worldbank.example",
            "recommended_by_name": "An accredited specialist", "recommended_reason": "The quote supports it.",
            "published_on": published, "days_from_publication": None, "public_from": LESSONS_DECIDED})
        sources.append({"lesson_id": lesson, "version": 1, "proposal_id": proposal, "item_id": f"item-{number}",
                        "public_from": LESSONS_DECIDED})
        evidence.append({"proposal_id": proposal, "role": "source", "passage_id": f"{document}/v1/{number}",
                         "document_id": document, "version": 1, "project_id": project, "document_type": ICR_TYPE,
                         "report_number": f"ICR{document}", "document_date": published, "paragraph": str(number),
                         "cited_page": 9, "quote": f"The {key.replace('_', ' ')} hurt the works.",
                         "restated_by_ieg": False, "public_from": published})
    insert(engine, "strata.ops.lesson_versions", versions)
    insert(engine, "strata.ops.lesson_sources", sources)
    insert(engine, "strata.silver.lesson_evidence", evidence)


@pytest.fixture(scope="module")
def gate_db(records, tmp_path_factory):
    """The hand-made set coded, planned, exposed where it should be and given its library, built once."""
    from strata.estimates import hindsight_coding

    path = copy(records, tmp_path_factory.mktemp("hindsight-gate"))
    blamed = {**{project: keys for project, (*_, keys) in HAND_MADE.items()}, **EXTRA_BLAMED}
    with DuckDBEngine.open(path) as engine:
        for project, keys in blamed.items():
            for email, name in (ANA, BEN):
                hindsight_coding.code(engine, project, hindsight_coding.Coder(email, name), keys, now=CODED_AT)
        hindsight_coding.reconcile(engine, CODED_AT)
        for project in [*HAND_MADE, EXAMPLE, EXPOSED, NOT_CODED]:
            approved = HAND_MADE[project][2] if project in HAND_MADE else dt.date(2015, 5, 4)
            first_plan(engine, project, f"93{project[1:]}", approved + dt.timedelta(days=120),
                       [(f"XX-{project}-{n}-CW-RFB", "WORKS", f"{project} works package {n}", "Request for Bids",
                         f"{(5 - n) * 1000000}.00") for n in range(1, 5)])
        expose(engine, f"XX-{EXPOSED}-1-CW-RFB", dt.datetime(2026, 10, 22, 12, tzinfo=dt.UTC))
        library(engine)
    return path


# What each builder shows, by project: the champion shows every blamed risk a lesson covered except P900003's
# market_response, 18 of the 24, and one risk that was not blamed (P900001's market_response). The worse challenger
# also misses six the champion caught; the milder one misses two.
CHAMPION = {"P900001": ("cost_estimates", "permits_before_award", "market_response"),
            "P900002": ("cost_estimates", "procurement_capacity"), "P900003": ("permits_before_award", "contract_management"),
            "P900004": ("cost_estimates", "evaluation_delays"), "P900005": ("procurement_capacity", "designs_and_specifications"),
            "P900006": ("cost_estimates", "permits_before_award", "market_response"),
            "P900007": ("contract_management", "evaluation_delays", "permits_before_award"),
            "P900008": ("cost_estimates", "procurement_capacity")}
WORSE = {**CHAMPION, "P900001": ("permits_before_award", "market_response"), "P900002": ("procurement_capacity",),
         "P900004": ("evaluation_delays",), "P900006": ("permits_before_award", "market_response"), "P900008": ()}
MILDER = {**CHAMPION, "P900001": ("cost_estimates", "market_response"), "P900002": ("cost_estimates",)}


def showing(shows):
    """A builder that shows, for a package of project P, the risks shows[P] gives, spread over its packages."""
    from strata.harness.facts import Facts
    from strata.packages.risks import RiskTable

    def build(engine, viewer, *, as_of, criteria, words=None, thresholds=None, decided_by=None):
        project, number = words.split()[0], int(words.split()[-1])
        keys = [key for index, key in enumerate(shows.get(project, ())) if index % 3 == number - 1]
        facts = Facts()
        facts.record(f"fake:{project}:{number}", {"evidence_id": f"fake:{project}:{number}", "public_from": as_of.isoformat()})
        rows = [{"risk_key": key, "lesson": {"evidence_id": f"lesson:{key}"}, "sources": []} for key in keys]
        return RiskTable({"rows": rows, "empty_reason": None if rows else "no_lessons", "verifier": {"removed": []}},
                         facts, None)
    return build


def run_test(database, release, shows, ran_at=RAN_AT, **options):
    with DuckDBEngine.open(database) as engine:
        return hindsight.run(engine, OfflineTracker(), release, ran_at, builder=showing(shows), **options)


@pytest.fixture
def gate_copy(gate_db, tmp_path):
    return copy(gate_db, tmp_path)


def with_example():
    """The lesson lists, with EXAMPLE as a project the lesson extractor's instructions quote."""
    import dataclasses

    from strata.config import load_lesson_lists

    return dataclasses.replace(load_lesson_lists(), example_projects=(EXAMPLE,))


def test_extraction_examples_and_exposed_projects_are_left_out_and_listed(gate_copy):
    done = run_test(gate_copy, "2026.10", CHAMPION, lists=with_example())

    with DuckDBEngine.open(gate_copy, read_only=True) as engine:
        stored = hindsight.stored_release(engine, done.run_id)
        projects = {segment for (kind, segment) in harness.segments(harness.run_rows(engine, done.run_id))
                    if kind == "project"}
    assert projects == set(HAND_MADE)
    assert json.loads(stored["excluded"]) == [{"project_id": EXAMPLE, "reason": "extraction_example"},
                                              {"project_id": EXPOSED, "reason": "exposed"}]
    assert json.loads(stored["waiting"]) == [{"project_id": NOT_CODED, "reason": "not_coded"},
                                             {"project_id": NO_PLAN, "reason": "no_first_plan"},
                                             {"project_id": NOT_READ, "reason": "icr_not_read"}]
    # The pilot projects with an ICR are the 13 hand-made ones in Kenya, Bangladesh, Vietnam and Pakistan; the one in
    # India (OUTSIDE) is outside the pilot, so it is neither replayed nor listed.
    assert (stored["candidates"], stored["projects"], stored["expected_projects"]) == (13, 8, 49)


KNOWN = TRUTH["hindsight"]


@pytest.fixture(scope="module")
def champion(gate_db, tmp_path_factory):
    """The champion builder's run over the hand-made gate set, stored once, with its tracker."""
    path = copy(gate_db, tmp_path_factory.mktemp("hindsight-champion"))
    tracker = OfflineTracker()
    with DuckDBEngine.open(path) as engine:
        done = hindsight.run(engine, tracker, "2026.10", RAN_AT, builder=showing(CHAMPION), lists=with_example())
    return path, done, tracker


def test_hindsight_recall_is_stored_as_coverage_times_shown_when_covered_for_the_dashboard(champion):
    path, done, tracker = champion
    with DuckDBEngine.open(path, read_only=True) as engine:
        stored = hindsight.stored_release(engine)

    assert stored["run_id"] == done.run_id
    assert (stored["blamed"], stored["covered"], stored["shown"], stored["checklist_caught"]) == (
        KNOWN["blamed"], KNOWN["covered"], KNOWN["champion_caught"], KNOWN["checklist_caught"])
    # Coverage, 19 of 24, times shown-when-covered, 18 of 19, is 18 of 24.
    assert (stored["coverage"], stored["shown_when_covered"], stored["hindsight_recall"]) == (0.7917, 0.9474, 0.75)
    assert stored["hindsight_recall"] == round(KNOWN["champion_caught"] / KNOWN["blamed"], 4)
    assert (stored["interval_low"], stored["interval_high"]) == (KNOWN["interval_low"], KNOWN["interval_high"])
    # Each project's replay and the release's totals have their own MLflow run in the tracker.
    assert stored["mlflow_run_id"] in tracker.runs
    assert tracker.runs[stored["mlflow_run_id"]].metrics["hindsight_recall"] == 0.75
    assert len(tracker.runs) == len(HAND_MADE) + 1


def test_the_report_sentence_is_written_from_the_stored_results_with_its_interval_and_the_checklist(champion,
                                                                                                    tmp_path):
    path, _, _ = champion
    with DuckDBEngine.open(path, read_only=True) as engine:
        stored = hindsight.stored_release(engine)

    assert hindsight.report_sentence(stored) == (
        "In the hindsight test of October 26, I caught 18 of 24 blamed risks across eight projects, at five risks per "
        "package. A checklist of the sector's five commonest risks caught 11. The 95 percent interval runs from 55 to "
        "88 percent. I expected 49 pilot projects with a completion report and could use eight.")
    # Below min_blamed_for_share blamed risks the sentence gives no interval (DESIGN.md section 7, rule 15).
    assert hindsight.report_sentence({**stored, "min_blamed_for_share": 25}).endswith(
        "caught 11. I expected 49 pilot projects with a completion report and could use eight.")
    assert hindsight.report_sentence(None) == "The hindsight test hasn't run yet. It runs on every release."


def test_a_challenger_worse_on_the_same_risks_loses_mcnemar_and_is_not_promoted(champion, tmp_path):
    path, first, _ = champion
    database = copy(path, tmp_path)
    tracker = OfflineTracker()
    with DuckDBEngine.open(database) as engine:
        # The first release has no champion to lose to; it beats the checklist (18 against 11), so it is promoted.
        opening = hindsight.decide(engine, first.run_id, tracker)
        assert (opening.promoted, opening.reason, opening.champion_run_id) == (True, "promoted", None)

        worse = hindsight.run(engine, tracker, "2026.11", RAN_AT + dt.timedelta(days=1), builder=showing(WORSE),
                              lists=with_example())
        lost = hindsight.decide(engine, worse.run_id, tracker)
        milder = hindsight.run(engine, tracker, "2026.12", RAN_AT + dt.timedelta(days=2), builder=showing(MILDER),
                               lists=with_example())
        kept = hindsight.decide(engine, milder.run_id, tracker)
        stored = hindsight.stored_decision(engine, worse.run_id)
        now_champion = hindsight.champion_run(engine)

    # The worse challenger still beats the checklist (12 against 11), but loses the paired comparison on the same 24
    # blamed risks, so it is not promoted, and the first run stays the champion it was compared with.
    assert (lost.champion_run_id, lost.pairs, lost.caught, lost.checklist_caught) == (
        first.run_id, KNOWN["blamed"], KNOWN["worse_caught"], KNOWN["checklist_caught"])
    assert (lost.champion_only, lost.challenger_only, lost.p_value) == (
        KNOWN["worse_champion_only"], KNOWN["worse_challenger_only"], KNOWN["worse_mcnemar_p"])
    assert (lost.promoted, lost.reason) == (False, "lost_to_champion")
    assert (stored["promoted"], stored["reason"], stored["mcnemar_p"]) == (0, "lost_to_champion", KNOWN["worse_mcnemar_p"])
    # The milder challenger does not lose (p = 0.5) and beats the checklist, so it becomes the champion.
    assert (kept.champion_run_id, kept.champion_only, kept.p_value, kept.promoted) == (
        first.run_id, KNOWN["milder_champion_only"], KNOWN["milder_mcnemar_p"], True)
    assert now_champion == milder.run_id


# ── The release-gate command ─────────────────────────────────────────────

def release_gate(database, release, monkeypatch, at=RAN_AT):
    monkeypatch.setattr("sys.path", list(__import__("sys").path))  # the command puts its folders on the path
    return command("release_gate").main(["--database", str(database), "--release", release, "--now", at.isoformat()])


def test_on_the_fixture_the_release_gate_reports_the_projects_it_found_and_records_the_run(fixture_db, tmp_path,
                                                                                            monkeypatch, capsys):
    """The fixture's only ICR is P130164's, outside the pilot projects, so the gate set is empty: N is 0 of 49."""
    database = scenario.copy_of(fixture_db, tmp_path)

    assert release_gate(database, "2026.10-fixture", monkeypatch) == 3
    printed = capsys.readouterr().out
    with DuckDBEngine.open(database, read_only=True) as engine:
        stored = hindsight.stored_release(engine)
        decision = hindsight.stored_decision(engine, stored["run_id"])

    assert (stored["projects"], stored["candidates"], stored["expected_projects"]) == (0, 0, 49)
    assert decision["reason"] == "nothing_to_compare"
    assert hindsight.report_sentence(stored) in printed
    assert "None of the 49 I expected" in printed
    assert stored["run_id"] in printed and stored["mlflow_run_id"] in printed


def test_the_release_gate_runs_the_risk_table_builder_over_the_gate_set_and_says_why_it_blocks(gate_db, tmp_path,
                                                                                                monkeypatch, capsys):
    """The real builder finds no comparable package in the hand-made set, so it shows no risk, and the gate blocks
    the release: it caught fewer blamed risks than the checklist."""
    database = copy(gate_db, tmp_path)

    assert release_gate(database, "2026.10", monkeypatch) == 1
    printed = capsys.readouterr().out
    with DuckDBEngine.open(database, read_only=True) as engine:
        stored = hindsight.stored_release(engine)
        decision = hindsight.stored_decision(engine, stored["run_id"])
        projects = {segment: record for (kind, segment), record in
                    harness.segments(harness.run_rows(engine, stored["run_id"])).items() if kind == "project"}

    # P900009 is an extraction example only in the other tests' lesson lists, so the command replays it too.
    assert (stored["projects"], stored["expected_projects"], stored["shown"]) == (9, 49, 0)
    assert decision["reason"] == "did_not_beat_checklist"
    assert "could use nine" in printed and stored["run_id"] in printed
    assert all(record["mlflow_run_id"] in printed for record in projects.values())
    assert json.loads(projects["P900001"]["package_tables"])[0]["empty_reason"] == "no_comparables"
    assert "P900010 (exposed to Prism)" in printed and "P900011 (not coded yet)" in printed


def test_both_commands_stop_with_one_sentence_when_there_is_no_env_file(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("sys.path", list(__import__("sys").path))
    missing = str(tmp_path / "missing.env")

    assert command("release_gate").main(["--env-file", missing, "--release", "2026.11"]) == 2
    assert command("code").main(["--env-file", missing, "status"]) == 2
    assert capsys.readouterr().out.count("There is no env file") == 2
