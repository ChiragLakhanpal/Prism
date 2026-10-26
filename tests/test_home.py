"""Home (ticket 41): the briefing, the Start here strip, "Worth knowing", "Waiting for you" and the seed command, through
the HTTP routes (seam 3), on tests/home_story.py's story: Ana's examples set up by the seed command on a copy of the
fixture with its three lessons decided, as of October 28, 2026, with a window of 15 days ending on the fixture's
data-through date, October 23.

Every expected sentence is written here from tests/ground_truth/values.toml and the wireframe, never from Home's code.
"""

from __future__ import annotations

import datetime as dt
import tomllib
from pathlib import Path

import pytest

import home_story
from home_story import ANA, ANA_PANELIST, BEN, CY
from strata.config import ConfigError, load_examples, load_roles
from strata.lakehouse.engine import DuckDBEngine
from strata.seed_examples import EXAMPLE_KEYS, panel, plan
from strata.server.home import text_of

ROOT = Path(__file__).resolve().parents[1]
TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())
NWWDA_PLAN = "/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09"


def value(key: str):
    return next(entry for entry in TRUTH["value"] if entry["id"] == key)["value"]


def long(day: dt.date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


@pytest.fixture(scope="module")
def built(fixture_db, tmp_path_factory):
    return home_story.build(fixture_db, tmp_path_factory.mktemp("home-built"))


@pytest.fixture
def story(built, tmp_path):
    return home_story.story_at(built, tmp_path / "story")


def sentences(answer: dict) -> list[str]:
    return [text_of(sentence) for sentence in answer["briefing"]["sentences"]]


def counts(answer: dict) -> dict[str, dict]:
    return {segment["kind"]: segment for sentence in answer["briefing"]["sentences"] for segment in sentence
            if "kind" in segment}


def lines(answer: dict, kind: str | None = None, status: str | None = None) -> list[dict]:
    return [line for line in answer["worth"]["lines"] if (kind is None or line["kind"] == kind)
            and (status is None or line["status"] == status)]


# ── The briefing and its lines ───────────────────────────────────────────

def test_the_briefing_reads_like_the_tickets_and_each_count_equals_the_lines_it_counts(story):
    answer = story.home().json()

    assert sentences(answer) == ["One plan changed in the past 15 days.",
                                 "One of its activities needs a look and two are worth watching.",
                                 "One lesson cited in your drafts changed.",
                                 "Two drafts are waiting for you to check."]
    found = counts(answer)
    assert {kind: found[kind]["count"] for kind in found} == {"plans": 1, "look": 1, "watch": 2, "lessonsChanged": 1,
                                                              "drafts": 2}
    # Each count lists the ids of what it counts, and those are the lines below, kind by kind.
    assert found["look"]["ids"] == [line["id"] for line in lines(answer, "activity", "needs_a_look")]
    assert found["watch"]["ids"] == [line["id"] for line in lines(answer, "activity", "watch")]
    assert found["lessonsChanged"]["ids"] == [line["id"] for line in lines(answer, "lesson", "changed")]
    assert found["drafts"]["ids"] == [row["draft_id"] for row in answer["waiting"]["rows"]]
    assert found["plans"]["ids"] == sorted({line["plan"] for line in lines(answer, "activity")})
    assert answer["window"] | {"phrase": None} == {"days": 15, "start": "2026-10-09", "end": "2026-10-23",
                                                   "data_through": "2026-10-23", "phrase": None}


def test_the_first_two_lines_are_the_wireframes_real_lines_from_the_nwwda_plan_of_october_9(story):
    answer = story.home().json()
    first, second = lines(answer)[:2]
    name, closes = value("project-name-p156634"), long(value("closing-date-p156634"))
    completion = long(value("plan-541055-planned-completion"))
    actual, estimate = value("plan-229129-actual"), value("plan-229129-estimated")

    # The wireframe's two real lines, with the project named from its record and "in the plan" after "no signed
    # contract", because the awards dataset shows the contract signed (values.toml, award-541055-signed).
    assert text_of(first["segments"]) == (
        f"KE-NWWDA-541055-CW-RFB, US$1.23 million of works in the {name} (P156634), passed its planned completion "
        f"date of {completion} with no signed contract in the plan. The project closes {closes}.")
    assert text_of(second["segments"]) == (
        f"In the same plan, KE-NWWDA-229129-CW-RFB was signed at US${actual:,.2f} against an estimate of "
        f"US${estimate:,.0f}.")
    assert (first["status"], second["status"]) == ("needs_a_look", "watch")
    # Each "Open the activity" lands on that activity's page, and each line cites its plan row.
    assert first["action"] == {"key": "openActivity", "href": "/projects/P156634/packages/KE-NWWDA-541055-CW-RFB",
                               "hidden": "KE-NWWDA-541055-CW-RFB"}
    assert second["action"]["href"] == "/projects/P156634/packages/KE-NWWDA-229129-CW-RFB"
    assert first["source"]["evidence_id"] == "strata.silver.plan_rows:40132287/KE-NWWDA-541055-CW-RFB"
    assert first["source"]["date"] == value("plan-2026-10-09-disclosed").isoformat()


def test_each_activity_page_the_lines_open_answers_for_its_activity(story):
    for line in lines(story.home().json(), "activity"):
        reference = line["action"]["href"].rsplit("/", 1)[1]
        assert story.get(f"/api/projects/P156634/packages/{reference}").status_code == 200, reference


def test_the_default_window_of_seven_days_ending_on_the_data_through_date_leaves_the_october_9_plan_out(built, tmp_path):
    story = home_story.story_at(built, tmp_path / "seven", window_days=7)
    answer = story.home().json()

    assert answer["window"]["start"] == "2026-10-17"
    assert lines(answer, "activity") == []
    assert sentences(answer) == ["No plan changed in the past seven days.", "One lesson cited in your drafts changed.",
                                 "Two drafts are waiting for you to check."]


def test_a_project_level_signal_disclosed_in_the_window_is_a_project_line(built, tmp_path):
    """With a window of 400 days, P156634's third closing date move, on November 30, 2025, falls inside it."""
    story = home_story.story_at(built, tmp_path / "long", window_days=400)
    answer = story.home().json()

    [project] = lines(answer, "project")
    assert text_of(project["segments"]) == ("The closing date of the Water and Sanitation Development Project (P156634) "
                                            "moved again on November 30, 2025. It has moved three times since 2022.")
    assert project["action"]["href"] == "/projects/P156634"
    assert counts(answer)["projects"]["ids"] == [project["id"]]
    assert "One project you follow has a new signal." in sentences(answer)


def test_the_lesson_line_names_the_seeded_change_and_lands_on_its_notice(story):
    answer = story.home().json()
    [lesson] = lines(answer, "lesson")

    assert lesson["example"] is True
    assert text_of(lesson["segments"]).startswith('The lesson "') and text_of(lesson["segments"]).endswith(" cite version 1.")
    assert lesson["action"]["href"].startswith("/lessons#notice-lesson-")
    link = next(link for link in answer["start_here"]["links"] if link["key"] == "lessonChange")
    assert link["href"] == lesson["action"]["href"]


def test_a_viewer_who_follows_nothing_still_gets_the_lesson_count_for_the_lesson_lines_below(story):
    """Lesson lines come from the viewer's drafts, not their follows, so the briefing counts them on a first run too."""
    for project_id in ("P156634", "P130164"):
        assert story.call("DELETE", f"/api/projects/{project_id}/follow", json={"view": "staff"}).status_code == 200
    answer = story.home().json()

    assert sentences(answer) == ["You don't follow any projects yet, so I have no plans to brief you on.",
                                 "One lesson cited in your drafts changed.",
                                 "Two drafts are waiting for you to check."]
    assert counts(answer)["lessonsChanged"]["ids"] == [line["id"] for line in lines(answer, "lesson", "changed")]
    assert len(lines(answer, "lesson", "changed")) == 1


def test_every_kind_of_draft_has_the_words_a_lesson_line_names_it_by():
    """A lesson line names the draft that cites the lesson by its kind ("Your suggested PPSD risk rows for ... cite"),
    so a kind added to config/drafts.toml fails here until copy.home.server.line.cites has its words."""
    from strata.config import load_draft_kinds
    from strata.server.home import words

    assert set(words()["line"]["cites"]) == set(load_draft_kinds().kinds)


def test_home_calls_no_model_and_answers_in_at_most_15_kb(story):
    from strata.server.app import model_routes

    response = story.home()
    assert len(response.content) <= 15 * 1024
    assert {"method": "GET", "path": "/api/home"} not in model_routes(story.app)


# ── Waiting for you ──────────────────────────────────────────────────────

def test_waiting_for_you_lists_the_viewers_drafts_to_check_with_their_progress_and_empties_as_work_is_done(story):
    waiting = story.home().json()["waiting"]

    assert [row["kind"] for row in waiting["rows"]] == ["ppsd_rows", "review_notes"]
    ppsd, notes = waiting["rows"]
    # Strata never sets a risk owner, so the seeded rows start at none of two set (the 41 brief, 4.5).
    assert (ppsd["progress"]["owners_set"], ppsd["progress"]["total"]) == (0, 2)
    assert notes["opened"]["count"] == 0 and notes["opened"]["of"] > 0
    assert all(row["example"] for row in waiting["rows"])

    for row in waiting["rows"]:
        assert story.act(row["draft_id"], "check", "draft").status_code == 200
    answer = story.home().json()

    assert answer["waiting"]["rows"] == [] and answer["waiting"]["total"] == 0
    assert sentences(answer)[-1] == "No draft is waiting for you to check."


def test_a_teammate_sees_none_of_anas_drafts_and_a_first_run_briefing(story):
    answer = story.home(BEN).json()

    assert sentences(answer) == ["You don't follow any projects yet, so I have no plans to brief you on.",
                                 "No draft is waiting for you to check."]
    assert answer["worth"]["empty"] == "first_run" and answer["waiting"]["rows"] == []


# ── Start here ───────────────────────────────────────────────────────────

def test_each_start_here_link_lands_where_it_says(story):
    links = {link["key"]: link for link in story.home().json()["start_here"]["links"]}

    assert list(links) == ["checkPlan", "planPackage", "wholeStory", "lessonChange", "checkData", "publicView"]
    assert links["checkPlan"]["href"] == NWWDA_PLAN and links["checkPlan"]["pid"] == "P156634"
    assert story.get("/api/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09").status_code == 200
    assert links["planPackage"]["href"] == "/packages?box=plan&example=rural_roads_kenya"
    assert story.get("/api/examples/rural_roads_kenya").json()["sentence"] == "rural roads, Kenya, about US$15 million"
    assert links["wholeStory"]["href"] == "/projects/P130164/timeline" and links["wholeStory"]["pid"] == "P130164"
    assert story.get("/api/projects/P130164/timeline").status_code == 200
    notice = links["lessonChange"]["href"].removeprefix("/lessons#")
    assert notice in [found["anchor"] for found in story.get("/api/lessons/page").json()["notices"]]
    assert links["checkData"]["href"] == "/data" and links["publicView"]["href"] == "/?view=public"


def test_remove_hides_the_strip_for_that_viewer_in_every_later_visit_and_show_again_brings_it_back(story):
    assert story.get("/api/me").json()["start_here_visible"] is True

    removed = story.call("POST", "/api/home/start-here", json={"visible": False, "view": "staff"})
    assert removed.json() == {"recorded": True, "visible": False}
    # A later visit, from any browser: the choice is kept on the server, per viewer.
    assert story.get("/api/me").json()["start_here_visible"] is False
    assert story.home().json()["start_here"]["visible"] is False
    assert story.get("/api/me", BEN).json()["start_here_visible"] is True

    story.call("POST", "/api/home/start-here", json={"visible": True, "view": "staff"})
    assert story.get("/api/me").json()["start_here_visible"] is True


def test_a_preview_cannot_remove_the_strip_and_never_shows_it(story):
    refused = story.call("POST", "/api/home/start-here", json={"visible": False, "view": "public"})

    assert refused.status_code == 403
    assert refused.json() | {"view": None} == {"code": "preview", "error": "preview", "capability": "start_here",
                                               "copy_key": "home.start.preview", "view": None}
    assert story.get("/api/me", view="public").json()["start_here_visible"] is False
    assert story.get("/api/me").json()["start_here_visible"] is True


def test_the_strip_shows_only_to_world_bank_staff(story):
    """Cy is signed in but holds no group the roles file's [staff] names, so the examples are not his."""
    assert story.get("/api/me", CY).json()["start_here_visible"] is False
    # No links either, so the page never reads the hidden strip as one Cy removed and offers to show it again.
    assert story.home(CY).json()["start_here"] == {"visible": False, "links": []}


# ── The roles table's other columns ──────────────────────────────────────

def test_the_agency_preview_lists_the_activities_behind_their_planned_dates_in_the_agencys_latest_plan(story):
    answer = story.home(view="piu").json()

    assert sentences(answer)[:2] == [
        f"I checked your team's latest Procurement Plan, the plan of October 9, 2026 for the "
        f"{value('project-name-p156634')} (P156634).",
        "Two of its activities are behind their planned dates."]
    assert [line["key"] for line in lines(answer)] == ["KE-NWWDA-541055-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]
    assert text_of(lines(answer)[0]["segments"]).startswith("KE-NWWDA-541055-CW-RFB passed its planned completion")
    # The preview shows no team's drafts and no examples, and says so.
    assert answer["waiting"] == {"rows": [], "total": 0, "more": False, "reason": "preview"}
    assert answer["start_here"]["visible"] is False and answer["preview"] is True


def test_an_officers_own_home_lists_their_plans_activities_behind_their_dates_and_their_own_drafts(fixture_db):
    """An implementing agency officer at NWWDA (tests/fixtures/roles.toml's team A), in their own view: the same
    activities as the agency preview, their own drafts in place of the preview's sentence, and no Start here."""
    import asyncio
    import dataclasses
    from contextlib import contextmanager

    import httpx

    from strata.server.access import Access, StaticGroups
    from strata.server.app import create_app

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    real = load_roles()
    roles = dataclasses.replace(real, teams=real.teams + load_roles(ROOT / "tests" / "fixtures" / "roles.toml").teams)
    officer = {"X-Forwarded-Email": "amina.example@worldbank.org", "X-Forwarded-User": "5031@1984",
               "X-Forwarded-Preferred-Username": "Amina Example", "X-Forwarded-Access-Token": "not-a-real-token"}
    app = create_app(engine_for=reading, access=Access(roles, StaticGroups({"5031@1984": ["users", "strata-agency-nwwda"]})),
                     today=lambda: home_story.TODAY)

    async def get(path):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            return await client.get(path, headers=officer)
    answer = asyncio.run(get("/api/home")).json()

    assert (answer["view"], answer["preview"]) == ("piu", False)
    assert sentences(answer) == [
        f"I checked your team's latest Procurement Plan, the plan of October 9, 2026 for the "
        f"{value('project-name-p156634')} (P156634).",
        "Two of its activities are behind their planned dates.", "No draft is waiting for you to check."]
    assert [line["key"] for line in lines(answer)] == ["KE-NWWDA-541055-CW-RFB", "KE-NWWDA-541062-CW-RFQ"]
    assert answer["waiting"]["reason"] is None and answer["start_here"] == {"visible": False, "links": []}
    assert asyncio.run(get("/api/me")).json()["start_here_visible"] is False


def test_the_public_preview_lists_closed_projects_with_the_contracts_traced_and_nothing_private(story):
    """A closed project with no contract has no trail, so the fixture's one closed project with contracts is the line:
    P130164, whose one contract with a STEP reference a notice also carries is the one traced (values.toml,
    counts.p130164_trail)."""
    answer = story.home(view="public").json()
    trail = TRUTH["counts"]["p130164_trail"]

    assert answer["view"] == "public" and answer["start_here"] == {"visible": False, "links": []}
    assert answer["waiting"]["rows"] == []
    assert sentences(answer) == [
        "I hold records for 93 World Bank-financed projects. Search for one by name, project ID or country in the "
        "search box, or start from the one that closed most recently."]
    [line] = lines(answer)
    assert line["kind"] == "public" and line["action"]["href"] == "/projects/P130164/procurement#packages"
    assert text_of(line["segments"]) == (
        f"The {value('project-p130164-name')} (P130164) in {value('project-p130164-country')} closed on "
        f"{long(value('project-p130164-closing'))}. I traced {trail['traced']} of its {trail['contracts']} contracts "
        f"from notice to signature.")
    assert not lines(answer, "lesson") and answer["waiting"]["reason"] == "public"


def test_as_of_a_past_date_the_window_ends_on_it_and_lessons_drafts_and_the_strip_are_left_out(story):
    answer = story.home(asof="2026-10-20").json()

    assert answer["window"]["end"] == "2026-10-20" and answer["as_of"] == "2026-10-20"
    assert lines(answer, "lesson") == [] and answer["waiting"]["reason"] == "asof"
    assert answer["start_here"]["visible"] is False
    assert sentences(answer)[0] == "One plan changed in the 15 days to October 20, 2026."
    assert not any("draft" in sentence for sentence in sentences(answer))


def test_a_plan_that_changed_with_no_activity_marked_never_reads_as_no_plan_changed(story):
    """As of March 25, 2025, the window holds one plan of P156634, Kilifi - Mariakani's of March 19, 2025, and check_plan
    marks none of its activities. "Worth knowing" then says that, never "No plan changed", which the briefing contradicts."""
    answer = story.home(asof="2025-03-25").json()

    assert sentences(answer) == ["One plan changed in the 15 days to March 25, 2025.",
                                 "None of its activities needs a look or is worth watching."]
    assert lines(answer) == [] and answer["worth"]["empty"] == "nothing_marked"


# ── The seed command ─────────────────────────────────────────────────────

def seeded_rows(story) -> list[tuple]:
    with DuckDBEngine.open(story.state_db, read_only=True) as engine:
        return engine.run("SELECT viewer_id, example_key, item_kind, seeded_by FROM strata.ops.seeded_examples "
                          "ORDER BY example_key").rows


def table_count(story, table: str) -> int:
    with DuckDBEngine.open(story.state_db, read_only=True) as engine:
        return int(engine.run(f"SELECT count(*) FROM {table}").rows[0][0])  # sql-lint: names only


def test_the_seed_command_sets_up_every_example_labeled_as_an_example(story):
    rows = seeded_rows(story)

    assert sorted(key for _, key, _, _ in rows) == sorted(EXAMPLE_KEYS)
    assert {(viewer, seeded_by) for viewer, _, _, seeded_by in rows} == {(ANA["X-Forwarded-User"], "strata")}
    assert story.get("/api/projects/P156634/follow").json()["following"] is True
    # The Drafts tab labels each seeded draft an example, as Home does.
    listed = story.get("/api/drafts").json()["groups"]["to_check"]
    assert [row["example"] for row in listed] == [True, True]


def test_every_seeded_item_is_labeled_an_example_where_it_is_listed_and_only_for_its_viewer(story):
    """The 41 brief, 5.12: the follows on Following and the follow control, the package on the Packages tab and in
    its workspace, and each draft on its own page. Ben's own follow of the same project is no example."""
    following = story.get("/api/following").json()["projects"]
    assert {entry["project"]["project_id"]: entry.get("example") for entry in following} == {"P156634": True,
                                                                                            "P130164": True}
    assert story.get("/api/projects/P156634/follow").json() == {"following": True, "example": True}

    [package] = [row for row in story.get("/api/planned-packages").json()["rows"] if row["type"] == "package"]
    assert package["example"] is True
    assert story.get(f"/api/planned-packages/{package['package_id']}").json()["example"] is True

    for row in story.get("/api/drafts").json()["groups"]["to_check"]:
        assert story.get(f"/api/drafts/{row['draft_id']}").json()["example"] is True

    story.call("PUT", "/api/projects/P156634/follow", BEN, json={"view": "staff"})
    assert story.get("/api/projects/P156634/follow", BEN).json() == {"following": True}
    assert [entry.get("example") for entry in story.get("/api/following", BEN).json()["projects"]] == [None]


EXISTING_NOTES = {"kind": "review_notes", "project_id": "P156634",
                  "agency_id": "northern-water-works-development-agency", "plan_date": "2026-10-09"}
EXISTING_ROWS = {"kind": "ppsd_rows", "package": "KE-NWWDA-541055-CW-RFB"}


def test_the_existing_draft_notices_name_a_seeded_draft_an_example_for_its_viewer_alone(story):
    """The plan check the first Start here link opens, and the package workspace, name the open draft the team
    started. For Ana's seeded drafts they say Strata set them up (the 41 brief, 5.12); Ben's view is unchanged."""
    for query in (EXISTING_NOTES, EXISTING_ROWS):
        ana = story.get("/api/drafts/existing", **query).json()["draft"]
        ben = story.get("/api/drafts/existing", BEN, **query).json()["draft"]

        assert (ana["author"]["you"], ana.get("example")) == (True, True), query
        assert ben["draft_id"] == ana["draft_id"] and "example" not in ben, query


def test_running_the_seed_command_twice_sets_up_nothing_twice(story):
    tables = ("strata.ops.seeded_examples", "strata.ops.drafts", "strata.ops.follows",
              "strata.ops.example_lesson_versions")
    before = {table: table_count(story, table) for table in tables}

    report = story.seed()

    assert set(report[ANA_PANELIST.email].values()) == {"already"}
    assert {table: table_count(story, table) for table in tables} == before


def test_an_example_the_viewer_discarded_or_unfollowed_is_not_set_up_again(story):
    notes = next(row for row in story.home().json()["waiting"]["rows"] if row["kind"] == "review_notes")
    assert story.act(notes["draft_id"], "discard", "draft").status_code == 200
    assert story.call("DELETE", "/api/projects/P130164/follow", json={"view": "staff"}).status_code == 200

    story.seed()

    assert [row["kind"] for row in story.home().json()["waiting"]["rows"]] == ["ppsd_rows"]
    assert story.get("/api/projects/P130164/follow").json()["following"] is False


def test_the_example_lesson_change_stays_private_to_its_viewer(story):
    """Ben, Ana's teammate, still gets the lead's version everywhere, and the digest counts no change."""
    ana, ben = story.get("/api/lessons/page").json(), story.get("/api/lessons/page", BEN).json()
    [notice] = ana["notices"]
    lesson_id, a, b = notice["lesson_id"], notice["a"], notice["b"]

    assert notice["example"] is True and (a, b) == (1, 2)
    assert ben["notices"] == []
    for page in (ana, ben):
        card = next(card for card in page["library"]["lessons"] if card["lesson_id"] == lesson_id)
        assert card["version"] == 1 and card["statement"] == notice["statement_a"]
    # The digest counts the lead's versions alone, the same for both.
    assert ana["digest"]["counts"] == ben["digest"]["counts"]
    # The two-versions view opens version 2 for Ana alone.
    assert story.get(f"/api/lessons/{lesson_id}/versions", **{"from": 1, "to": 2}).status_code == 200
    assert story.get(f"/api/lessons/{lesson_id}/versions", BEN, **{"from": 1, "to": 2}).status_code == 404
    assert story.get("/api/evidence", BEN, id=f"versions:{lesson_id}:1:2").status_code == 404
    # get_lessons, which drafts cite, still returns the lead's version 1.
    with DuckDBEngine.open(story.database, read_only=True) as engine:
        versions = engine.run("SELECT max(version) FROM strata.ops.lesson_versions WHERE lesson_id = :lesson_id",
                              {"lesson_id": lesson_id}).rows[0][0]
    assert versions == 1


def test_the_seed_command_sets_up_examples_only_for_the_reviewing_panel(tmp_path):
    roles = tmp_path / "roles.toml"
    roles.write_text((ROOT / "config" / "roles.toml").read_text() + (
        '\n[[people]]\nemail = "ana.example@worldbank.org"\nname = "Ana Example"\ngroups = ["reviewing_panel"]\n'
        'user_id = "4021@1984"\n\n[[people]]\nemail = "cy.example@worldbank.org"\nname = "Cy Example"\n'
        'groups = ["model_owner"]\nuser_id = "4023@1984"\n'))

    assert panel(load_roles(roles), load_examples()) == [ANA_PANELIST]
    assert [kind for kind, _ in plan()] == ["The example"] * 5
    assert CY["X-Forwarded-User"] == "4023@1984"


def test_the_examples_registry_reads_the_showcase_and_demo_plan_from_the_slice_file_and_names_its_mistakes(tmp_path):
    examples = load_examples()
    assert (examples.showcase.project_id, examples.demo_plan.project_id) == ("P130164", "P156634")

    broken = tmp_path / "examples.toml"
    broken.write_text((ROOT / "config" / "examples.toml").read_text().replace("/data\"", "/data/{nowhere}\""))
    with pytest.raises(ConfigError, match="nowhere"):
        load_examples(broken)


# ── The screens' recordings ──────────────────────────────────────────────

def test_the_screens_recorded_answers_are_what_the_routes_answer(built, tmp_path):
    from record_home_api import answers

    for name, text in answers(tmp_path, built=built).items():
        assert (ROOT / "tests" / "fixtures" / "api" / name).read_text() == text, (
            f"{name} is out of date: uv run --frozen python tests/record_home_api.py")
