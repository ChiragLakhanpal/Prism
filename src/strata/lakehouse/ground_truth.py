"""Ground-truth SQL files: a query, its parameters, the engines it runs on and the rows it must return.

A file in tests/ground_truth holds one Databricks SQL query and these comment lines:

    -- param: as_of = 2018-12-31        a named parameter, bound as text (the SQL casts it)
    -- engines: duckdb, databricks      where it runs; DuckDB only when the line is missing
    -- expect: event,happened_on         the rows it must return, as CSV, header first

The gate runs every file on the fixture database. A file marked for databricks also runs on the
workspace's SQL warehouse, through ops/bundle/check.py, and must return the same rows there.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

ENGINES = ("duckdb", "databricks")


@dataclass(frozen=True)
class Case:
    path: Path
    sql: str
    params: dict[str, str]
    engines: tuple[str, ...]
    expected: list[tuple[str, ...]]


def _comment(line: str, label: str) -> str | None:
    marker = f"-- {label}:"
    return line[len(marker):].strip() if line.startswith(marker) else None


def read(path: Path) -> Case:
    sql = Path(path).read_text()
    params, engines, expected = {}, ("duckdb",), []
    for line in sql.splitlines():
        if (value := _comment(line, "expect")) is not None:
            expected.append(value)
        elif (value := _comment(line, "param")) is not None:
            name, equals, text = value.partition("=")
            if not equals or not name.strip():
                raise ValueError(f"{Path(path).name}: write a parameter as '-- param: name = value', not {line!r}.")
            params[name.strip()] = text.strip()
        elif (value := _comment(line, "engines")) is not None:
            engines = tuple(engine.strip() for engine in value.split(","))
            unknown = [engine for engine in engines if engine not in ENGINES]
            if unknown:
                raise ValueError(f"{Path(path).name} names engines I do not know: {', '.join(unknown)}. "
                                 f"Use {', '.join(ENGINES)}.")
    return Case(Path(path), sql, params, engines, [tuple(row) for row in csv.reader(expected)])
