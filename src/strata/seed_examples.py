"""The seed command: sets up the examples the reviewing panel lands on (ticket 41; the 41 design brief, section 4.5).

    python -m strata.seed_examples [--env-file .env]

For each person in the reviewing panel's group in config/roles.toml (config/examples.toml names the group), it sets up,
through the app's own routes so every example passes the same checks a person's would:

- follows: the demo plan's project (config/slice.toml's [demo_plan]) and the projects config/examples.toml lists;
- review_notes_demo_plan: review notes on the demo plan, in Draft, written by the review notes writer and checked by the
  verifier;
- package_rural_roads_kenya: a package planned from config/examples.toml's sentence;
- ppsd_rows_demo_package: suggested PPSD risk rows for config/examples.toml's package, from its first risks in the
  risk-table builder's order, in Draft, with no risk owner set: Strata never sets one;
- lesson_change: a version of one lesson those rows cite, with a changed wording, that only this viewer sees
  (strata.ops.example_lesson_versions). The library, the Lessons digest and every other viewer keep the lead's version.
  It is set up only when the rows cite a lesson.

Each example is recorded once per viewer in strata.ops.seeded_examples with seeded_by strata, which is how every screen
labels it "Example". Running the command again sets nothing up twice, and an example a viewer discarded or unfollowed is
not set up again, because the record of what was set up is kept apart from the drafts and follows themselves.

Offline, tests/test_home.py runs seed() through tests/home_story.py, on a copy of the fixture with the scripted writers
and the recorded reader. The live run needs the workspace and the Foundry writers (docs/workspace-catchup.md).
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass

import httpx

from strata.config import Examples, Roles, load_examples, load_roles
from strata.knowledge.lessons import notices
from strata.server.home import HomeStore
from strata.lakehouse.clean import agency_id

FOLLOWS = "follows"
REVIEW_NOTES = "review_notes_demo_plan"
PACKAGE = "package_rural_roads_kenya"
PPSD_ROWS = "ppsd_rows_demo_package"
LESSON_CHANGE = "lesson_change"
EXAMPLE_KEYS = (FOLLOWS, REVIEW_NOTES, PACKAGE, PPSD_ROWS, LESSON_CHANGE)


@dataclass(frozen=True)
class Panelist:
    """One person the examples are set up for: the email and user id the Databricks App forwards for them."""

    email: str
    name: str
    user_id: str

    def headers(self) -> dict:
        return {"X-Forwarded-Email": self.email, "X-Forwarded-User": self.user_id,
                "X-Forwarded-Preferred-Username": self.name, "X-Forwarded-Access-Token": "not-a-real-token"}


def panel(roles: Roles, examples: Examples) -> list[Panelist]:
    """The people in the group the examples registry names, each with the user id the roles file gives them."""
    return [Panelist(person.email, person.name, person.user_id) for person in roles.people
            if examples.viewers in person.groups and person.user_id]


def events(text: str) -> list[tuple[str, dict]]:
    """A server-sent event stream's events, as (type, data), without its keep-alive comments."""
    found = []
    for block in text.split("\n\n"):
        lines = [line for line in block.splitlines() if line and not line.startswith(":")]
        if len(lines) >= 2:
            found.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return found


Call = Callable[[str, str, dict, dict | None], httpx.Response]


def asgi_call(app) -> Call:
    """A call of the app's own routes in this process, as the panelist the headers name."""
    def call(method: str, path: str, headers: dict, body: dict | None = None) -> httpx.Response:
        async def go():
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.seed", timeout=600) as client:
                return await client.request(method, path, headers=headers, json=body)
        return asyncio.run(go())
    return call


def _made(response: httpx.Response, kind: str, key: str) -> str | None:
    found = [data.get(key) for name, data in events(response.text) if name == kind]
    return found[0] if found and found[0] else None


def seed_one(call: Call, person: Panelist, examples: Examples, store: HomeStore, drafts, lesson_engine,
             now: Callable[[], dt.datetime]) -> dict[str, str]:
    """Set up every example one person lacks, and say for each what happened: set up, already set up, or why not."""
    done = {row["example_key"]: row for row in store.seeded(person.user_id)}
    said: dict[str, str] = {}
    headers = person.headers()
    plan = examples.demo_plan

    if FOLLOWS in done:
        said[FOLLOWS] = "already"
    else:
        followed = [plan.project_id, *(project for project in examples.follows if project != plan.project_id)]
        for project in followed:
            answer = call("PUT", f"/api/projects/{project}/follow", headers, {"view": "staff"})
            if answer.status_code >= 400:
                raise SeedError(f"I couldn't follow {project} for {person.email}: {answer.status_code} {answer.text}")
        store.seed(person.user_id, FOLLOWS, "follow", ",".join(followed), now())
        said[FOLLOWS] = "set_up"

    if REVIEW_NOTES in done:
        said[REVIEW_NOTES] = "already"
    else:
        answer = call("POST", "/api/drafts", headers, {
            "kind": "review_notes", "project_id": plan.project_id, "agency_id": agency_id(plan.implementing_agency),
            "plan_date": plan.plan_date.isoformat(), "idempotency_key": f"example-{REVIEW_NOTES}", "view": "staff"})
        draft = _made(answer, "draft", "draft_id")
        if draft is None:
            said[REVIEW_NOTES] = "not_written"
        else:
            store.seed(person.user_id, REVIEW_NOTES, "draft", draft, now())
            said[REVIEW_NOTES] = "set_up"

    if PACKAGE in done:
        said[PACKAGE] = "already"
    else:
        sentence = examples.sentences.get("rural_roads_kenya")
        answer = call("POST", "/api/planned-packages", headers, {"sentence": sentence, "view": "staff"})
        package = [data for name, data in events(answer.text) if name == "package"]
        package_id = (package[0].get("package_id") or (package[0].get("package") or {}).get("package_id")) if package else None
        if package_id is None:
            said[PACKAGE] = "not_planned"
        else:
            store.seed(person.user_id, PACKAGE, "package", package_id, now())
            said[PACKAGE] = "set_up"

    ppsd_draft = done[PPSD_ROWS]["item_id"] if PPSD_ROWS in done else None
    if PPSD_ROWS in done:
        said[PPSD_ROWS] = "already"
    else:
        package = examples.ppsd_package
        query = "&".join(f"{key}={value}" for key, value in examples.ppsd_criteria.items())
        table = call("GET", f"/api/packages/{package}/risks?{query}", headers)
        keys = [row["risk_key"] if "risk_key" in row else row["key"] for row in (table.json().get("rows") or [])
                ] if table.status_code == 200 else []
        chosen = keys[:examples.ppsd_risks]
        if not chosen:
            said[PPSD_ROWS] = "no_risks"
        else:
            call("PUT", f"/api/packages/{package}/risk-selection", headers,
                 {"changes": {key: True for key in chosen}, "view": "staff"})
            answer = call("POST", "/api/drafts", headers, {
                "kind": "ppsd_rows", "package": package, "criteria": examples.ppsd_criteria,
                "idempotency_key": f"example-{PPSD_ROWS}", "view": "staff"})
            ppsd_draft = _made(answer, "draft", "draft_id")
            if ppsd_draft is None:
                said[PPSD_ROWS] = "not_written"
            else:
                store.seed(person.user_id, PPSD_ROWS, "draft", ppsd_draft, now())
                said[PPSD_ROWS] = "set_up"

    if LESSON_CHANGE in done:
        said[LESSON_CHANGE] = "already"
    elif ppsd_draft is None:
        said[LESSON_CHANGE] = "no_draft"
    else:
        said[LESSON_CHANGE] = change_a_lesson(person, examples, store, drafts, lesson_engine, ppsd_draft, now)
    return said


def change_a_lesson(person: Panelist, examples: Examples, store: HomeStore, drafts, lesson_engine, draft_id: str,
                    now: Callable[[], dt.datetime]) -> str:
    """The example lesson change: the first lesson the draft cites, at one version after its latest, with the example's
    sentence added to its wording, seen only by this person."""
    saved = drafts.get(draft_id)
    cited = list(notices.citations(saved.content)) if saved is not None else []
    if not cited:
        return "no_lesson_cited"
    _row_key, lesson_id, version = cited[0]
    with lesson_engine() as engine:
        history = notices.history(engine)
    rows = sorted(history.get(lesson_id) or [], key=lambda row: row["version"])
    if not rows:
        return "no_lesson_cited"
    latest = rows[-1]
    moment = now()
    changed = f"{latest['statement']} {examples.lesson_change_sentence}"
    row = {**{key: (value.isoformat() if isinstance(value, dt.date) else value) for key, value in latest.items()},
           "version": latest["version"] + 1, "statement": changed, "state": "current", "change_kind": "wording",
           "was": json.dumps({"statement": latest["statement"]}), "now": json.dumps({"statement": changed}),
           "reason": examples.lesson_change_sentence,
           "item_id": f"example-{lesson_id}", "decided_on": moment.date().isoformat(), "decided_by": "strata",
           "decided_by_name": "Strata", "published_on": None, "days_from_publication": None, "example": True}
    store.add_lesson_version(person.user_id, lesson_id, row["version"], row, moment)
    store.seed(person.user_id, LESSON_CHANGE, "lesson_version", f"{lesson_id}:{version}:{row['version']}", moment)
    return "set_up"


class SeedError(RuntimeError):
    """An example the command could not set up, with why."""


def seed(call: Call, people: list[Panelist], examples: Examples, store: HomeStore, drafts, lesson_engine,
         now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)) -> dict[str, dict[str, str]]:
    """Set up the examples for each person, and say for each person what happened to each example."""
    return {person.email: seed_one(call, person, examples, store, drafts, lesson_engine, now) for person in people}


def plan(examples: Examples | None = None) -> list[tuple[str, str]]:
    """What the command sets up for each panelist, in words, for the demo-ready command's dry run (ticket 48)."""
    examples = examples or load_examples()
    followed = [examples.demo_plan.project_id, *(project for project in examples.follows
                                                 if project != examples.demo_plan.project_id)]
    return [("The example", f"follows on {' and '.join(followed)}"),
            ("The example", f"review notes on the {examples.demo_plan.agency_short_name} plan of "
                            f"{examples.demo_plan.plan_date.isoformat()}"),
            ("The example", f"a package planned from \"{examples.sentences.get('rural_roads_kenya', '')}\""),
            ("The example", f"suggested PPSD risk rows for {examples.ppsd_package}, with no risk owner set"),
            ("The example", "a changed lesson those rows cite, seen only by the panelist")]


def read_env_file(path: str) -> dict[str, str]:
    """KEY=VALUE lines, the way the setup wizard writes them (ops/dayone/dayone.py's load_env)."""
    from pathlib import Path

    values: dict[str, str] = {}
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.removeprefix("export ").strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        values[key] = value
    return values


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None) -> int:
    """Run against the workspace the env file names, as the app's own service principal:

        uv run python -m strata.seed_examples --env-file .env

    The env file's values win over the process's environment (environ, by default os.environ). Each time the platform
    starts the App again it makes the App's service principal a new secret, so the DATABRICKS_CLIENT_SECRET the env
    file holds stops working at the App's next restart (ticket 129). The command then writes as the owner, with the
    env file's DATABRICKS_TOKEN, and says so in one line (strata.server.settings.app_token). The owner owns the catalog
    strata, so writing as the owner needs no grant beyond those the owner already holds. No table the command writes
    has a column for who wrote a row: seeded_by and decided_by say strata, since no person set an example up, and the
    owner shows as the writer only in each table's history (DESCRIBE HISTORY).
    """
    parser = argparse.ArgumentParser(description="Set up the examples the reviewing panel lands on.")
    parser.add_argument("--env-file", help="the env file that names the workspace, as the setup wizard wrote it")
    arguments = parser.parse_args(argv)
    import os
    from contextlib import contextmanager

    from strata.drafts.store import DraftStore
    from strata.server.access import Access, StaticGroups
    from strata.server.settings import _the_app_s_engine, app_from_env

    environ = dict(os.environ if environ is None else environ) | (
        read_env_file(arguments.env_file) if arguments.env_file else {})
    # One engine for the whole run, so the App's secret is tried once and a fallback is said once.
    state = _the_app_s_engine(environ)
    if state is None:
        print("I need the workspace: DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_CLIENT_ID and "
              "DATABRICKS_CLIENT_SECRET, in the env file --env-file names.")
        return 1
    roles, examples = load_roles(), load_examples()
    people = panel(roles, examples)
    if not people:
        print(f"The roles file names no one with a user_id in the group {examples.viewers}, so I set up no examples.")
        return 1

    @contextmanager
    def as_the_app(_viewer=None):
        engine = state()
        try:
            yield engine
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    # The panel are World Bank staff: the app reads their groups from the roles file's [staff], not their tokens.
    access = Access(roles, StaticGroups({person.user_id: list(roles.staff) for person in people}))
    app = app_from_env(environ, engine_for=as_the_app, access=access, the_app=state)
    report = seed(asgi_call(app), people, examples, HomeStore(state), DraftStore(state), as_the_app)
    for email, said in report.items():
        print(f"{email}: " + ", ".join(f"{key} {value.replace('_', ' ')}" for key, value in said.items()) + ".")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
