"""Ticket 84: the app's grant list names every strata.ops table the app writes as itself.

The app writes some tables as its own service principal, which owns no table on a fresh workspace, so it can write
only what grants() in ops/app/deploy_app.py gives it. DuckDB has no grants, so no other offline test sees a table the
list leaves out. On October 26, 2026 the paid workspace refused strata.ops.tool_calls on the app's first answer, and
every run's lineage was lost until the user granted the table by hand.

So these tests read the tables the app writes as itself from the code, not from a list kept by hand:

1. The entry points that build the app's writers (ENTRY_POINTS) take the app's own engine from _the_app_s_engine(),
   in a statement that calls it (the_app = the_app or _the_app_s_engine(environ)), or from a name that falls back on
   it (state = the_app or state_file). Every class built on one of those engines is
   a writer, found in its module through the file's imports. Lakebase (app_state) is left out: its grants are the
   database's own (ADR 0005), not Unity Catalog's.
2. A keyword that gets the engine itself (lesson_record=the_app) hands it to the modules ENGINE_USERS names.
3. A writer's tables are every string in its module that names a strata.ops table or writes one, and every table a
   write statement names in the SQL folder the module reads.

The tests read source files only: nothing is imported from src/strata and nothing touches the network.
"""

import ast
import re
import sys
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
sys.path.insert(0, str(REPO / "ops" / "app"))

import deploy_app  # noqa: E402

PRINCIPAL = "6f1c2d3e-4b5a-4c6d-8e7f-90a1b2c3d4e5"
# Each function that builds the app's writers on its own engine: the server's, and the seed command's (ticket 41).
ENTRY_POINTS = (("strata/server/settings.py", "app_from_env"), ("strata/seed_examples.py", "main"))
# The function that opens the SQL warehouse as the app's own service principal.
THE_APP_S_ENGINE = "_the_app_s_engine"
# The keywords of create_app() that take the app's engine itself, and the modules create_app() hands it to.
ENGINE_USERS = {
    # The lesson review record (ticket 29), and the writer's note that the review page's "Try again" stores again.
    "lesson_record": ("strata.knowledge.lessons.review", "strata.knowledge.lessons.writer"),
    # The retrieval loop (ticket 32): passage reports, the decisions on them, and the judges' queries and grades.
    "feedback_record": ("strata.knowledge.retrieval.reports", "strata.knowledge.retrieval.judging"),
    # The seed command hands the engine it opened to app_from_env (ticket 129), an entry point read on its own.
    "the_app": (),
}
# Tables a writer's module names that the app never writes: the weekly retrieval job writes them as the user who
# deploys (src/strata/knowledge/retrieval/weekly.py calls judging.load, reports.measure and judging.measure with its
# own engine). The app only reads retrieval_feedback_viewers, through its SELECT grant.
WRITTEN_BY_THE_WEEKLY_JOB = frozenset({"strata.ops.retrieval_pool", "strata.ops.retrieval_agreement",
                                       "strata.ops.retrieval_feedback_weekly", "strata.ops.retrieval_feedback_viewers"})

TABLE = re.compile(r"strata\.ops\.[a-z_]+")
WRITE = re.compile(r"\b(?:INSERT\s+INTO|MERGE\s+INTO|UPDATE|DELETE\s+FROM)\s+(strata\.ops\.[a-z_]+)", re.IGNORECASE)
# Where a module reads its SQL: Path(__file__).resolve().parent / "sql" / "home", HERE / "sql" / "home", or
# resources.files("strata.drafts") / "sql".
SQL_FOLDER = re.compile(r'(?:resources\.files\("(?P<package>[\w.]+)"\)|\w+)\s*/\s*"sql"(?:\s*/\s*"(?P<folder>\w+)")?')


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    return next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)


def _imports(tree: ast.Module) -> dict[str, str]:
    """Each name the file imports from strata, anywhere in it, with its module."""
    return {alias.asname or alias.name: node.module for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("strata")
            for alias in node.names}


def _engines(function: ast.FunctionDef) -> set[str]:
    """The names in the function that hold the app's own engine, in the order the function assigns them."""
    names: set[str] = set()
    for statement in function.body:
        if not (isinstance(statement, ast.Assign) and len(statement.targets) == 1
                and isinstance(statement.targets[0], ast.Name)):
            continue
        value = statement.value
        # Such as the_app = _the_app_s_engine(environ), or the_app = the_app or _the_app_s_engine(environ) when a
        # command such as the seed gives the engine it opened (ticket 129).
        opened = any(isinstance(node, ast.Call) and getattr(node.func, "id", None) == THE_APP_S_ENGINE
                     for node in ast.walk(value))
        falls_back = (isinstance(value, ast.BoolOp) and isinstance(value.values[0], ast.Name)
                      and value.values[0].id in names)
        if opened or falls_back:
            names.add(statement.targets[0].id)
    return names


@cache
def writers() -> tuple[frozenset[str], frozenset[str]]:
    """The modules whose classes the entry points build on the app's own engine, and the keywords that take it bare."""
    modules, bare = set(), set()
    for file, name in ENTRY_POINTS:
        tree = ast.parse((SRC / file).read_text())
        function, imports = _function(tree, name), _imports(tree)
        engines = _engines(function)
        assert engines, f"{file}'s {name}() no longer opens the app's engine with {THE_APP_S_ENGINE}()."
        for node in ast.walk(function):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and any(isinstance(argument, ast.Name) and argument.id in engines
                                                           for argument in node.args):
                    modules.add(imports[node.func.id])
                bare |= {keyword.arg for keyword in node.keywords
                         if isinstance(keyword.value, ast.Name) and keyword.value.id in engines}
    return frozenset(modules), frozenset(bare)


def _path(module: str) -> Path:
    return SRC / (module.replace(".", "/") + ".py")


def tables_written_by(module: str) -> set[str]:
    """The strata.ops tables a module names in its code or writes in the SQL folder it reads."""
    path = _path(module)
    text = path.read_text()
    found = set()
    for node in ast.walk(ast.parse(text)):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found |= {node.value} if TABLE.fullmatch(node.value) else set(WRITE.findall(node.value))
    for match in SQL_FOLDER.finditer(text):
        base = SRC / match["package"].replace(".", "/") if match["package"] else path.parent
        for sql in sorted((base / "sql" / (match["folder"] or "")).glob("*.sql")):
            found |= set(WRITE.findall(sql.read_text()))
    return found


@cache
def written_as_the_app() -> frozenset[str]:
    """Every strata.ops table the app writes as its own service principal, read from the code."""
    modules, bare = writers()
    unnamed = sorted(bare - ENGINE_USERS.keys())
    assert not unnamed, f"Name the modules that write with {unnamed} in ENGINE_USERS."
    modules |= {module for keyword in bare for module in ENGINE_USERS[keyword]}
    return frozenset(table for module in modules for table in tables_written_by(module)) - WRITTEN_BY_THE_WEEKLY_JOB


def may_modify(grants: list[str]) -> set[str]:
    """The tables a grant list gives SELECT and MODIFY on."""
    prefix = "GRANT SELECT, MODIFY ON TABLE "
    return {grant.removeprefix(prefix).split()[0] for grant in grants if grant.startswith(prefix)}


def left_out(grants: list[str]) -> list[str]:
    return sorted(written_as_the_app() - may_modify(grants))


def test_the_grant_list_gives_the_app_select_and_modify_on_every_ops_table_it_writes_as_itself():
    assert left_out(deploy_app.grants(PRINCIPAL)) == [], (
        "The app writes these tables as its own service principal, and grants() in ops/app/deploy_app.py gives it "
        "no MODIFY on them, so the workspace would refuse every row. Add them to grants() and its test.")


def test_the_grant_list_gives_modify_on_no_ops_table_the_app_does_not_write():
    """The other way round: no grant outlives its writer, and the reading above found every table the list names."""
    assert sorted(may_modify(deploy_app.grants(PRINCIPAL)) - written_as_the_app()) == []


def test_a_table_the_app_writes_left_out_of_the_grant_list_is_named():
    """The check is not empty: without the run log's tool calls (October 26, 2026), it names that table."""
    without = [grant for grant in deploy_app.grants(PRINCIPAL) if " strata.ops.tool_calls " not in grant]

    assert left_out(without) == ["strata.ops.tool_calls"]


def test_the_writers_are_read_from_the_code_including_the_run_log_and_the_seed_command():
    modules, bare = writers()

    assert {"strata.agent.runs", "strata.estimates.exposures", "strata.server.usage", "strata.drafts.store",
            "strata.server.home"} <= modules
    assert bare == {"lesson_record", "feedback_record", "the_app"}
    assert {"strata.ops.agent_runs", "strata.ops.tool_calls", "strata.ops.tool_call_reads",
            "strata.ops.answer_removals"} <= tables_written_by("strata.agent.runs")
