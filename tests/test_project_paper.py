"""The Project Paper summary at seam 3, through the HTTP routes (ticket 36, criterion 6).

"Draft a Project Paper summary" posts {"kind": "project_paper", "project_id": "P156634", "agency_id": ...,
"plan_date": "2026-10-09"} to /api/drafts. The workflow runs check_plan and agency_track_record as the viewer, reads the
PPSD rows the viewer's team checked for the project's packages, the writer (the scripted writer) drafts three parts,
and all six of the verifier's checks run on every sentence before the draft is saved. The story is tests/ppsd_story.py.

Expected values come from independent sources: the plan's counts from check_plan's benchmark question
(evals/benchmark.yaml) and the track record from tests/ground_truth/agency_track_record_nwwda_2026_10_09.sql.
"""

import io
import re
import zipfile
from pathlib import Path

import pytest
import yaml

import ppsd_story as story_of
from strata.lakehouse import ground_truth

ROOT = Path(__file__).resolve().parents[1]
TRACK = ground_truth.read(ROOT / "tests" / "ground_truth" / "agency_track_record_nwwda_2026_10_09.sql")
PLAN_QUESTION = next(question for question in yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
                     if question["id"] == "check-plan-nwwda-2026-10-09")


@pytest.fixture(scope="module")
def database(fixture_db, tmp_path_factory):
    return story_of.library(fixture_db, tmp_path_factory.mktemp("paper-library"))


@pytest.fixture
def story(database, tmp_path):
    return story_of.Story(database, tmp_path)


def with_checked_rows(story) -> str:
    """Ana's suggested PPSD rows for KE-NWWDA-541055-CW-RFB, a package of P156634, marked as checked."""
    story.select()
    _, draft_id = story.suggest()
    story.act(draft_id, "check", "draft")
    return draft_id


def summarized(story, case="project-paper-p156634") -> dict:
    sent, draft_id = story.summarize(case)
    assert draft_id, sent
    return story.get(f"/api/drafts/{draft_id}").json()


def test_the_summary_for_p156634_cites_the_plan_check_s_counts_and_the_track_record_and_passes_the_six_checks(story):
    with_checked_rows(story)
    draft = summarized(story)
    notes = {note["key"]: note for note in draft["notes"]}

    assert [note["key"] for note in draft["notes"]] == ["plan", "record", "ppsd"]
    assert all(note["state"] == "written" for note in draft["notes"])
    assert draft["checks"]["checks_run"] == [1, 2, 3, 4, 5, 6] and draft["removed"] == []
    plan_summary = next(key for key in draft["evidence"] if key.startswith("strata.tools.check_plan:"))
    track_summary = next(key for key in draft["evidence"] if key.startswith("strata.tools.agency_track_record:"))
    counts = draft["evidence"][plan_summary]["row"]["counts"]
    assert counts["activities"] == PLAN_QUESTION["expected"]["activities"][0] == 9
    assert (counts["needs_a_look"], counts["watch"]) == (len(PLAN_QUESTION["expected"]["needs_a_look"]),
                                                         len(PLAN_QUESTION["expected"]["watch"]))
    [header, values] = TRACK.expected
    track = draft["evidence"][track_summary]["row"]["counts"]
    assert {name: str(track[name]) for name in header} == dict(zip(header, values, strict=True))
    assert any(plan_summary in sentence["evidence_ids"] for sentence in notes["plan"]["sentences"])
    assert any(track_summary in sentence["evidence_ids"] for sentence in notes["record"]["sentences"])
    # Every number a sentence states is a value of a record it cites (check 1).
    assert draft["checks"]["numbers"]["matched"] == draft["checks"]["numbers"]["total"] > 0
    stated = " ".join(sentence["text"] for note in draft["notes"] for sentence in note["sentences"])
    assert "0 of 7" in stated and "%" not in stated and " in 10" not in stated
    for word in ("rate the agency", "weak", "capable", "risky"):
        assert word not in stated.lower()


def test_the_ppsd_part_draws_only_on_rows_the_team_checked_and_names_the_draft(story):
    rows_id = with_checked_rows(story)
    draft = summarized(story)
    ppsd = next(note for note in draft["notes"] if note["key"] == "ppsd")

    assert [entry["draft_id"] for entry in ppsd["drafts"]] == [rows_id]
    assert ppsd["drafts"][0]["checked_by"] == "Ana Example"
    assert draft["summary"]["parts"][2] == {"part": "ppsd", "reason": None, "state": "written"}


def test_with_no_checked_ppsd_rows_the_ppsd_part_is_empty_and_says_why(story):
    """A draft still in Draft has not been checked by a person, so it does not count (the 36 brief, 5.7)."""
    story.select()
    story.suggest()
    draft = summarized(story, "project-paper-p156634-no-ppsd")
    ppsd = next(note for note in draft["notes"] if note["key"] == "ppsd")

    assert (ppsd["state"], ppsd["reason"], ppsd["drafts"]) == ("abstained", "no_ppsd_rows", [])


def test_the_panel_counts_the_checked_ppsd_rows_and_the_project_s_agencies_before_the_click(story):
    before = story.get("/api/drafts/project-paper-inputs", project_id="P156634").json()
    rows_id = with_checked_rows(story)
    after = story.get("/api/drafts/project-paper-inputs", project_id="P156634").json()

    assert before["qualifying_ppsd_rows"] == {"count": 0, "draft_ids": []}
    assert after["qualifying_ppsd_rows"] == {"count": 2, "draft_ids": [rows_id]}
    # The fixture records plans from four of P156634's implementing agencies (data/fixture/README.md).
    assert after["agencies_with_plans"] == 4
    assert story.get("/api/drafts/project-paper-inputs", story_of.CY, project_id="P156634").json()["code"] == "not_staff"


def test_the_word_file_has_a_heading_and_paragraph_per_part_and_leaves_an_empty_part_out(story):
    draft = summarized(story, "project-paper-p156634-no-ppsd")
    story.act(draft["draft_id"], "check", "draft")
    assert story.act(draft["draft_id"], "export", "checked").json()["state"] == "exported"
    name, document = story.download(draft["draft_id"], ".docx")
    body = zipfile.ZipFile(io.BytesIO(document)).read("word/document.xml").decode().replace("&apos;", "'")

    assert name == "project-paper-summary-P156634-northern-water-works-development-agency-2026-10-09.docx"
    assert "Procurement summary for the Project Paper" in body
    assert "Water and Sanitation Development Project (P156634). Northern Water Works Development Agency, Procurement Plan of October 9, 2026." in body
    assert "This summary is not a World Bank review, clearance or no-objection." in body
    headings = re.findall(r'<w:pStyle w:val="Heading2"/></w:pPr><w:r><w:t xml:space="preserve">([^<]*)</w:t>', body)
    assert headings == ["The Procurement Plan", "The implementing agency's track record"]


def test_the_existing_draft_lookups_name_the_open_drafts_on_a_package_and_on_a_plan(story):
    rows_id = with_checked_rows(story)
    paper = summarized(story)

    on_package = story.get("/api/drafts/existing", kind="ppsd_rows", package=story_of.PACKAGE).json()
    on_plan = story.get("/api/drafts/existing", kind="project_paper", **story_of.PLAN).json()
    assert on_package["draft"]["draft_id"] == rows_id
    assert on_plan["draft"]["draft_id"] == paper["draft_id"]
