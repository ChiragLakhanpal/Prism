"""Drafts at seam 3: review notes on a plan, written, checked and exported through the HTTP routes (ticket 35).

POST /api/drafts streams the writing of a draft: the check-a-plan workflow reads check_plan as the viewer,
its writer drafts one note per activity with a signal, the verifier checks every sentence, and only then
is the draft saved in strata.ops with its author's team. The writer is the scripted writer, replaying the
cases in tests/fixtures/agent/writers.toml. The draft then moves from Draft to Checked by you to Exported
only on its author's actions, through the routes. App state is written as the app's own service
principal, a DuckDB file here; the fixture database is opened read-only.

Expected values come from independent sources: the three activities with a signal and their marks from
the blueprint's Check a plan wireframe (tests/ground_truth/values.toml, plan_row wireframe_mark), and each
citation's evidence id from check_plan's own recorded answer (tests/fixtures/api).
"""

import asyncio
import datetime as dt
import json
import tomllib
from contextlib import contextmanager
from pathlib import Path

import httpx
import pytest

from strata.agent.loop import AgentError
from strata.agent.runs import RunLog
from strata.agent.scripted import WRITER_CASES, ScriptedAgent, ScriptedJudge, load_cases
from strata.config import load_draft_kinds, load_roles
from strata.drafts import files
from strata.drafts.store import DraftStore
from strata.lakehouse import catalog
from strata.lakehouse.engine import DuckDBEngine, PermissionDenied
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app
from strata.server.evidence import OpenedLog

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
CHECKED = json.loads((ROOT / "tests" / "fixtures" / "api" / "check-plan-p156634-nwwda-2026-10-09.json").read_text())
ROW_OF = {row["activity_reference_no"]: row["evidence_id"] for row in CHECKED["rows"]}
# The activities with a signal, in the wireframe's order: Needs a look first, then Watch.
MARKED = [row["reference"] for row in TRUTH["plan_row"] if row["wireframe_mark"] in ("Needs a look", "Watch")]
TODAY = dt.date(2026, 10, 23)
NWWDA = {"kind": "review_notes", "project_id": "P156634", "agency_id": "northern-water-works-development-agency",
         "plan_date": "2026-10-09"}


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"40{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN, CY = viewer(21, "Ana"), viewer(22, "Ben"), viewer(23, "Cy")
# Ana and Ben are on the roles file's Kenya water team; Cy is in no team's group.
GROUPS = {"4021@1984": ["strata-team-kenya-water"], "4022@1984": ["strata-team-kenya-water", "admins"],
          "4023@1984": ["admins"]}


class Clock:
    """The server's clock, which a test moves on."""

    def __init__(self, start: dt.datetime):
        self.at = start

    def __call__(self) -> dt.datetime:
        return self.at

    def move(self, **delta):
        self.at += dt.timedelta(**delta)


def call(app, method, path, headers=None, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers or {}, **options)
    return asyncio.run(go())


def events(text: str) -> list[tuple[str, dict]]:
    """A server-sent event stream's events, as (type, data), without its keep-alive comments."""
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if lines:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


@pytest.fixture
def state_db(tmp_path):
    path = tmp_path / "state.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def clock():
    return Clock(dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC))


@pytest.fixture
def drafting(fixture_db, state_db, clock):
    """The app with the fixture database, app state in a DuckDB file, and the scripted writer of a case."""
    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    def make(case: str = "review-notes-nwwda-2026-10-09", writer=None, groups=GROUPS, store=None, judge=None):
        written = load_cases(WRITER_CASES)[case]
        numbers = iter(range(1, 100))
        return create_app(engine_for=reading, drafts=store or DraftStore(state), opened=OpenedLog(state, now=clock),
                          writers=writer or (lambda kind: ScriptedAgent(written)), runs=RunLog(state),
                          access=Access(load_roles(), StaticGroups(groups)), today=lambda: TODAY, now=clock,
                          new_draft_id=lambda: f"draft-{next(numbers):04d}", new_run_id=lambda: "run-0001",
                          judge=judge)
    return make


def draft_review_notes(app, headers=ANA, key="key-1", **extra) -> tuple[list, str | None]:
    sent = events(call(app, "POST", "/api/drafts", headers, json={**NWWDA, "idempotency_key": key, **extra}).text)
    made = [data["draft_id"] for kind, data in sent if kind == "draft"]
    return sent, made[0] if made else None


def test_every_hold_a_kind_names_has_its_line_in_the_copy_file():
    """The draft bar shows each hold's line by its copy key, and copy.json repeats the bar's lines by kind."""
    kinds = load_draft_kinds()
    lines = json.loads((ROOT / "src" / "strata" / "drafts" / "copy.json").read_text())["holds"]

    for key, kind in kinds.kinds.items():
        for hold in kind.holds:
            assert kinds.holds[hold].copy in lines[key], f"{key}'s hold {hold} has no line in web/src/copy.ts"


def test_the_screens_recorded_draft_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    """tests/record_drafts_api.py writes the answers the draft screens' tests serve, from one story on the
    fixture; the routes must still answer with them word for word."""
    from record_drafts_api import answers

    for name, text in answers(tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), f"{name} is out of date"


# ── Writing the draft ────────────────────────────────────────────────────

def test_draft_review_notes_writes_a_note_on_each_activity_with_a_signal_each_citing_its_plan_row(drafting):
    app = drafting()

    sent, draft_id = draft_review_notes(app)

    assert [data["id"] for kind, data in sent if kind == "step" and data["status"] == "done"] == [
        "read", "write", "check", "save"]
    assert draft_id is not None
    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    assert [note["activity_reference_no"] for note in draft["notes"]] == MARKED
    project = CHECKED["project"]["evidence_id"]
    for note in draft["notes"]:
        cited = {evidence for sentence in note["sentences"] for evidence in sentence["evidence_ids"]}
        assert note["state"] == "written" and note["sentences"]
        # Each note cites its own row, and the records its row's reasons name (ticket 61): the project record, for
        # the closing date that KE-NWWDA-541062-CW-RFQ's reason states.
        assert cited == {ROW_OF[note["activity_reference_no"]]} | (
            {project} if note["activity_reference_no"] == "KE-NWWDA-541062-CW-RFQ" else set())
    closing = next(sentence for note in draft["notes"] for sentence in note["sentences"]
                   if "the project closes on October 31, 2026" in sentence["text"])
    assert closing["evidence_ids"] == [ROW_OF["KE-NWWDA-541062-CW-RFQ"], project]
    # The date is the project record's: checks 1 to 3 read the row without the closing date its reason repeats.
    assert closing["dates"] == [{"text": "October 31, 2026", "evidence_id": project}]
    assert draft["evidence"][project]["row"]["closing_date"] == "2026-10-31"
    # No sentence states the date of another plan version, which no footnote of this plan's could point at.
    assert not [sentence for note in draft["notes"] for sentence in note["sentences"] if "March 5" in sentence["text"]]
    # Every sentence the writer wrote passed the checks the verifier runs, and none was removed.
    checks = draft["checks"]
    assert checks["sentences"]["kept"] == checks["sentences"]["written"] and checks["sentences"]["removed"] == 0
    assert draft["removed"] == []
    assert (draft["state"], draft["kind"], draft["author"]) == ("draft", "review_notes", {"name": "Ana Example", "you": True})
    # The six checks ran on every sentence, as on an answer (ticket 24), and each sentence states a value its
    # row holds, so checks 1 to 3 proved them all and no model was needed.
    assert checks["checks_run"] == [1, 2, 3, 4, 5, 6]
    assert (checks["judge"]["called"], checks["judge"]["proven"]) == (False, checks["sentences"]["written"])
    assert [data["checks_run"] for kind, data in sent if kind == "step" and data["id"] == "check"
            and data["status"] == "done"] == [[1, 2, 3, 4, 5, 6]]


def test_a_note_sentence_its_row_does_not_support_and_advice_with_no_lesson_are_removed_after_one_judge_call(drafting):
    """Checks 4 and 5 on a draft: the judge is asked once, about the one sentence checks 1 to 3 could not prove,
    and says it does not follow; the advice cites only its plan row, which backs no advice, so check 5 removes it
    before the judge sees it."""
    case = load_cases(WRITER_CASES)["review-notes-checks-4-and-5"]
    judge = ScriptedJudge(case)
    app = drafting(case.id, judge=judge)

    _, draft_id = draft_review_notes(app)

    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    assert [(item["key"], item["sentence"], item["reason"]) for item in draft["removed"]] == [
        (MARKED[2], "The agency has stopped working on this activity.", "not_supported"),
        (MARKED[2], "Ask the agency to publish a new planned signing date.", "advice_without_lesson_or_comparable")]
    assert [[question.sentence for question in asked] for asked in judge.calls] == [
        ["The agency has stopped working on this activity.", "The plan records no signed contract for this activity."]]
    [note] = [note for note in draft["notes"] if note["activity_reference_no"] == MARKED[2]]
    assert [sentence["text"] for sentence in note["sentences"]] == [
        "The plan lists this activity as Pending Implementation, with an Actual Amount of 0.00.",
        "The plan records no signed contract for this activity."]
    checks = draft["checks"]
    assert checks["checks_run"] == [1, 2, 3, 4, 5, 6]
    assert checks["advice"] == {"total": 1, "cited": 0}
    assert (checks["judge"]["called"], checks["judge"]["judged"], checks["judge"]["followed"]) == (True, 2, 1)
    # The evidence pack's check line, which the draft page writes word for word, says a model judged one sentence.
    assert files.check_line(checks, load_draft_kinds().kinds["review_notes"]) == (
        "Checked: 6 of 6 numbers match records; 3 of 3 dates match records. "
        "Judged by a model: 1 of 1 sentence follows from its sources. "
        "The other five needed no model, because everything they stated matched a record or a page. "
        "Not checked: whether the plan's published records are complete, "
        "or whether these notes are what you would tell the borrower.")


def test_the_draft_s_check_line_names_a_cited_only_tool_only_once_a_sentence_on_screen_cites_it(drafting):
    """Ticket 24's review round 3, follow-up 7: a tool whose "Not checked" clause applies only once a sentence cites
    it (config/tools.toml, not_checked_when = "cited", get_lessons) is named in the draft's checks as in an answer's,
    and the evidence pack's check line follows the page's rule (notCheckedFor in web/src/components/Checks.tsx)."""
    app = drafting()
    _, draft_id = draft_review_notes(app)
    checks = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()["checks"]
    kind = load_draft_kinds().kinds["review_notes"]
    clause = files.words()["checkLine"]["notCheckedClauses"]["get_lessons"]

    assert checks["cited_only"] == ["get_lessons"]
    ran = {**checks, "tools": [*checks["tools"], "get_lessons"]}
    assert clause not in files.check_line(ran, kind)
    assert clause in files.check_line({**ran, "cited_tools": [*checks["cited_tools"], "get_lessons"]}, kind)


def test_a_note_sentence_that_cites_nothing_is_removed_and_never_saved(drafting):
    """Ticket 24's verify F1, round 2, on a draft: a summary that cites nothing has nothing to be checked against, so
    check 2 removes it before the judge, and the judge is not called, because checks 1 to 3 prove the rest."""
    case = load_cases(WRITER_CASES)["review-notes-uncited-summary"]
    judge = ScriptedJudge(case)
    app = drafting(case.id, judge=judge)

    _, draft_id = draft_review_notes(app)

    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    assert [(item["key"], item["sentence"], item["reason"]) for item in draft["removed"]] == [
        (MARKED[2], "The agency was to blame for the delay.", "no_source")]
    [note] = [note for note in draft["notes"] if note["activity_reference_no"] == MARKED[2]]
    assert [sentence["text"] for sentence in note["sentences"]] == [
        "The plan lists this activity as Pending Implementation, with an Actual Amount of 0.00."]
    assert judge.calls == []
    assert draft["checks"]["checks_run"] == [1, 2, 3, 4, 5, 6]


def test_a_note_sentence_stating_a_date_only_another_record_holds_is_removed_unless_it_cites_that_record(drafting):
    """Ticket 61's verify F2 and review F1: check_plan's row repeats dates that other records hold, the plan version
    that first published a planned date and, in a reason, the project's closing date. A sentence that stated one and
    cited only the row was kept, and its only footnote pointed at this plan's page, which holds neither date. Checks
    1 to 3 now read the row without them, so such a sentence is removed, and the closing date is kept where the
    sentence also cites the project record, which holds it and gets its own footnote."""
    project = CHECKED["project"]["evidence_id"]
    app = drafting("review-notes-dates-of-other-records")

    _, draft_id = draft_review_notes(app)

    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    assert [(item["key"], item["sentence"], item["reason"]) for item in draft["removed"]] == [
        ("KE-NWWDA-541055-CW-RFB", "Its planned completion of July 31, 2026, first published in the plan of March 5, "
         "2026, has passed with no signed contract.", "date_not_in_records"),
        ("KE-NWWDA-541062-CW-RFQ", "The project closes on October 31, 2026.", "date_not_in_records")]
    [kept] = [sentence for note in draft["notes"] if note["activity_reference_no"] == "KE-NWWDA-541062-CW-RFQ"
              for sentence in note["sentences"]]
    assert kept["text"] == "The project's closing date is October 31, 2026."
    assert kept["dates"] == [{"text": "October 31, 2026", "evidence_id": project}]


def test_with_no_judge_connected_a_note_sentence_that_needs_one_is_removed_and_never_saved_unchecked(drafting):
    app = drafting("review-notes-checks-4-and-5")

    _, draft_id = draft_review_notes(app)

    removed = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()["removed"]
    assert [(item["sentence"], item["reason"]) for item in removed][0] == (
        "The agency has stopped working on this activity.", "judge_unavailable")


def test_the_same_request_sent_twice_saves_one_draft(drafting):
    app = drafting()

    _, first = draft_review_notes(app, key="key-twice")
    _, second = draft_review_notes(app, key="key-twice")

    assert first == second
    listed = call(app, "GET", "/api/drafts", ANA).json()
    assert [row["draft_id"] for row in listed["groups"]["to_check"]] == [first]


def test_when_no_sentence_passes_the_checks_no_draft_is_saved(drafting):
    app = drafting("review-notes-nothing-passes")

    sent, draft_id = draft_review_notes(app)

    assert draft_id is None
    [(_, nothing)] = [(kind, data) for kind, data in sent if kind == "nothing_survived"]
    assert {item["reason"] for item in nothing["removed"]} == {"id_not_returned"}
    assert "save" not in [data["id"] for kind, data in sent if kind == "step"]
    assert call(app, "GET", "/api/drafts", ANA).json()["total"] == 0


def test_an_activity_whose_sentences_all_fail_keeps_its_row_with_no_note_and_its_removed_sentences(drafting):
    app = drafting("review-notes-one-activity-fails")

    _, draft_id = draft_review_notes(app)

    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    assert [(note["activity_reference_no"], note["state"]) for note in draft["notes"]] == [
        (MARKED[0], "written"), (MARKED[1], "written"), (MARKED[2], "abstained")]
    assert [item["reason"] for item in draft["removed"]] == ["number_not_in_records", "date_not_in_records"]
    assert draft["counts"] == {"signal": 3, "written": 2}


def test_a_sentence_citing_another_activity_s_row_is_removed_from_the_note(drafting):
    app = drafting("review-notes-a-cross-cited-sentence")

    _, draft_id = draft_review_notes(app)

    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    first = draft["notes"][0]
    assert [sentence["text"] for sentence in first["sentences"]] == [
        "The plan lists this activity as Pending Implementation, with an Actual Amount of 0.00."]
    [removed] = draft["removed"]
    assert (removed["key"], removed["reason"], removed["sentence"]) == (
        MARKED[0], "id_not_returned", "The plan records an Actual Amount of 1,245,092.76.")


def test_a_refused_activity_keeps_its_row_with_the_refusal_and_no_sentence(drafting):
    app = drafting("review-notes-a-refused-activity")

    _, draft_id = draft_review_notes(app)

    [refused] = [note for note in call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()["notes"] if note["state"] == "refused"]
    assert (refused["activity_reference_no"], refused["refusal"], refused["sentences"]) == (MARKED[2], "out_of_scope", [])


def test_the_writer_s_run_is_logged_with_what_the_verifier_found(drafting, state_db):
    app = drafting()

    draft_review_notes(app)

    with DuckDBEngine.open(state_db, read_only=True) as engine:
        result = engine.run("SELECT run_id, viewer_id, scope, agent, status, sentences_written, sentences_removed "
                            "FROM strata.ops.agent_runs")
    assert result.rows == (("run-0001", "4021@1984", "P156634", "strata-review-notes-writer", "answered", 6, 0),)


class Unavailable:
    name, version = "strata-review-notes-writer", None

    def respond(self, items, previous_response_id):
        raise AgentError("agent_unavailable", "The model did not answer.")


@pytest.mark.parametrize("writer, code", [(lambda kind: None, "no_agent"), (lambda kind: Unavailable(), "agent_unavailable")])
def test_when_the_writer_is_not_connected_or_does_not_answer_nothing_is_saved_and_the_stream_says_why(drafting, writer, code):
    app = drafting(writer=writer)

    sent, draft_id = draft_review_notes(app)

    assert draft_id is None
    assert [data for kind, data in sent if kind == "error"] == [{"code": code}]
    assert sent[-1][0] == "done"
    assert call(app, "GET", "/api/drafts", ANA).json()["total"] == 0


class RefusedStore(DraftStore):
    """The app's own account may not write or read the drafts tables."""

    def __init__(self):
        super().__init__(lambda: None)

    def _open(self):
        raise PermissionDenied("The app's service principal has no grant on strata.ops.")


def test_when_the_app_cannot_save_or_read_drafts_the_viewer_is_not_blamed(drafting):
    app = drafting(store=RefusedStore())

    sent, draft_id = draft_review_notes(app, key=None)
    listed = call(app, "GET", "/api/drafts", ANA)

    assert draft_id is None
    assert [data for kind, data in sent if kind == "error"] == [{"code": "draft_store"}]
    assert (listed.status_code, listed.json()["code"]) == (503, "draft_store")


def test_a_request_with_no_forwarded_viewer_writes_nothing(drafting):
    answer = call(drafting(), "POST", "/api/drafts", {}, json={**NWWDA, "idempotency_key": "key-1"})

    assert (answer.status_code, answer.json()["code"]) == (401, "no_identity")


# ── Draft, Checked by you, Exported: only on the author's acts ───────────

def act(app, draft_id, action, expected, headers=ANA, view="staff"):
    return call(app, "POST", f"/api/drafts/{draft_id}/{action}", headers, json={"expected_state": expected, "view": view})


def test_a_draft_moves_from_draft_to_checked_by_you_to_exported_only_on_its_author_s_acts(drafting, clock):
    app = drafting()
    _, draft_id = draft_review_notes(app)
    opened = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    # Until its author marks it as checked, export is held, and the bar says why.
    assert (opened["state"], [hold["key"] for hold in opened["holds"]], opened["may_act"]) == ("draft", ["notChecked"], True)

    refused = act(app, draft_id, "export", "draft")
    assert (refused.status_code, refused.json()["error"], refused.json()["state"]) == (409, "draft_state", "draft")
    clock.move(minutes=5)
    checked = act(app, draft_id, "check", "draft")
    assert checked.status_code == 200
    assert (checked.json()["state"], checked.json()["holds"]) == ("checked", [])
    assert checked.json()["checked"] == {"at": "2026-10-23T14:05:00Z", "by": "Ana Example", "you": True}
    clock.move(minutes=5)
    exported = act(app, draft_id, "export", "checked")
    assert exported.status_code == 200
    assert (exported.json()["state"], exported.json()["may_act"]) == ("exported", False)
    # Nothing moves a draft on its own: reading it again finds it where its author left it.
    assert call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()["state"] == "exported"


def test_a_teammate_can_open_the_draft_but_only_its_author_can_act_on_it(drafting):
    app = drafting()
    _, draft_id = draft_review_notes(app)

    seen = call(app, "GET", f"/api/drafts/{draft_id}", BEN)
    refused = act(app, draft_id, "check", "draft", headers=BEN)

    assert seen.status_code == 200
    assert (seen.json()["author"], seen.json()["may_act"]) == ({"name": "Ana Example", "you": False}, False)
    assert (refused.status_code, refused.json()["error"]) == (403, "not_author")
    assert call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()["state"] == "draft"


def test_a_draft_another_team_made_is_not_found(drafting):
    app = drafting()
    _, draft_id = draft_review_notes(app)

    for method, path in (("GET", f"/api/drafts/{draft_id}"), ("POST", f"/api/drafts/{draft_id}/check")):
        answer = call(app, method, path, CY, **({"json": {"expected_state": "draft"}} if method == "POST" else {}))
        assert (answer.status_code, answer.json()["code"]) == (404, "unknown_draft")


def test_an_author_keeps_their_own_drafts_after_a_group_puts_them_on_a_team(drafting):
    # Cy, on no team, saves a draft; then a workspace group puts Cy on the Kenya water team.
    groups = dict(GROUPS)
    app = drafting(groups=groups)
    _, draft_id = draft_review_notes(app, headers=CY)
    groups["4023@1984"] = ["strata-team-kenya-water"]

    opened = call(app, "GET", f"/api/drafts/{draft_id}", CY)
    listed = call(app, "GET", "/api/drafts", CY).json()

    assert (opened.status_code, opened.json()["author"]["you"]) == (200, True)
    assert [row["draft_id"] for row in listed["groups"]["to_check"]] == [draft_id]
    assert act(app, draft_id, "check", "draft", headers=CY).status_code == 200
    # Ana, already on the team, never saw a draft Cy saved before joining it.
    assert call(app, "GET", f"/api/drafts/{draft_id}", ANA).status_code == 404


@pytest.mark.parametrize("view", ["piu", "public"])
def test_a_preview_cannot_check_or_export_and_says_which_capability_and_why(drafting, view):
    app = drafting()
    _, draft_id = draft_review_notes(app)
    act(app, draft_id, "check", "draft")

    # The capability and the reason's copy key are the roles file's [views] (ticket 40), so the draft bar's held
    # button and the server say the same sentence.
    for action, expected, capability in (("check", "draft", "mark_checked"), ("export", "checked", "export_draft")):
        refused = act(app, draft_id, action, expected, view=view)
        assert refused.status_code == 403
        assert {key: refused.json()[key] for key in ("error", "capability", "copy_key")} == {
            "error": "preview", "capability": capability, "copy_key": "draft.bar.hold.preview"}
    assert call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()["state"] == "checked"


def test_an_act_on_a_state_the_author_no_longer_sees_is_refused_with_the_state_now(drafting):
    # Another tab marked the draft as checked; this one still shows it as a draft.
    app = drafting()
    _, draft_id = draft_review_notes(app)
    act(app, draft_id, "check", "draft")

    stale = act(app, draft_id, "check", "draft")

    assert (stale.status_code, stale.json()["error"], stale.json()["state"]) == (409, "stale", "checked")


@pytest.mark.parametrize("checked_first", [False, True])
def test_discard_can_be_undone_and_restores_the_state_the_draft_was_in(drafting, checked_first):
    app = drafting()
    _, draft_id = draft_review_notes(app)
    before = "draft"
    if checked_first:
        act(app, draft_id, "check", "draft")
        before = "checked"

    discarded = act(app, draft_id, "discard", before)
    assert (discarded.json()["state"], discarded.json()["discarded_from"]) == ("discarded", before)
    assert call(app, "GET", "/api/drafts", BEN).json()["total"] == 0  # the team no longer sees it
    restored = act(app, draft_id, "restore", "discarded")

    assert restored.json()["state"] == before
    assert [row["draft_id"] for row in call(app, "GET", "/api/drafts", BEN).json()["groups"][
        "to_check" if before == "draft" else "checked"]] == [draft_id]


def test_after_restore_checked_by_keeps_the_time_of_the_check(drafting, clock):
    app = drafting()
    _, draft_id = draft_review_notes(app)
    clock.move(minutes=5)
    act(app, draft_id, "check", "draft")
    clock.move(minutes=1)
    act(app, draft_id, "discard", "checked")
    clock.move(minutes=1)

    restored = act(app, draft_id, "restore", "discarded").json()

    assert restored["checked"] == {"at": "2026-10-23T14:05:00Z", "by": "Ana Example", "you": True}
    [row] = call(app, "GET", "/api/drafts", ANA).json()["groups"]["checked"]
    assert row["checked"] == {"at": "2026-10-23T14:05:00Z", "by": "Ana Example", "you": True}


def test_an_exported_draft_cannot_be_discarded(drafting):
    app = drafting()
    _, draft_id = draft_review_notes(app)
    act(app, draft_id, "check", "draft")
    act(app, draft_id, "export", "checked")

    refused = act(app, draft_id, "discard", "exported")

    assert (refused.status_code, refused.json()["error"], refused.json()["state"]) == (409, "draft_state", "exported")


# ── "You opened N of M sources" ──────────────────────────────────────────

def open_source(app, evidence_id, headers=ANA):
    answer = call(app, "POST", "/api/evidence/opened", headers, json={"evidence_id": evidence_id, "route": "/drafts/x"})
    assert answer.json() == {"recorded": True}


def test_you_opened_counts_the_distinct_cited_sources_this_viewer_opened_since_the_draft_was_saved(drafting, clock):
    app = drafting()
    # An open before the draft was saved is from an earlier visit, so it does not count.
    open_source(app, ROW_OF[MARKED[0]])
    clock.move(minutes=1)
    _, draft_id = draft_review_notes(app)
    fresh = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    # Each note cites its own plan row (check_plan's recorded answer), and the closing date's note also the project
    # record its reason names (ticket 61).
    assert fresh["opened"] == {"count": 0, "of": len(MARKED) + 1}
    assert [entry["evidence_id"] for entry in fresh["sources"]] == [ROW_OF[ref] for ref in MARKED] + [
        CHECKED["project"]["evidence_id"]]

    clock.move(minutes=1)
    open_source(app, ROW_OF[MARKED[1]])
    open_source(app, ROW_OF[MARKED[1]])  # opened twice, counted once
    open_source(app, ROW_OF[MARKED[2]], headers=BEN)  # a teammate's open counts for the teammate only

    mine = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()
    assert mine["opened"] == {"count": 1, "of": 4}
    assert [entry["opened"] for entry in mine["sources"]] == [False, True, False, False]
    assert call(app, "GET", f"/api/drafts/{draft_id}", BEN).json()["opened"] == {"count": 1, "of": 4}
    # The Drafts tab gives the author the same count on their own draft to check.
    [row] = call(app, "GET", "/api/drafts", ANA).json()["groups"]["to_check"]
    assert row["opened"] == {"count": 1, "of": 4}


# ── The Drafts tab ───────────────────────────────────────────────────────

def test_the_drafts_tab_lists_only_the_author_s_team_s_drafts_under_to_check_checked_and_exported(drafting, clock):
    app = drafting()
    made = []
    for key in ("key-a", "key-b", "key-c", "key-d"):
        clock.move(minutes=1)
        made.append(draft_review_notes(app, key=key)[1])
    first, second, third, fourth = made
    clock.move(minutes=1)
    act(app, second, "check", "draft")
    act(app, third, "check", "draft")
    clock.move(minutes=1)
    act(app, third, "export", "checked")
    act(app, fourth, "discard", "draft")

    teammate = call(app, "GET", "/api/drafts", BEN).json()
    author = call(app, "GET", "/api/drafts", ANA).json()
    outsider = call(app, "GET", "/api/drafts", CY).json()

    by_group = {group: [row["draft_id"] for row in rows] for group, rows in teammate["groups"].items()}
    assert by_group == {"to_check": [first], "checked": [second], "exported": [third]}
    assert teammate["counts"] == {"to_check": 1, "checked": 1, "exported": 1}
    # Only the author's own drafts to check carry the opened count, and only the author sees what they discarded.
    assert [row["opened"] for row in teammate["groups"]["to_check"]] == [None]
    assert [row["opened"] for row in author["groups"]["to_check"]] == [{"count": 0, "of": 4}]
    assert ([row["draft_id"] for row in author["discarded"]], teammate["discarded"]) == ([fourth], [])
    assert (outsider["total"], outsider["groups"]) == (0, {"to_check": [], "checked": [], "exported": []})
    row = author["groups"]["checked"][0]
    assert (row["notes"], row["subject"]["plan_date"], row["changed"]["you"]) == (3, "2026-10-09", True)


def test_a_preview_lists_no_drafts_and_says_why(drafting):
    app = drafting()
    draft_review_notes(app)

    # Drafts are private to their team, so no preview keeps them (the roles file's [views], ticket 40).
    for view in ("piu", "public"):
        answer = call(app, "GET", "/api/drafts", ANA, params={"view": view})
        assert (answer.status_code, answer.json()["error"], answer.json()["view"]) == (404, "not_in_view", view)


def test_check_a_plan_finds_the_team_s_open_draft_on_the_same_plan_version(drafting, clock):
    app = drafting()
    asked = {"kind": "review_notes", "project_id": "P156634", "agency_id": NWWDA["agency_id"], "plan_date": "2026-10-09"}
    assert call(app, "GET", "/api/drafts/existing", BEN, params=asked).json() == {"draft": None}
    _, draft_id = draft_review_notes(app)

    found = call(app, "GET", "/api/drafts/existing", BEN, params=asked).json()["draft"]
    other_version = call(app, "GET", "/api/drafts/existing", BEN, params={**asked, "plan_date": "2026-03-05"}).json()

    assert (found["draft_id"], found["author"], found["created_at"]) == (
        draft_id, {"name": "Ana Example", "you": False}, "2026-10-23T14:00:00Z")
    assert other_version == {"draft": None}
    assert call(app, "GET", "/api/drafts/existing", CY, params=asked).json() == {"draft": None}
    clock.move(minutes=1)
    act(app, draft_id, "check", "draft")
    act(app, draft_id, "export", "checked")
    assert call(app, "GET", "/api/drafts/existing", BEN, params=asked).json() == {"draft": None}


def test_with_no_plan_date_the_lookup_names_the_open_draft_on_each_plan_version(drafting):
    """The plan check with no version in its address asks before it knows the plan's date (the 35 review)."""
    app = drafting()
    asked = {"kind": "review_notes", "project_id": "P156634", "agency_id": NWWDA["agency_id"]}
    assert call(app, "GET", "/api/drafts/existing", BEN, params=asked).json() == {"by_plan_date": {}}
    _, draft_id = draft_review_notes(app)

    found = call(app, "GET", "/api/drafts/existing", BEN, params=asked).json()["by_plan_date"]
    other_agency = call(app, "GET", "/api/drafts/existing", BEN, params={**asked, "agency_id": "another-agency"}).json()

    assert found == {"2026-10-09": {"draft_id": draft_id, "created_at": "2026-10-23T14:00:00Z",
                                    "author": {"name": "Ana Example", "you": False}}}
    assert other_agency == {"by_plan_date": {}}
    assert call(app, "GET", "/api/drafts/existing", CY, params=asked).json() == {"by_plan_date": {}}
