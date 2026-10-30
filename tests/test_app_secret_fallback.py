"""The scripts that write as the App fall back to the owner's token when the App's secret is gone (ticket 129).

Each time Databricks Apps stops the App and it starts again, the platform makes the App's service principal a new OAuth
secret, and the one in the env file stops working: on October 28 and 29, 2026 the seed command and the demo-ready
command's Home step failed with "The workspace gave the app no token: HTTP Error 401: Unauthorized". The App itself is
unaffected, since the platform gives it its secret. A script that writes as the App tries the App's client id and
secret once, and when the token endpoint refuses them it writes with the owner's token (DATABRICKS_TOKEN, as every
other ops script does) and says so in one line.

The workspace is tests/fake_warehouse.py's: a token endpoint that hands the App a token or refuses it, and a SQL
warehouse that keeps the token each statement carried. The live proof is a workspace step (docs/workspace-catchup.md).
"""

import asyncio
import contextlib
import importlib.util
import io
import shutil
import sys
from pathlib import Path

import fake_warehouse
import httpx
import pytest

from strata import seed_examples
from strata.config import load_examples, load_roles
from strata.dbx import Viewer
from strata.server.engines import duckdb_file
from strata.server.settings import app_from_env

ROOT = Path(__file__).resolve().parents[1]

# The line the ticket gives, word for word.
FALLBACK = "The App's secret is gone since the platform restarted the App; writing as the owner instead."
OWNER = "owner-not-a-real-key"
ANA = {"X-Forwarded-Email": "ana.example@worldbank.org", "X-Forwarded-User": "4021@1984",
       "X-Forwarded-Access-Token": "token-for-ana-only"}


def environment(host: str, **more) -> dict:
    """The env file a script reads: the workspace, the App's client id and secret, and the owner's token."""
    return {"DATABRICKS_HOST": host, "DATABRICKS_WAREHOUSE_ID": "wh-1", "DATABRICKS_CLIENT_ID": "strata-app",
            "DATABRICKS_CLIENT_SECRET": "not-a-real-key", "DATABRICKS_TOKEN": OWNER, **more}


def visit(app, *paths):
    async def go():
        async with app.router.lifespan_context(app):
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
                return [await client.get(path, headers=ANA) for path in paths]
    return asyncio.run(go())


def written(calls, table: str) -> list[str]:
    """The token each statement that names the table carried."""
    return [call[1] for call in calls if call[0] == "statement" and table in call[2]]


def test_when_the_workspace_refuses_the_app_s_secret_the_rows_go_with_the_owner_s_token_and_one_line_says_so(capsys):
    with fake_warehouse.workspace(token_status=401) as (host, calls):
        app = app_from_env(environment(host))
        visit(app, "/api/freshness", "/api/health")

    assert written(calls, "strata.ops.usage_events") == [f"Bearer {OWNER}"]
    # The App's client id and secret were tried once, and never again once refused.
    assert len([call for call in calls if call[0] == "token"]) == 1
    assert capsys.readouterr().out.splitlines().count(FALLBACK) == 1


def test_when_the_app_s_secret_works_the_rows_go_with_the_app_s_token_and_nothing_is_said(capsys):
    with fake_warehouse.workspace() as (host, calls):
        app = app_from_env(environment(host))
        visit(app, "/api/freshness", "/api/health")

    assert written(calls, "strata.ops.usage_events") == [f"Bearer {fake_warehouse.APP_TOKEN}"]
    assert not [call for call in calls if call[1] == f"Bearer {OWNER}"]
    assert FALLBACK not in capsys.readouterr().out


def test_on_the_app_which_has_no_owner_s_token_a_refused_secret_is_still_an_error(capsys):
    """The platform gives the App its own secret and no DATABRICKS_TOKEN, so the App never writes as a person."""
    environ = environment("")
    del environ["DATABRICKS_TOKEN"]
    with fake_warehouse.workspace(token_status=401) as (host, calls):
        app = app_from_env({**environ, "DATABRICKS_HOST": host})
        visit(app, "/api/freshness", "/api/health")

    # The usage log did try to write, so the secret was asked for and refused.
    assert [call[0] for call in calls].count("token") == 1
    assert written(calls, "strata.ops.usage_events") == []
    assert FALLBACK not in capsys.readouterr().out


def test_on_the_app_a_refused_secret_is_an_error_even_when_its_environment_holds_a_person_s_token(capsys):
    """CLAUDE.md rule 7: the App writes its own rows with its own token. The platform sets DATABRICKS_APP_PORT on the
    App (ops/app/app.yaml), so a DATABRICKS_TOKEN that a later deploy gave the App is never a fallback there."""
    with fake_warehouse.workspace(token_status=401) as (host, calls):
        app = app_from_env(environment(host, DATABRICKS_APP_PORT="8000"))
        visit(app, "/api/freshness", "/api/health")

    assert [call[0] for call in calls].count("token") == 1
    assert not [call for call in calls if call[1] == f"Bearer {OWNER}"]
    assert FALLBACK not in capsys.readouterr().out


def test_a_token_endpoint_that_fails_for_another_reason_is_an_error_not_a_fallback(capsys):
    with fake_warehouse.workspace(token_status=503) as (host, calls):
        app = app_from_env(environment(host))
        visit(app, "/api/freshness", "/api/health")

    assert [call[0] for call in calls].count("token") == 1
    assert written(calls, "strata.ops.usage_events") == []
    assert FALLBACK not in capsys.readouterr().out


# ── The seed command (ticket 41), on a copy of the fixture database ──────

def env_file(folder, host: str):
    """The env file as the setup wizard writes it: KEY=VALUE lines."""
    path = folder / "workspace-env"
    path.write_text("".join(f"{key}={value}\n" for key, value in environment(host).items()))
    return path


def seed_on_the_fixture(fixture_db, folder, token_status: int):
    """One run of python -m strata.seed_examples --env-file, against a workspace whose warehouse is a copy of the
    fixture database: its exit code, what it printed, and the workspace's calls."""
    database = folder / "workspace.duckdb"
    shutil.copyfile(fixture_db, database)
    out = io.StringIO()
    with fake_warehouse.workspace(database, token_status=token_status) as (host, calls):
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            code = seed_examples.main(["--env-file", str(env_file(folder, host))], environ={})
    return code, out.getvalue(), calls


def demo_ready():
    """ops/demo/ready.py, by its path, under the name tests/test_demo_ready.py loads it by: the ops folders are not a
    package."""
    if "strata_demo_ready" not in sys.modules:
        spec = importlib.util.spec_from_file_location("strata_demo_ready", ROOT / "ops" / "demo" / "ready.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules["strata_demo_ready"] = module
        spec.loader.exec_module(module)
    return sys.modules["strata_demo_ready"]


class SeedingWorkspace:
    """The demo-ready command's workspace as its Home step uses it: seed() runs the seed command, here in this process
    as ops/demo/demo_live.py's LiveDemo.seed runs it in a subprocess, and gives its exit code and what it printed; the
    SQL warehouse the step reads the data-through date from is the fixture database."""

    def __init__(self, fixture_db, folder, token_status: int):
        self.fixture_db, self.folder, self.token_status = fixture_db, folder, token_status
        self.viewer = Viewer(email="ana.example@worldbank.org", name="Ana Example", user_id="ana", token=OWNER)
        self.engine_for = duckdb_file(fixture_db)
        self.seeded = None

    def seed(self):
        self.seeded = seed_on_the_fixture(self.fixture_db, self.folder, self.token_status)
        code, out, _calls = self.seeded
        return code, out.strip()


@pytest.fixture(scope="module", params=[200, 401], ids=["secret works", "secret refused"])
def home(request, fixture_db, tmp_path_factory):
    """The demo-ready command's Home step, run once each way: the workspace, what the step said, and its outcome."""
    ready = demo_ready()
    workspace = SeedingWorkspace(fixture_db, tmp_path_factory.mktemp("seed"), request.param)
    said: list[str] = []
    outcome = ready.home_step(workspace, ready.Setup(fixture_db=fixture_db, seed_command=lambda: True), said.append,
                              kept={})
    return workspace, said, outcome


@pytest.fixture
def seeded(home):
    workspace, _said, _outcome = home
    return workspace.token_status, *workspace.seeded


def test_the_seed_command_sets_up_the_panel_s_follows_both_ways_with_the_token_that_worked(seeded):
    token_status, code, out, calls = seeded
    people = seed_examples.panel(load_roles(), load_examples())

    assert code == 0, out
    assert people
    for person in people:
        assert f"{person.email}: follows set up" in out
    writer = f"Bearer {OWNER}" if token_status == 401 else f"Bearer {fake_warehouse.APP_TOKEN}"
    assert set(written(calls, "INSERT INTO strata.ops.seeded_examples")) == {writer}
    assert set(written(calls, "INSERT INTO strata.ops.follows")) == {writer}


def test_the_seed_command_says_the_fallback_once_only_when_the_secret_was_refused(seeded):
    token_status, _code, out, calls = seeded

    assert out.splitlines().count(FALLBACK) == (1 if token_status == 401 else 0)
    # The App's client id and secret are tried once in the whole run, even though the run opens many engines.
    assert len([call for call in calls if call[0] == "token"]) == 1


class FailingSeed:
    """A workspace whose seed command fell back to the owner's token and then failed with a long error."""

    ERROR = ("EngineError: The SQL warehouse refused the statement: " + "PERMISSION_DENIED on strata.ops.follows. " * 7
             + "That is the end of the real error.")

    def seed(self):
        return 1, f"{FALLBACK}\n{self.ERROR}"


def test_when_the_seed_fails_after_the_fallback_the_home_step_keeps_the_whole_error_and_still_names_the_fallback():
    ready = demo_ready()
    said: list[str] = []

    outcome = ready.home_step(FailingSeed(), ready.Setup(seed_command=lambda: True), said.append, kept={})

    assert outcome.state == ready.FAILED
    assert outcome.summary == f"The seed command failed: {FailingSeed.ERROR}"
    assert f"   {FALLBACK}" in said


def test_the_demo_ready_command_s_home_step_passes_both_ways_and_names_the_fallback_only_when_it_happened(home):
    workspace, said, outcome = home

    assert outcome.state == demo_ready().PASSED, said
    assert "   I ran python -m strata.seed_examples for the reviewing panel's group. It makes only the examples that " \
           "are missing." in said
    if workspace.token_status == 401:
        assert f"   {FALLBACK}" in said
        assert outcome.summary == "The examples are seeded, as the owner, and the window is checked."
    else:
        assert not [line for line in said if FALLBACK in line]
        assert outcome.summary == "The examples are seeded and the window is checked."
