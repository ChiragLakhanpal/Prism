"""The nightly job's refresh_drafts task (seam 1; ticket 43, brief 39 sections 4.1 and 9): it marks each open
draft row that cites a lesson at a version a lead has since changed or retired, with a version notice in
strata.ops.lesson_version_notices. It never changes a draft: a draft's content and its states stay as their
author left them (GLOSSARY.md, "Lesson version").

The lesson versions here are what a lead's decisions write (strata.knowledge.lessons.review); the drafts are
what the draft runtime saves (strata.drafts.store).
"""

import datetime as dt
import json

import pytest

from strata.drafts.store import DraftStore, NewDraft
from strata.lakehouse import catalog, nightly
from strata.lakehouse.engine import DuckDBEngine

LESSON = "lesson-3f2a9c1d0b"
CITED = f"strata.ops.lesson_versions:{LESSON}/v1"
DECIDED = dt.date(2026, 10, 20)


class Unclosed:
    """The test's engine, which the draft store's close leaves open."""

    def __init__(self, engine):
        self.engine = engine

    def __getattr__(self, name):
        return getattr(self.engine, name)

    def close(self):
        pass


@pytest.fixture
def engine():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def version(engine, number, statement, change_kind, state="current", risk_factors='["rebidding"]'):
    engine.run(
        "INSERT INTO strata.ops.lesson_versions (lesson_id, version, statement, risk_factors, stage, kind, edition_key, "
        "project_id, state, change_kind, was, now, reason, item_id, decided_on, decided_by, decided_by_name, "
        "recommended_by, recommended_by_name, recommended_reason, published_on, days_from_publication, public_from) "
        "VALUES (:lesson_id, :version, :statement, :risk_factors, 'evaluation', 'hurt', NULL, 'P130164', :state, "
        ":change_kind, NULL, NULL, 'The lead gave a reason.', :item_id, :decided_on, 'lead@worldbank.example', "
        "'A lead', 'specialist@worldbank.example', 'A specialist', 'It holds.', NULL, NULL, :decided_on)",
        {"lesson_id": LESSON, "version": number, "statement": statement, "risk_factors": risk_factors, "state": state,
         "change_kind": change_kind, "item_id": f"item-{number}", "decided_on": DECIDED + dt.timedelta(days=number)})


def draft(engine, draft_id="draft-1", cited=(CITED,), state=None):
    content = {"subject": {}, "evidence": {}, "checks": None, "removed": [], "disagreements": [], "notes": [
        {"key": "row-1", "state": "written", "sentences": [{"text": "Plan for rebidding.", "evidence_ids": list(cited)}]},
        {"key": "row-2", "state": "written", "sentences": [{"text": "No lesson here.", "evidence_ids": ["x:1"]}]},
    ]}
    store = DraftStore(lambda: Unclosed(engine))
    created = dt.datetime(2026, 10, 21, 14, tzinfo=dt.UTC)
    store.create(NewDraft(draft_id, "review_notes", "team:nwwda", "user-1", "An author", None, "P156634", "40132287",
                          content, created))
    if state:
        store.change(draft_id, "draft", state, "user-1", "An author", created + dt.timedelta(hours=1))


def drafts_as_saved(engine):
    return (engine.run("SELECT * FROM strata.ops.drafts ORDER BY draft_id").rows,
            engine.run("SELECT * FROM strata.ops.draft_states ORDER BY draft_id, step").rows)


def refresh(engine, run_id="night-1"):
    nightly.main(["--task", "refresh_drafts", "--run-id", run_id, "--src", "src"], engine, fetch=lambda s, e: ())
    return [dict(zip(("draft_id", "row_key", "lesson_id", "cited_version", "current_version", "tier",
                      "holds_export"), row))
            for row in engine.run("SELECT draft_id, row_key, lesson_id, cited_version, current_version, tier, "
                                  "holds_export FROM strata.ops.lesson_version_notices "
                                  "ORDER BY draft_id, row_key").rows]


def test_a_draft_row_citing_a_lesson_whose_wording_changed_is_marked_and_the_draft_is_left_as_it_was(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts under US$5 million.", "wording")
    before = drafts_as_saved(engine)

    notices = refresh(engine)

    assert notices == [{"draft_id": "draft-1", "row_key": "row-1", "lesson_id": LESSON, "cited_version": 1,
                        "current_version": 2, "tier": "narrowed", "holds_export": False}]
    assert drafts_as_saved(engine) == before


def test_a_suggested_ppsd_row_whose_lesson_changed_is_marked_on_its_row(engine):
    """Ticket 36's suggested PPSD rows cite a lesson version in each row's mitigation cell, and the draft page shows
    a notice under the row (brief 39, section 2.4), so the notice names the PPSD row, not the cell."""
    cells = {"risk_description": "cost_estimates/risk_description", "mitigation": "cost_estimates/mitigation"}
    content = {"subject": {}, "evidence": {}, "checks": None, "removed": [], "disagreements": [], "notes": [
        {"key": cells["risk_description"], "state": "written",
         "sentences": [{"text": "Cost estimates ran short.", "evidence_ids": ["strata.tools.find_comparables:1"]}]},
        {"key": cells["mitigation"], "state": "written",
         "sentences": [{"text": "Plan for rebidding.", "evidence_ids": [CITED, "31525018/v1/54"]}]},
    ], "ppsd": {"form": "short", "selected": 1, "rows": [
        {"row_key": "cost_estimates", "risk_key": "cost_estimates", "cells": cells,
         "lesson": {"id": LESSON, "evidence_id": CITED, "version": 1, "decided_on": "2026-10-21"}}]}}
    DraftStore(lambda: Unclosed(engine)).create(NewDraft(
        "draft-ppsd", "ppsd_rows", "team:nwwda", "user-1", "An author", None, "P156634", "40132287", content,
        dt.datetime(2026, 10, 21, 14, tzinfo=dt.UTC)))
    version(engine, 1, "Plan for rebidding.", "added")
    version(engine, 2, "Plan for rebidding in remote areas.", "wording")

    assert [(n["draft_id"], n["row_key"], n["tier"]) for n in refresh(engine)] == [
        ("draft-ppsd", "cost_estimates", "narrowed")]


def test_a_lesson_that_only_gained_a_quote_marks_no_draft(engine):
    """Brief 39, 4.1: an added quote is "strengthened", which goes to the digest and never to the draft."""
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts.", "merged")

    assert refresh(engine) == []


def test_the_strongest_change_since_the_cited_version_sets_the_tier(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts.", "merged")
    version(engine, 3, "Plan for rebidding in works contracts.", "tags", risk_factors='["rebidding", "permits"]')
    version(engine, 4, "Plan for rebidding in works contracts.", "merged")

    assert [(n["current_version"], n["tier"]) for n in refresh(engine)] == [(4, "narrowed")]


def test_a_lesson_retired_as_wrong_marks_the_draft_and_holds_its_export(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts.", "retired", state="retired_wrong")

    assert [(n["tier"], n["holds_export"]) for n in refresh(engine)] == [("retired_wrong", True)]


def test_a_lesson_retired_as_out_of_date_marks_the_draft_without_holding_it(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts.", "retired", state="retired_outdated")

    assert [(n["tier"], n["holds_export"]) for n in refresh(engine)] == [("retired_outdated", False)]


def test_a_second_night_marks_nothing_again_until_another_version_comes(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts under US$5 million.", "wording")
    refresh(engine, "night-1")

    assert len(refresh(engine, "night-2")) == 1

    version(engine, 3, "Plan for rebidding in works contracts.", "retired", state="retired_outdated")
    assert [(n["current_version"], n["tier"]) for n in refresh(engine, "night-3")] == [
        (2, "narrowed"), (3, "retired_outdated")]


def test_a_discarded_draft_and_a_draft_citing_the_current_version_are_not_marked(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    version(engine, 2, "Plan for rebidding in works contracts under US$5 million.", "wording")
    draft(engine, "draft-discarded", state="discarded")
    draft(engine, "draft-current", cited=(f"strata.ops.lesson_versions:{LESSON}/v2",))

    assert refresh(engine) == []


def test_the_task_records_the_rows_it_marked(engine):
    version(engine, 1, "Plan for rebidding in works contracts.", "added")
    draft(engine)
    version(engine, 2, "Plan for rebidding in works contracts under US$5 million.", "wording")
    refresh(engine, "night-1")

    rows = engine.run("SELECT task_key, status, rows_changed FROM strata.ops.pipeline_runs WHERE run_id = :run_id",
                      {"run_id": "night-1"}).rows
    assert list(rows) == [("refresh_drafts", "succeeded", 1)]
    assert json.loads(engine.run("SELECT content FROM strata.ops.drafts").rows[0][0])["notes"][0]["key"] == "row-1"
