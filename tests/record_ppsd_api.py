"""Writes the recorded answers of suggested PPSD rows and the Project Paper summary in tests/fixtures/api from the
server itself (ticket 36).

The screen tests and the design gallery serve these files, and tests/test_ppsd_rows.py checks that the server still
answers with the real ones, so the draft screens and the server cannot drift apart. Build the fixture database first,
then run:

    uv run --frozen python tests/record_ppsd_api.py

One story makes the real ones (tests/ppsd_story.py), as of October 28, 2026: Ana suggests PPSD rows for
KE-NWWDA-541055-CW-RFB from the two risks she selected, sets one owner, then the other, marks the rows as checked
(before the second owner, so export waits), exports them, and drafts the Project Paper summary, which she checks and
exports. Ben, her teammate, opens the rows. A rows draft with one failed cell and one with a row left out are recorded
too.

The states the fixture cannot reach (the Long Form above Table I, a package with no cost estimate, a summary with no
track record) are made up from the real answers, each named *-made-up-*.json and saying so in its made_up field. They
are never served as findings: the screen tests use them for layout and states only.
"""

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

import ppsd_story as story_of  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
OWNER = "Implementing agency, procurement unit"


def pretty(value) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def answers(folder: Path, fixture_db: Path = FIXTURE_DB) -> dict[str, str]:
    """Every real recorded answer, by its file name, as the text the file holds."""
    (folder / "library").mkdir()
    database = story_of.library(fixture_db, folder / "library")
    story = story_of.Story(database, folder)
    found: dict[str, str] = {}

    def get(name: str, path: str, headers=story_of.ANA, **params):
        found[name] = pretty(story.get(path, headers, **params).json())

    story.select()
    found["drafts-pp-inputs-none.json"] = pretty(story.get("/api/drafts/project-paper-inputs", project_id="P156634").json())
    story.case = "ppsd-rows-ke-nwwda-541055"
    found["drafts-write-ppsd.sse"] = story.call("POST", "/api/drafts", json={
        "kind": "ppsd_rows", "package": story_of.PACKAGE, "criteria": story_of.INDIA, "idempotency_key": "ppsd-1"}).text
    get("drafts-ppsd-draft.json", "/api/drafts/draft-0001")
    get("drafts-ppsd-teammate.json", "/api/drafts/draft-0001", story_of.BEN)
    get("drafts-existing-ppsd.json", "/api/drafts/existing", kind="ppsd_rows", package=story_of.PACKAGE)
    found["drafts-ppsd-some-owners.json"] = pretty(story.set_field("draft-0001", "cost_estimates", "risk_owner", OWNER).json())
    found["drafts-ppsd-checked-owners-left.json"] = pretty(story.act("draft-0001", "check", "draft").json())
    found["drafts-ppsd-export-held.json"] = pretty(story.act("draft-0001", "export", "checked").json())
    found["drafts-ppsd-checked.json"] = pretty(
        story.set_field("draft-0001", "permits_before_award", "risk_owner", OWNER).json())
    found["drafts-ppsd-exported.json"] = pretty(story.act("draft-0001", "export", "checked").json())
    get("drafts-pp-inputs.json", "/api/drafts/project-paper-inputs", project_id="P156634")
    story.case = "project-paper-p156634"
    found["drafts-write-pp.sse"] = story.call("POST", "/api/drafts", json={
        "kind": "project_paper", **story_of.PLAN, "idempotency_key": "pp-1"}).text
    get("drafts-pp-draft.json", "/api/drafts/draft-0002")
    get("drafts-existing-pp.json", "/api/drafts/existing", kind="project_paper", **story_of.PLAN)
    found["drafts-pp-checked.json"] = pretty(story.act("draft-0002", "check", "draft").json())
    found["drafts-pp-exported.json"] = pretty(story.act("draft-0002", "export", "checked").json())
    _, draft_id = story.suggest("ppsd-rows-one-cell-fails", "ppsd-2")
    get("drafts-ppsd-one-cell.json", f"/api/drafts/{draft_id}")
    _, draft_id = story.suggest("ppsd-rows-a-row-removed", "ppsd-3")
    get("drafts-ppsd-row-removed.json", f"/api/drafts/{draft_id}")
    _, draft_id = story.summarize("project-paper-p156634-no-ppsd", "pp-2")
    get("drafts-pp-no-ppsd.json", f"/api/drafts/{draft_id}")
    get("drafts-list-ppsd.json", "/api/drafts")
    return found


def made_up(real: dict[str, str]) -> dict[str, str]:
    """The states the fixture cannot reach, made up from the real answers, each saying so."""
    draft = json.loads(real["drafts-ppsd-draft.json"])
    paper = json.loads(real["drafts-pp-draft.json"])

    long_form = copy.deepcopy(draft)
    long_form["made_up"] = ("Made up from drafts-ppsd-draft.json: the package's cost estimate set at Table I's works "
                            "threshold, the Long Form chosen, one owner and one row's ratings set, for layout only.")
    long_form["ppsd"]["table_i"].update(applies=True, amount="60000000.00")
    long_form["ppsd"]["form"] = "long"
    values = {("cost_estimates", "risk_owner"): OWNER, ("cost_estimates", "likelihood"): "4",
              ("cost_estimates", "impact"): "3", ("cost_estimates", "score"): "12"}
    long_form["ppsd"]["values"] = [{"row_key": row["row_key"], "field": column["key"],
                                    "value": values.get((row["row_key"], column["key"]))}
                                   for row in long_form["ppsd"]["rows"]
                                   for column in long_form["ppsd"]["forms"]["long"]["columns"]
                                   if column["filled_by"] == "people"]
    long_form["ppsd"]["counts"] = {"total": 2, "owners_set": 1, "rated": 1}
    long_form["holds"] = [{"key": "notChecked", "copy": "notChecked", "left": 1, "first_anchor": None},
                          {"key": "owners", "copy": "owners", "left": 1,
                           "first_anchor": "fill-permits_before_award-risk_owner"},
                          {"key": "ratings", "copy": "ratings", "left": 1,
                           "first_anchor": "fill-permits_before_award-likelihood"}]

    no_amount = copy.deepcopy(draft)
    no_amount["made_up"] = "Made up from drafts-ppsd-draft.json: a package with no cost estimate, for layout only."
    no_amount["ppsd"]["table_i"].update(applies=False, amount=None, threshold=None)

    no_record = copy.deepcopy(paper)
    no_record["made_up"] = ("Made up from drafts-pp-draft.json: an agency with no measurable past package and one "
                            "agency with plans, for layout only.")
    for note in no_record["notes"]:
        if note["key"] == "record":
            note.update(state="abstained", reason="no_track_record", sentences=[])
    no_record["summary"]["parts"][1].update(reason="no_track_record", state="abstained")
    no_record["summary"]["agencies_with_plans"] = 1
    no_record["subject"]["agencies_with_plans"] = 1
    return {"drafts-ppsd-made-up-long.json": pretty(long_form), "drafts-ppsd-made-up-no-amount.json": pretty(no_amount),
            "drafts-pp-made-up-no-record.json": pretty(no_record)}


def main() -> int:
    if not FIXTURE_DB.exists():
        print("Build the fixture database first: uv run --frozen python gates/build_fixture.py")
        return 1
    with tempfile.TemporaryDirectory() as folder:
        real = answers(Path(folder))
    for name, text in {**real, **made_up(real)}.items():
        (OUT / name).write_text(text)
        print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
