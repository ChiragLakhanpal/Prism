"""Ticket 88: the App's lean requirements hold every package the server can import.

The Databricks App installs only ops/app/requirements.txt. A package the server imports inside a function is not
needed to start, so the start-up test in test_app_package.py cannot see it missing, and the page that needs it fails
on the deployed App instead. That is how the Packages page answered 500 from its first deploy: the transpile step
that the app-state store runs on Lakebase imports sqlglot, and the list lacked it (py3langid had the same gap before
ticket 66).

So this test reads the code without running it. It starts where the App starts the server and follows every import
through src/strata/, at the top of a module or inside a function, and every strata module that a string names, such
as uvicorn's "strata.server.settings:app_from_env" and each adapter or writer a config registry names. Each package
from outside the standard library that it reaches must be in requirements.txt, unless LEFT_OUT below lists it with
the places that import it, which the App never runs, and why. Nothing is imported from src/strata, and nothing
touches the network.
"""

import ast
import re
import sys
import tomllib
from collections import deque
from functools import cache
from pathlib import Path

from test_app_package import requirements

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"

# app.yaml's command is `python -m strata.server`, which runs strata.server.__main__; the routes are in
# strata.server.app.
STARTS = ("strata.server.__main__", "strata.server.app")
# A string that names a strata module, alone or with one of its functions after a colon, and the quotes around one
# in a source file.
BY_NAME = re.compile(r"(strata(?:\.\w+)+)(?::\w+(?:\.\w+)*)?")
QUOTED = re.compile(r"(?<=[\"'])strata[\w.:]+(?=[\"'])")

# Import names whose package has another name. A namespace package, which several packages share, is named by its
# first two parts.
PACKAGES = {
    "PIL": "pillow",
    "yaml": "pyyaml",
    "opentelemetry": "opentelemetry-api",
    "fpdf": "fpdf2",
    "azure.monitor": "azure-monitor-opentelemetry",
    "databricks.sdk": "databricks-sdk",
}

# Packages the server's code imports only in places the App never runs, so the App does not install them. A place
# is a module, or a module and a function or class after a colon. Keep this list short: a package a page needs
# belongs in requirements.txt.
LEFT_OUT = {
    "duckdb": (("strata.lakehouse.engine:DuckDBEngine",),
               "DuckDB is this computer's engine, for the gate, the fixture build and scripts/dev. On the App the "
               "server reads the SQL warehouse as the viewer and keeps its own state in Lakebase."),
    "xgboost": (("strata.estimates.time_estimate:XGBoostAFT", "strata.estimates.time_estimate:TimeEstimateModel.from_state",
                 "strata.estimates.rebidding_model:RebiddingModel", "strata.estimates.rebidding_model:fit_gbm_model"),
                "The nightly job trains and scores with XGBoost. The App reads a model's trees from XGBoost's JSON "
                "with the portable learner (src/strata/estimates/portable.py), and only the nightly score task asks "
                "from_state for learner='xgboost'."),
    "mlflow": (("strata.estimates.tracking:MlflowTracker", "strata.estimates.tracking:_rebidding_pyfunc"),
               "The nightly job registers its models in MLflow. The App reads them from strata.gold."),
    "pandas": (("strata.estimates.rebidding_model:RebiddingModel.pyfunc_inputs",),
               "Only MLflow's model wrapper, in the nightly job, gives the rebidding model a data frame."),
    "databricks-sdk": (("strata.estimates.tracking:MlflowTracker", "strata.lakehouse.readers:_workspace_transport"),
                       "The nightly job makes MLflow's folder and calls the AI Search index through the SDK. The "
                       "App calls the workspace's REST API itself (strata.lakehouse.engine.http_transport)."),
    "pypdf": (("strata.reader.documents:LiveDocuments", "strata.reader.layout:single_page",
               "strata.fixture.record:pdf_pages"),
              "Only the nightly job's readers and the recording command read a PDF. The App reads the pages they "
              "stored."),
    "splink": (("strata.knowledge.suppliers.matching:candidate_pairs",),
               "Supplier matching runs in the nightly job. The App reads the suppliers it matched from strata.gold."),
    "httpx": (("strata.agent.scripted:stream_text", "strata.agent.scripted:failed_stream_text"),
              "The scripted agent's recording command drives the server inside its own process with httpx. The App "
              "never runs that command."),
}


def normal(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def package(name: str) -> str:
    """The package that installs an imported module, by its longest name in PACKAGES, or else its first part."""
    parts = name.split(".")
    for end in range(len(parts), 0, -1):
        if ".".join(parts[:end]) in PACKAGES:
            return normal(PACKAGES[".".join(parts[:end])])
    return normal(parts[0])


@cache
def source(module: str) -> Path | None:
    """The file that holds a strata module, or None when the name is not a module, such as strata.config.load_slice."""
    base = SRC.joinpath(*module.split("."))
    for path in (base / "__init__.py", base.with_suffix(".py")):
        if path.is_file():
            return path
    return None


def _type_checking(node: ast.stmt) -> bool:
    test = getattr(node, "test", None)
    return isinstance(node, ast.If) and getattr(test, "id", getattr(test, "attr", None)) == "TYPE_CHECKING"


def read(path: Path) -> tuple[list[tuple[str, str]], set[str]]:
    """A file's imports and the strata modules its strings name. Each import is (place, imported name), where place
    is the function or class around the import, or '' at the top. A from-import gives the module and each name after
    it, since a name may be a module too. Imports under `if TYPE_CHECKING:` never run, so they are left out. A string
    counts when its quotes hold a name and nothing else, as "strata.server.settings:app_from_env" does; a docstring
    that mentions a module in a sentence does not."""
    text, found = path.read_text(), []

    def visit(statements, place: str) -> None:
        for node in statements:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(node.body, f"{place}.{node.name}" if place else node.name)
            elif isinstance(node, ast.Import):
                found.extend((place, alias.name) for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                assert not node.level, f"{path} has a relative import, which this test does not follow"
                found.append((place, node.module))
                found.extend((place, f"{node.module}.{alias.name}") for alias in node.names if alias.name != "*")
            elif _type_checking(node):
                visit(node.orelse, place)
            else:  # an import can sit only in a block of statements: an if, a loop, a with, a try or a match
                for block in ("body", "orelse", "finalbody", "handlers", "cases"):
                    visit(getattr(node, block, ()), place)

    visit(ast.parse(text).body, "")
    return found, named(QUOTED.findall(text))


def named(strings) -> set[str]:
    return {match.group(1) for match in map(BY_NAME.fullmatch, strings) if match}


def toml_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from toml_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from toml_strings(item)


@cache
def reached() -> dict[str, dict[str, str]]:
    """Each package outside the standard library that the server can import, with each place that imports it and
    the chain of modules from the server's start to that place."""
    by_config = set().union(*(named(toml_strings(tomllib.loads(path.read_text())))
                              for path in (REPO / "config").glob("*.toml")))
    came_from: dict[str, str | None] = {}
    todo = deque((module, None) for module in (*STARTS, *sorted(by_config)))
    packages: dict[str, dict[str, str]] = {}

    def chain(module: str) -> str:
        names = [module]
        while came_from.get(names[-1]):
            names.append(came_from[names[-1]])
        return " <- ".join(names)

    while todo:
        module, parent = todo.popleft()
        parts = module.split(".")
        for end in range(1, len(parts) + 1):  # importing a.b.c runs a and a.b first
            name = ".".join(parts[:end])
            path = source(name)
            if path is None or name in came_from:
                continue
            came_from[name] = parent
            found, names = read(path)
            todo.extend((other, name) for other in sorted(names) if other not in came_from)
            for place, imported in found:
                top = imported.split(".")[0]
                if top == "strata":
                    todo.append((imported, name))
                elif top not in sys.stdlib_module_names and top != "__future__":
                    site = f"{name}:{place}" if place else name
                    packages.setdefault(package(imported), {}).setdefault(site, chain(name))
    return packages


def _covers(place: str, site: str) -> bool:
    return site == place or site.startswith((f"{place}.", f"{place}:"))


def missing(pins) -> dict[str, list[str]]:
    """The packages the server can import that requirements.txt lacks, each with the places that import it and how
    the server reaches them. A package in LEFT_OUT counts only at the places it names."""
    gaps = {}
    for name, sites in reached().items():
        if name in pins:
            continue
        places = LEFT_OUT.get(name, ((), ""))[0]
        unexplained = [f"{site} (reached as {how})" for site, how in sorted(sites.items())
                       if not any(_covers(place, site) for place in places)]
        if unexplained:
            gaps[name] = unexplained
    return gaps


def test_every_package_the_server_can_import_is_in_the_app_s_lean_requirements():
    gaps = missing(requirements())

    assert not gaps, "ops/app/requirements.txt lacks packages the server imports. Pin each at uv.lock's version, " \
        "or, if the App never runs that place, add it to LEFT_OUT with the reason:\n" + "\n".join(
            f"- {name}, imported at {', '.join(sites)}" for name, sites in sorted(gaps.items()))


def test_the_check_names_sqlglot_when_the_list_lacks_it_as_build_strata_s_did_before_ticket_88():
    """The Packages page's 500 on the deployed App (ModuleNotFoundError: No module named 'sqlglot', from
    src/strata/lakehouse/engine.py's transpile step) is the gap this test is for."""
    pins = {name: version for name, version in requirements().items() if name != "sqlglot"}

    gaps = missing(pins)

    assert list(gaps) == ["sqlglot"]
    assert any(site.startswith("strata.lakehouse.engine:transpile ") for site in gaps["sqlglot"])


def test_each_package_left_out_of_the_app_is_imported_at_the_places_named_and_is_not_in_the_list():
    pins, packages = requirements(), reached()

    for name, (places, _why) in LEFT_OUT.items():
        assert name not in pins, f"{name} is in LEFT_OUT, so the App's lean list should not install it"
        for place in places:
            assert any(_covers(place, site) for site in packages.get(name, {})), \
                f"{place} no longer imports {name}; take it out of LEFT_OUT"
