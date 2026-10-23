#!/usr/bin/env python3
"""The SQL lint, a gate step: every query names its tables in three parts and binds its values.

Strata's SQL runs on the workspace and on DuckDB, as each viewer, so two rules hold everywhere
(docs/agents/areas/data.md; spec, "Security and privacy"):

1. Every table is named in three parts, in the strata catalog: strata.<schema>.<table> (or
   system.information_schema.<x>). A name defined in the same query, by WITH, needs no parts.
2. Every value is a bound :name parameter. Code never builds a value into a query's text. A query
   whose text code does build, from table or column names only, says so on any line of the
   statement that builds it with the comment `# sql-lint: names only`, so a reviewer can check
   that claim in one place.

It reads every .sql file under src/strata and tests/ground_truth, and the Python under src/strata
and ops/bundle: every string that holds a query, wherever it is written (passed to run(),
execute(), executemany() or sql(), held in a variable or a constant, or returned), and every
query text that code builds with an f-string, + or %, += or %=, .format() or .replace(), or by
joining a list or tuple whose first item is a query (" ".join([...])). A built query may
start from a string written right there or from a name any of those files gives a query
(QUERY = "SELECT ..."), read bare or through its module (queries.QUERY), as this repo writes its
queries as named constants. A string is a query when it starts the way a statement does
(QUERY_START): a SELECT, an INSERT or MERGE into a table, a WITH clause, a CREATE of a table, view
or schema, a DELETE, or an UPDATE that sets columns.

Two places are left out on purpose: gates/, whose fixture build loads the fixture's own copy of
the sources into schemas of its own, and ops/dayone, ticket 03's day-one probes, which run once on
the workspace's own catalog and bind each name with IDENTIFIER(:name).

    uv run --frozen python gates/sql_lint.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ROOT = Path(__file__).resolve().parents[1]
SQL_FOLDERS = ("src/strata", "tests/ground_truth")
PYTHON_FOLDERS = ("src/strata", "ops/bundle")
QUERY_CALLS = {"run", "execute", "executemany", "sql"}
QUERY_START = re.compile(r"(SELECT|INSERT\s+INTO|MERGE\s+INTO|WITH\s+\w+\s+AS\s*\(|CREATE\s+(OR\s+REPLACE\s+)?"
                         r"(TABLE|VIEW|SCHEMA)|DELETE\s+FROM|UPDATE\s+\S+\s+SET)\b", re.I)
CATALOGS = ("strata", "system")
NAMES_ONLY = "# sql-lint: names only"
BUILT = ("this query's text is built in code. Bind each value as a :name parameter; a query that builds in only "
         f"table or column names says so with '{NAMES_ONLY}'.")


def _is_query(text: str) -> bool:
    lines = [line for line in text.strip().splitlines() if not line.strip().startswith("--")]
    return bool(lines) and bool(QUERY_START.match(lines[0].lstrip()))


def _name_problems(sql: str, where: str, unreadable: bool = True) -> list[str]:
    """Each table the SQL names in fewer than three parts, or outside the strata catalog. SQL that
    does not parse is reported when unreadable is true, and is taken for ordinary text otherwise."""
    try:
        statements = [statement for statement in sqlglot.parse(sql, read="databricks") if statement is not None]
    except ParseError as error:
        return [f"{where}: I could not read this SQL to check it: {str(error).splitlines()[0]}"] if unreadable else []
    problems = []
    for statement in statements:
        defined = {cte.alias_or_name for cte in statement.find_all(exp.CTE)}
        for table in statement.find_all(exp.Table):
            if not table.name or (not table.db and table.name in defined):
                continue
            name = ".".join(part for part in (table.catalog, table.db, table.name) if part)
            if not (table.catalog and table.db):
                problems.append(f"{where}: {name} is not a three-part name. Write it as strata.<schema>.<table>.")
            elif table.catalog not in CATALOGS:
                problems.append(f"{where}: {name} is not in the strata catalog. Write it as strata.<schema>.<table>.")
    return problems


def _named_queries(tree: ast.AST) -> dict[str, str]:
    """Each name the file gives a query, at any level, with its text: QUERY = "SELECT ..." or
    QUERY: str = "SELECT ...". This repo writes its queries as named constants."""
    named = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        else:
            continue
        if (isinstance(target, ast.Name) and isinstance(value, ast.Constant) and isinstance(value.value, str)
                and _is_query(value.value)):
            named[target.id] = value.value
    return named


def _text(node: ast.AST, named: dict[str, str]) -> str | None:
    """A string written right there, or the query a name holds, also read through its module."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Attribute):
        return named.get(node.attr)
    return named.get(node.id) if isinstance(node, ast.Name) else None


def _first_text(node: ast.AST, named: dict[str, str]) -> str | None:
    """The text a built string starts with: an f-string's first part, the left end of a + or a %,
    the string .format() or .replace() is called on, the first item of a list or tuple that
    .join() joins, or the query a name holds when += or %= adds to it. A name
    in named stands for its query wherever a written string could, also as an f-string's first
    part (f"{QUERY} AND ...")."""
    if isinstance(node, ast.JoinedStr):
        first = node.values[0] if node.values else None
        if isinstance(first, ast.FormattedValue):
            return _text(first.value, named)
        return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left = node.left
        if isinstance(left, (ast.JoinedStr, ast.BinOp)):
            return _first_text(left, named)
        return _text(left, named)
    if isinstance(node, ast.AugAssign) and isinstance(node.op, (ast.Add, ast.Mod)):
        return _text(node.target, named)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
        if node.func.attr in ("format", "replace"):
            return _text(node.func.value, named)
        joined = node.args[0] if node.func.attr == "join" and node.args else None
        if isinstance(joined, (ast.List, ast.Tuple)) and joined.elts:
            return _text(joined.elts[0], named) or _first_text(joined.elts[0], named)
    return None


def _python_problems(path: Path, relative: str, shared: dict[str, str] | None = None) -> list[str]:
    """Each query in one Python file that breaks a rule. shared holds the queries other files name,
    so a constant imported from them counts; the file's own names come first."""
    source = path.read_text()
    lines = source.splitlines()
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.body and isinstance(node.body[0], ast.Expr)}
    named = {**(shared or {}), **_named_queries(tree)}

    def first_line(node: ast.AST) -> int:
        """The first line of the statement that holds the node."""
        held = node
        while held in parents and not isinstance(held, ast.stmt):
            held = parents[held]
        return getattr(held, "lineno", node.lineno)

    def part_of_a_built_string(node: ast.AST) -> bool:
        parent = parents.get(node)
        return isinstance(parent, (ast.JoinedStr, ast.BinOp, ast.FormattedValue)) or (
            isinstance(parent, ast.Attribute) and parent.attr == "format")

    def passed_to_a_query_call(node: ast.AST) -> bool:
        parent = parents.get(node)
        return (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute)
                and parent.func.attr in QUERY_CALLS and bool(parent.args) and parent.args[0] is node)

    problems = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if id(node) in docstrings or part_of_a_built_string(node) or not _is_query(node.value):
                continue
            problems += _name_problems(node.value, f"{relative}:{node.lineno}", unreadable=passed_to_a_query_call(node))
            continue
        text = _first_text(node, named)
        if text is None or not _is_query(text) or part_of_a_built_string(node):
            continue
        if NAMES_ONLY not in "\n".join(lines[first_line(node) - 1:node.end_lineno]):
            problems.append(f"{relative}:{node.lineno}: {BUILT}")
    return list(dict.fromkeys(problems))


def problems(root: Path = ROOT) -> list[str]:
    """Every place a query breaks one of the two rules, in file order."""
    root = Path(root)
    found = []
    for folder in SQL_FOLDERS:
        for path in sorted((root / folder).rglob("*.sql")):
            found += _name_problems(path.read_text(), path.relative_to(root).as_posix())
    python = [path for folder in PYTHON_FOLDERS for path in sorted((root / folder).rglob("*.py"))
              if "tests" not in path.relative_to(root).parts]
    shared = {}
    for path in python:
        shared.update(_named_queries(ast.parse(path.read_text())))
    for path in python:
        found += _python_problems(path, path.relative_to(root).as_posix(), shared)
    return found


def main() -> int:
    found = problems()
    for problem in found:
        print(problem)
    if found:
        print(f"The SQL lint found {len(found)} {'query' if len(found) == 1 else 'queries'} to fix.")
        return 1
    print("Every query names its tables in three parts and binds its values.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
