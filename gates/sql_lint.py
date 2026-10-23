#!/usr/bin/env python3
"""The SQL lint, a gate step: every query names its tables in three parts and binds its values.

Strata's SQL runs on the workspace and on DuckDB, as each viewer, so two rules hold everywhere
(docs/agents/areas/data.md; spec, "Security and privacy"):

1. Every table is named in three parts, strata.<schema>.<table> (or system.information_schema.<x>).
   A name defined in the same query, by WITH, needs no parts.
2. Every value is a bound :name parameter. Code never builds a value into a query's text. A query
   whose text code does build, from table or column names only, says so on its first line with
   the comment `# sql-lint: names only`, so a reviewer can check that claim in one place.

It reads every .sql file under src/strata and tests/ground_truth, and the Python under src/strata
and ops/bundle: each query passed to run(), execute(), executemany() or sql(), and each module
constant that holds a query. Two places are left out on purpose: gates/, whose fixture build
loads the fixture's own copy of the sources into schemas of its own, and ops/dayone, ticket 03's
day-one probes, which run once on the workspace's own catalog and bind each name with
IDENTIFIER(:name).

    uv run --frozen python gates/sql_lint.py
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

ROOT = Path(__file__).resolve().parents[1]
SQL_FOLDERS = ("src/strata", "tests/ground_truth")
PYTHON_FOLDERS = ("src/strata", "ops/bundle")
QUERY_CALLS = {"run", "execute", "executemany", "sql"}
QUERY_WORDS = ("SELECT", "INSERT", "MERGE", "WITH", "CREATE", "DELETE", "UPDATE")
NAMES_ONLY = "# sql-lint: names only"


def _is_query(text: str) -> bool:
    lines = [line for line in text.strip().splitlines() if not line.strip().startswith("--")]
    return bool(lines) and lines[0].lstrip().upper().startswith(QUERY_WORDS)


def _name_problems(sql: str, where: str) -> list[str]:
    try:
        statements = [statement for statement in sqlglot.parse(sql, read="databricks") if statement is not None]
    except ParseError as error:
        return [f"{where}: I could not read this SQL to check it: {str(error).splitlines()[0]}"]
    problems = []
    for statement in statements:
        defined = {cte.alias_or_name for cte in statement.find_all(exp.CTE)}
        for table in statement.find_all(exp.Table):
            if not table.name or (table.catalog and table.db):
                continue
            if not table.db and table.name in defined:
                continue
            name = ".".join(part for part in (table.catalog, table.db, table.name) if part)
            problems.append(f"{where}: {name} is not a three-part name. Write it as strata.<schema>.<table>.")
    return problems


def _python_problems(path: Path, relative: str) -> list[str]:
    source = path.read_text()
    lines = source.splitlines()
    tree = ast.parse(source)
    problems = []
    for node in tree.body:  # module constants that hold a query
        if (isinstance(node, ast.Assign) and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
                and _is_query(node.value.value)):
            problems += _name_problems(node.value.value, f"{relative}:{node.lineno}")
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                and node.func.attr in QUERY_CALLS and node.args):
            continue
        query = node.args[0]
        if isinstance(query, ast.Constant) and isinstance(query.value, str):
            if _is_query(query.value):
                problems += _name_problems(query.value, f"{relative}:{node.lineno}")
        elif isinstance(query, (ast.JoinedStr, ast.BinOp)) or (
                isinstance(query, ast.Call) and isinstance(query.func, ast.Attribute) and query.func.attr == "format"):
            if NAMES_ONLY not in "\n".join(lines[node.lineno - 1:query.end_lineno]):
                problems.append(f"{relative}:{node.lineno}: this query's text is built in code. Bind each value as a "
                                f":name parameter; a query that builds in only table or column names says so with "
                                f"'{NAMES_ONLY}'.")
    return problems


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
