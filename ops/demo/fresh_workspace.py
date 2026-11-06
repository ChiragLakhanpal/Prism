"""The demo-ready command's dry run (ticket 48): how a fresh workspace reaches the demo state, from code alone.

ops/demo/ready.py --fresh-workspace prints it. It changes nothing, reaches no service and needs no env file. Each
resource comes from its own deployer's plan, so this list cannot drift from them:

- the bundle: ops/bundle/deploy.py's plan(), from databricks.yml, bundle/*.yml and the table, view and metric view
  definitions in src/strata/lakehouse (ticket 04, with ticket 33's metric views)
- the AI Search endpoint and index: the endpoint ops/dayone/dayone.toml names, which the wizard's AI Search probe
  makes, and the index config/models.toml names, which the nightly job's sync_index task makes over
  strata.gold.passage (tickets 11 and 43)
- the app: ops/app/deploy_app.py's plan() (ticket 06)
- the Genie space: config/genie.toml, as strata.genie.space reads it for ops/genie/deploy_space.py (ticket 33)
- the Foundry agents: strata.agent.sync.plan(), from config/agents.toml (ticket 13)
- the examples for the reviewing panel: ticket 41's seed command, python -m strata.seed_examples, through its plan()
  once it has one

The order is the order to run them in: the bundle first, since everything else reads its catalog; the Genie space
before the app, because the space deploy saves Prism's space id in the env file and the app deploy writes that id
into app.yaml; the app before the nightly job's first run, because the app deploy saves the Azure keys the job's
tasks read from the secret scope.
"""

from __future__ import annotations

import importlib
import importlib.util
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle", REPO / "ops" / "app"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402
import deploy as bundle_deploy  # noqa: E402  (ops/bundle/deploy.py)
import deploy_app  # noqa: E402  (ops/app/deploy_app.py)

from strata.agent import sync  # noqa: E402
from strata.config import load_search  # noqa: E402
from strata.genie import space as genie_space  # noqa: E402
from strata.knowledge.search import SOURCE_TABLE  # noqa: E402

SEED_MODULE = "strata.seed_examples"


@dataclass
class Planned:
    """One deployer: what it is, the command that runs it, and what it makes. command is None when no code makes
    it yet, and missing then says which ticket adds it."""

    what: str
    command: str | None
    made: list[str]
    missing: str | None = None


def _counted(kinds: list[tuple[str, str]], kind: str, noun: str) -> str:
    names = [name for found, name in kinds if found == kind]
    return f"{dayone.count_words(len(names), noun)}: {', '.join(names)}"


def bundle() -> Planned:
    planned = bundle_deploy.plan()
    tables = [name for kind, name in planned if kind == "tables"]
    by_schema: dict[str, int] = {}
    for name in tables:
        schema = ".".join(name.split(".")[:2])
        by_schema[schema] = by_schema.get(schema, 0) + 1
    catalog = next(name for kind, name in planned if kind == "catalog")
    return Planned("The bundle", "uv run --script ops/bundle/deploy.py --env-file .env", [
        f"The catalog {catalog}",
        f"The {_counted(planned, 'schemas', 'schema')}",
        f"The {_counted(planned, 'volumes', 'volume')}",
        f"{dayone.count_words(len(tables), 'table')}, views and metric views: "
        + ", ".join(f"{count} in {schema}" for schema, count in by_schema.items()),
        f"The grants on {dayone.count_words(sum(1 for kind, _ in planned if kind == 'grants'), 'securable')}",
        f"The {_counted(planned, 'jobs', 'job')}",
        f"The {_counted(planned, 'dashboards', 'dashboard')}"])


def endpoint() -> Planned:
    name = dayone.load_config()["names"]["ai_search_endpoint"]
    return Planned("The AI Search endpoint", "uv run --script ops/dayone/probe_ai_search.py --env-file .env",
                   [f"The endpoint {name}, which AI_SEARCH_ENDPOINT in the env file names"])


def first_run() -> Planned:
    name = dayone.load_config()["names"]["ai_search_endpoint"]
    return Planned("The nightly job's first run, which fills the tables and makes the index",
                   "uv run --script ops/bundle/check.py job-run --env-file .env",
                   ["The rows of bronze, silver, gold and ops, from the sources in config/sources.toml",
                    f"The Delta Sync index {load_search().index} over {SOURCE_TABLE}, on the endpoint {name}"])


def app() -> Planned:
    grouped: dict[str, list[str]] = {}
    for what, name in deploy_app.plan():
        grouped.setdefault(what, []).append(name)
    return Planned("The app, which also saves the Azure keys the nightly job reads",
                   "uv run --script ops/app/deploy_app.py --env-file .env",
                   [f"{what if len(names) == 1 else what + 's'}: {', '.join(names)}" for what, names in grouped.items()])


def genie() -> Planned:
    space = genie_space.load()
    return Planned("The Genie space", "uv run python ops/genie/deploy_space.py --env-file .env",
                   [f"The space \"{space.title}\", reading {', '.join(genie_space.reads(space))}, with "
                    f"{dayone.count_words(len(space.trusted), 'trusted question')} and "
                    f"{dayone.count_words(len(space.benchmarks), 'benchmark question')}"])


def agents() -> list[Planned]:
    return [Planned(f"The Foundry agent {key}", f"uv run --script ops/agent/sync.py --env-file .env --agent {key}", [made])
            for key, made in sync.plan()]


def seed_plan() -> list[tuple[str, str]] | None:
    """Ticket 41's seed command's plan, or None while it has none."""
    if importlib.util.find_spec(SEED_MODULE) is None:
        return None
    found = getattr(importlib.import_module(SEED_MODULE), "plan", None)
    return found() if callable(found) else None


def examples(seeds: list[tuple[str, str]] | None) -> Planned:
    what = "The examples for the reviewing panel"
    if seeds is None:
        return Planned(what, None, [], f"Ticket 41 adds python -m {SEED_MODULE}.")
    return Planned(what, f"uv run python -m {SEED_MODULE} --env-file .env", [f"{kind}: {name}" for kind, name in seeds])


def show(say: Callable[[str], None] = print, seeds: list[tuple[str, str]] | None = None) -> int:
    planned = [bundle(), endpoint(), genie(), app(), first_run(), *agents(),
               examples(seeds if seeds is not None else seed_plan())]
    say("How a fresh workspace reaches the demo state, from code alone. I changed nothing.")
    say("First the wizard fills the env file, because tokens and sign-ins are yours: bash ops/wizard/strata-setup.sh")
    for number, step in enumerate(planned, 1):
        if step.command is None:
            say(f"{number}. {step.what}: no deployer yet. {step.missing}")
            continue
        say(f"{number}. {step.what}: {step.command}")
        for made in step.made:
            say(f"   - {made}")
    say(f"{len(planned) + 1}. Then make it ready: uv run --with databricks-sdk==0.156.0 python ops/demo/ready.py --env-file .env")
    missing = [step.what[0].lower() + step.what[1:] for step in planned if step.command is None]
    if len(missing) == 1:
        say(f"One resource has no deployer yet, so a fresh workspace still needs it: {missing[0]}.")
        return 1
    if missing:
        count = dayone.count_words(len(missing), "resource")
        say(f"{count[0].upper()}{count[1:]} have no deployer yet, so a fresh workspace still needs them: "
            f"{', '.join(missing)}.")
        return 1
    say("Every resource above deploys from code, with no manual step.")
    return 0
