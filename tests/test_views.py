"""The view switch's rules at seams 2 and 3 (ticket 40): the [views] section of the roles file, applied by the server.

The roles file (config/roles.toml) lists every capability with its kind and its value in each view: World Bank staff
(staff), an implementing agency officer (piu) and the public (public). A person sees their own view, and World Bank
staff may preview the other two. A preview can only take things away: it keeps a capability only where the previewed
view and the person's own view both have it, never one private to a team, and never an act (record, check, export or
draft). These tests read the file people edit, so a line that breaks a rule fails here.
"""

import asyncio
import dataclasses
import datetime as dt
import re
from pathlib import Path

import httpx
import pytest

from strata.config import WRITE_METHODS, load_roles, load_views
from strata.drafts import runtime
from strata.server import views as rules
from strata.server.access import Access, StaticGroups
from strata.server.app import create_app

VIEWS = load_views()
ACTS = ("record", "check", "export", "draft")


def test_each_capability_is_listed_with_its_kind_and_its_value_in_every_view():
    table = {key: (capability.kind, {view: capability.values[view] for view in ("staff", "piu", "public")})
             for key, capability in VIEWS.capabilities.items()}

    # The roles table's rows (the blueprint's "Navigation and roles"; the 40 brief, 5.1), one capability each.
    assert table["packages"] == ("read", {"staff": True, "piu": True, "public": False})
    assert table["following"] == ("read", {"staff": True, "piu": False, "public": False})
    assert table["time_estimates_on_active_projects"] == ("read", {"staff": True, "piu": True, "public": False})
    assert table["signals_on_active_projects"] == ("read", {"staff": True, "piu": True, "public": False})
    assert table["disagreements_on_active_projects"] == ("read", {"staff": True, "piu": True, "public": False})
    assert table["contract_trail"] == ("read", {"staff": True, "piu": True, "public": True})
    assert table["uploads"] == ("read", {"staff": False, "piu": True, "public": False})
    assert table["mark_checked"][0] == "check" and table["export_draft"][0] == "export"
    assert table["upload_and_check"][0] == "check" and table["compare_criteria"][0] == "check"
    assert {kind for kind, _ in table.values()} <= {"read", "setting", *ACTS}


@pytest.mark.parametrize("previewed", ["piu", "public"])
def test_the_agency_and_public_previews_are_subsets_of_the_staff_view(previewed):
    staff = rules.applied(VIEWS, own="staff", requested=None)
    preview = rules.applied(VIEWS, own="staff", requested=previewed)

    assert (preview.view, preview.preview) == (previewed, True)
    assert preview.capabilities < staff.capabilities


def test_the_officers_public_preview_is_a_subset_of_their_own_view_and_of_the_staff_view():
    own = rules.applied(VIEWS, own="piu", requested=None)
    preview = rules.applied(VIEWS, own="piu", requested="public")

    assert preview.capabilities < own.capabilities
    # The officer's own keys private to their team are left out of the comparison with the staff view.
    private = {key for key, capability in VIEWS.capabilities.items() if capability.private}
    assert preview.capabilities <= rules.applied(VIEWS, own="staff", requested=None).capabilities
    assert own.capabilities - private <= rules.applied(VIEWS, own="staff", requested=None).capabilities


def test_the_public_preview_keeps_the_same_from_either_own_view():
    """The guard and keeps() work out a public preview from the staff view alone, whoever is asking
    (src/strata/server/views.py); that holds only while both own views give the public preview the same."""
    assert (rules.applied(VIEWS, own="staff", requested="public").capabilities
            == rules.applied(VIEWS, own="piu", requested="public").capabilities)


@pytest.mark.parametrize("own, previewed", [("staff", "piu"), ("staff", "public"), ("piu", "public")])
def test_no_key_private_to_a_team_and_no_act_is_kept_in_any_preview(own, previewed):
    preview = rules.applied(VIEWS, own=own, requested=previewed)

    for key in preview.capabilities:
        capability = VIEWS.capabilities[key]
        assert not capability.private, key
        assert capability.kind not in ACTS, key
    acts = {key for key, capability in VIEWS.capabilities.items() if capability.kind in ACTS}
    assert acts and not acts & preview.capabilities


def test_each_act_names_the_copy_key_of_the_reason_a_preview_gives():
    for key, capability in VIEWS.capabilities.items():
        if capability.kind in ACTS:
            assert capability.reason and "." in capability.reason, key


def test_who_may_preview_what():
    # World Bank staff see three rows in the popover, an officer two: a preview can only take things away, so an
    # officer can't preview the staff view.
    assert rules.offered(VIEWS, "staff") == ("staff", "piu", "public")
    assert rules.offered(VIEWS, "piu") == ("piu", "public")
    officer_asks_for_staff = rules.applied(VIEWS, own="piu", requested="staff")
    assert (officer_asks_for_staff.view, officer_asks_for_staff.preview, officer_asks_for_staff.problem) == (
        "piu", False, "unknown")
    assert rules.applied(VIEWS, own="piu", requested="piu").preview is False
    assert rules.applied(VIEWS, own="staff", requested="everyone").problem == "unknown"


def test_the_public_view_has_only_projects_lessons_and_data():
    assert VIEWS.views["public"].tabs == ("projects", "lessons", "data")
    assert VIEWS.views["staff"].tabs == ("packages", "projects", "lessons", "drafts", "data")
    assert {"packages", "package", "drafts", "draft", "following"} <= set(VIEWS.views["public"].hidden)
    assert VIEWS.preview_agency == "Northern Water Works Development Agency"


# ── The server applies them (seam 3) ─────────────────────────────────────

ROOT = Path(__file__).resolve().parents[1]
TODAY = dt.date(2026, 10, 23)
STAFF = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
         "X-Forwarded-Access-Token": "token-for-ana-only"}
OFFICER = {"X-Forwarded-Email": "amina.example@worldbank.org", "X-Forwarded-User": "5031@1984",
           "X-Forwarded-Access-Token": "token-for-amina-only"}
GROUPS = {"4021@1984": ["users"], "5031@1984": ["users", "strata-agency-nwwda"]}


def roles():
    """config/roles.toml, with the test roles file's implementing agency teams."""
    real = load_roles()
    return dataclasses.replace(real, teams=real.teams + load_roles(ROOT / "tests" / "fixtures" / "roles.toml").teams)


def server():
    return create_app(engine_for=None, access=Access(roles(), StaticGroups(GROUPS)), today=lambda: TODAY)


def call(app, method, path, headers, **options):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.request(method, path, headers=headers, **options)
    return asyncio.run(go())


def test_every_write_route_declares_the_capability_it_needs():
    app = server()
    routes = [(method, route.path) for route in app.routes for method in getattr(route, "methods", None) or ()]
    missing = [f"{method} {path}" for method, path in routes
               if method in WRITE_METHODS and VIEWS.route(method, path) is None]

    assert missing == []
    # A draft's act depends on its action: each action the runtime knows has its capability.
    acts = VIEWS.route("POST", "/api/drafts/{draft_id}/{action}")
    assert {action: acts.needs({"action": action}) for action in runtime.ACTIONS} == {
        "check": "mark_checked", "export": "export_draft", "discard": "discard_draft", "restore": "discard_draft"}
    # And every line in [views.routes] names a route the server has.
    assert sorted(set(VIEWS.routes) - {f"{method} {path}" for method, path in routes}) == []


def addresses(kinds: tuple[str, ...]) -> list[tuple[str, str, str]]:
    """Each route whose capability is of these kinds, as (method, an address with stand-in path values, capability),
    with one address per draft action."""
    found = []
    for route, rule in VIEWS.routes.items():
        method, path = route.split(" ", 1)
        for action in (rule.by_value if rule.param else [None]):
            capability = rule.needs({"action": action})
            if VIEWS.capabilities[capability].kind in kinds:
                address = re.sub(r"\{(\w+)(?::path)?\}", lambda part: action if part.group(1) == "action" else "x1", path)
                found.append((method, address, capability))
    return sorted(found)


CHECKS_AND_EXPORTS = addresses(("check", "export"))


@pytest.mark.parametrize("view", ["piu", "public"])
@pytest.mark.parametrize("method, address, capability", CHECKS_AND_EXPORTS)
def test_a_preview_refuses_every_check_and_export_route_with_its_capability_and_reason(method, address, capability,
                                                                                      view):
    refused = call(server(), method, address, STAFF, params={"view": view}, json={"expected_state": "draft"})

    assert refused.status_code == 403
    assert refused.json() == {"code": "preview", "error": "preview", "capability": capability,
                              "copy_key": VIEWS.capabilities[capability].reason, "view": view}


def test_the_check_and_export_routes_are_marking_as_checked_exporting_uploading_and_comparing():
    assert {capability for _, _, capability in CHECKS_AND_EXPORTS} == {
        "mark_checked", "export_draft", "upload_and_check", "compare_criteria"}


def test_a_preview_named_in_the_body_is_a_preview_too():
    refused = call(server(), "POST", "/api/drafts/draft-1/export", STAFF, json={"expected_state": "checked", "view": "piu"})

    assert (refused.status_code, refused.json()["capability"]) == (403, "export_draft")


def test_a_preview_leaves_out_a_quiet_record_and_hides_a_page_it_does_not_keep():
    app = server()

    opened = call(app, "POST", "/api/evidence/opened", STAFF, params={"view": "public"}, json={"evidence_id": "a:b"})
    following = call(app, "GET", "/api/following", STAFF, params={"view": "piu"})
    package = call(app, "GET", "/api/packages/KE-NWWDA-541062-CW-RFQ", STAFF, params={"view": "public"})

    assert (opened.status_code, opened.json()) == (200, {"recorded": False})
    assert (following.status_code, following.json()) == (404, {"code": "not_in_view", "error": "not_in_view",
                                                               "capability": "following", "view": "piu"})
    assert (package.status_code, package.json()["capability"]) == (404, "packages")


def test_who_is_viewing_says_which_view_and_date_the_server_applied():
    app = server()

    own = call(app, "GET", "/api/me", STAFF).json()
    public = call(app, "GET", "/api/me", STAFF, params={"view": "public", "asof": "2016-08-26"}).json()
    officer = call(app, "GET", "/api/me", OFFICER, params={"view": "piu"}).json()
    unknown = call(app, "GET", "/api/me", STAFF, params={"view": "everyone", "asof": "October-22"}).json()
    today = call(app, "GET", "/api/me", STAFF, params={"asof": TODAY.isoformat()}).json()

    assert (own["own_view"], own["views"], own["applied"]) == (
        "staff", ["staff", "piu", "public"], {"view": "staff", "preview": False, "problem": None})
    assert own["tabs"] == ["packages", "projects", "lessons", "drafts", "data"] and own["hidden"] == []
    assert own["preview_agency"] == {"name": "Northern Water Works Development Agency", "short_name": "NWWDA",
                                     "agency_id": "northern-water-works-development-agency"}
    assert public["applied"] == {"view": "public", "preview": True, "problem": None}
    assert public["tabs"] == ["projects", "lessons", "data"] and "packages" in public["hidden"]
    assert public["asof"] == {"applied": "2016-08-26", "problem": None}
    assert "export_draft" not in public["capabilities"] and "contract_trail" in public["capabilities"]
    assert public["reasons"]["export_draft"] == "draft.bar.hold.preview"
    assert (officer["own_view"], officer["views"], officer["applied"]["preview"]) == ("piu", ["piu", "public"], False)
    assert unknown["applied"] == {"view": "staff", "preview": False, "problem": "unknown"}
    assert unknown["asof"] == {"applied": None, "problem": "unreadable"}
    assert today["asof"] == {"applied": None, "problem": "not_past"}


def test_who_is_viewing_lists_the_box_suggestions_for_staff_in_their_own_view_and_none_in_a_preview_or_as_of_a_date():
    """Ticket 112: the box suggests config/examples.toml's [[ask]] rows only where no view holds back their answers."""
    app = server()

    own = call(app, "GET", "/api/me", STAFF).json()["ask"]
    previews = [call(app, "GET", "/api/me", STAFF, params=params).json()["ask"]
                for params in ({"view": "piu"}, {"view": "public"}, {"asof": "2016-08-26"})]
    officer = call(app, "GET", "/api/me", OFFICER).json()["ask"]

    assert own[:1] + own[-2:] == [{"key": "pastRange", "page": "package", "within": None},
                                  {"key": "pastRange", "page": "home", "within": "KE-NWWDA-541055-CW-RFB"},
                                  {"key": "worksRebidding", "page": "home", "within": "P130164"}]
    assert [row["page"] for row in own] == ["package"] * 3 + ["project"] * 2 + ["plan_check"] + ["home"] * 2
    assert previews == [[], [], []]
    # An implementing agency officer's own view is not World Bank staff's.
    assert officer == []


def test_your_agencys_projects_lists_each_disclosed_plan_with_its_check(fixture_db):
    # The roles table's "Your agency's projects, with signals against your own plan" (the 40 brief, 3.8): the projects
    # where the agency has a disclosed Procurement Plan, each with check_plan's counts on the latest plan. In the
    # fixture the Northern Water Works Development Agency has plans only for P156634 (the plan of October 9, 2026,
    # whose marks the benchmark question check-plan-nwwda-2026-10-09 gives: one needs a look, two worth watching).
    from contextlib import contextmanager

    from strata.lakehouse.engine import DuckDBEngine

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(engine_for=reading, access=Access(roles(), StaticGroups(GROUPS)), today=lambda: TODAY)

    preview = call(app, "GET", "/api/agency/projects", STAFF, params={"view": "piu"}).json()
    officer = call(app, "GET", "/api/agency/projects", OFFICER).json()
    before = call(app, "GET", "/api/agency/projects", OFFICER, params={"asof": "2016-08-26"}).json()
    staff = call(app, "GET", "/api/agency/projects", STAFF)
    public = call(app, "GET", "/api/agency/projects", STAFF, params={"view": "public"})

    assert preview == officer
    assert preview["agency"]["name"] == "Northern Water Works Development Agency"
    assert [(item["project_id"], item["plan"]["plan_date"], item["counts"]["needs_a_look"], item["counts"]["watch"])
            for item in preview["projects"]] == [("P156634", "2026-10-09", 1, 2)]
    assert (before["state"], before["projects"]) == ("none", [])
    assert (staff.status_code, public.status_code) == (404, 404)


def test_the_view_switchs_recorded_answers_are_what_the_server_answers(fixture_db):
    from record_views_api import answers

    for name, text in answers(fixture_db).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), (
            f"{name} is out of date: uv run --frozen python tests/record_views_api.py")


def test_an_officers_own_view_is_not_a_preview_but_their_public_preview_is():
    app = server()

    own = call(app, "POST", "/api/drafts/draft-1/check", OFFICER, params={"view": "piu"}, json={"expected_state": "draft"})
    preview = call(app, "POST", "/api/drafts/draft-1/check", OFFICER, params={"view": "public"},
                   json={"expected_state": "draft"})

    assert own.json().get("code") != "preview"
    assert (preview.status_code, preview.json()["view"]) == (403, "public")


class ThreadNoted(StaticGroups):
    """StaticGroups that notes the thread each read of a viewer's groups ran on: in production that read is a
    request to the workspace's SCIM API (strata.server.access.WorkspaceGroups)."""

    def __init__(self, groups):
        super().__init__(groups)
        self.threads = []

    def groups(self, viewer):
        import threading
        self.threads.append(threading.get_ident())
        return super().groups(viewer)


def test_asking_who_the_viewer_is_never_blocks_the_server_loop():
    """ViewParams and the guard ask whether a viewer is an officer for every request in the agency preview. They run on
    the server's event loop, so the workspace call behind that question runs on a worker thread, and a slow workspace
    can't stall an answer that is streaming to someone else."""
    import threading

    noted = ThreadNoted(GROUPS)
    app = create_app(engine_for=None, access=Access(roles(), noted), today=lambda: TODAY)
    loop_threads = []

    async def go():
        loop_threads.append(threading.get_ident())
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            await client.post("/api/drafts/draft-1/check", headers=OFFICER, params={"view": "piu"},
                              json={"expected_state": "draft", "view": "piu"})

    asyncio.run(go())
    assert noted.threads and loop_threads[0] not in noted.threads
