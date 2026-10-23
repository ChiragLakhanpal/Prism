#!/usr/bin/env python3
"""The SQL lint, a gate step: every query names its tables in three parts and binds its values.

Strata's SQL runs on the workspace and on DuckDB, as each viewer, so two rules hold everywhere
(docs/agents/areas/data.md; spec, "Security and privacy"):

1. Every table is named in three parts, in the strata catalog: strata.<schema>.<table> (or
   system.information_schema.<x>). A name defined in the same query, by WITH, needs no parts.
2. Every value is a bound :name parameter. Code never builds a value into a query's text. A query
   whose text code does build, from table or column names only, says so on its first line with
   the comment `# sql-lint: names only`, so a reviewer can check that claim in one place.

It reads every .sql file under src/strata and tests/ground_truth, and the Python under src/strata
and ops/bundle: every string that holds a query, wherever it is written (passed to run(),
execute(), executemany() or sql(), held in a variable or a constant, or returned), and every
query text that code builds with an f-string, + or %, or .format(). A string is a query when it
starts the way a statement does (QUERY_START): a SELECT, an INSERT or MERGE into a table, a WITH
clause, a CREATE of a table, view or schema, a DELETE, or an UPDATE that sets columns. The
names-only comment may sit on any line of the statement that builds the query. Two places are
left out on purpose: gates/, whose fixture build
loads the fixture's own copy of the sources into schemas of its own, and ops/dayone, ticket 03's
day-one probes, which run once on the workspace's own catalog and bind each name with
IDENTIFIER(:name).

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


def _first_text(node: ast.AST) -> str | None:
    """The written text a built string starts with: an f-string's first part, the left end of a + or
    a %, or the string .format() is called on."""
    if isinstance(node, ast.JoinedStr):
        first = node.values[0] if node.values else None
        return first.value if isinstance(first, ast.Constant) and isinstance(first.value, str) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Mod)):
        left = node.left
        if isinstance(left, (ast.JoinedStr, ast.BinOp)):
            return _first_text(left)
        return left.value if isinstance(left, ast.Constant) and isinstance(left.value, str) else None
    if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "format"
            and isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str)):
        return node.func.value.value
    return None


def _python_problems(path: Path, relative: str) -> list[str]:
    source = path.read_text()
    lines = source.splitlines()
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
                  and node.body and isinstance(node.body[0], ast.Expr)}

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
        text = _first_text(node)
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
    for folder in PYTHON_FOLDERS:
        for path in sorted((root / folder).rglob("*.py")):
            if "tests" not in path.relative_to(root).parts:
                found += _python_problems(path, path.relative_to(root).as_posix())
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
