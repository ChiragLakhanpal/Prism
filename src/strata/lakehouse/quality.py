"""The nightly job's quality checks (ticket 43; the 45 brief, section 6, "Nightly runs and quality checks").

When a task of the job finishes, check() runs the checks config/quality_checks.toml names for it, and record()
keeps every result in strata.ops.quality_checks, passed or failed. A failed check never stops the job: the
dashboard's Governance page shows it. Five kinds of check, as the Governance page names them:

- row_count            the table's rows, inside the range config/thresholds.toml [quality_checks] gives it
- missing_key          the rows with no value in one of the table's key columns, one check per column
- missing_public_from  the rows with no Disclosed date (public_from, ADR 0002)
- duplicates           the rows that repeat a key, beyond the first row of each key
- contacts_left        the notices whose text still carries what ingestion takes out: an email address, a
                       labelled phone number or a name after "Attention" and a title (CLAUDE.md rule 8;
                       strata.lakehouse.contacts, LEFTOVERS)

Each table costs two queries, or one when it has no key, so the checks run the same on DuckDB in the gate and on
the SQL warehouse. Every value goes to the query as a bound parameter; only the checked table's and columns'
names, read from the registry, are written into the text.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from strata.config import QualityCheck, load_quality_checks, load_thresholds
from strata.lakehouse import contacts, gold
from strata.lakehouse.engine import Engine

COLUMNS = ("run_id", "night", "task_key", "check_kind", "table_name", "key_name", "found", "expected_min",
           "expected_max", "passed", "checked_at", "public_from")
# A notice that contacts_left counts: its text or its description holds what one of contacts.LEFTOVERS finds, the
# patterns the removal's last pass takes out, one bound parameter each. Silver's notices transform reads again the
# pages of the notices it counts (ticket 121).
CONTACTS_LEFT = " OR ".join(f"regexp_like({column}, :{leftover.parameter})"
                            for column in ("notice_text", "bid_description") for leftover in contacts.LEFTOVERS)


def contacts_left_params() -> dict[str, str]:
    """The patterns CONTACTS_LEFT binds, as parameters: Spark SQL mangles the backslashes of a literal."""
    return {leftover.parameter: leftover.pattern for leftover in contacts.LEFTOVERS}


@dataclass(frozen=True)
class Result:
    """One check's result: a row of strata.ops.quality_checks without its run, night, task and time."""

    check_kind: str
    table_name: str
    key_name: str | None
    found: int
    expected_min: int | None = None
    expected_max: int | None = None

    @property
    def passed(self) -> bool:
        if self.check_kind == "row_count":
            return self.expected_min <= self.found <= self.expected_max
        return self.found == 0


def key_of(check: QualityCheck) -> tuple[str, ...]:
    """The columns that identify a row: the registry's, or else the key line of the gold query that builds it."""
    if check.key:
        return check.key
    schema, table = check.table.split(".")[1:]
    return (gold.key(table) or ()) if schema == "gold" else ()


def row_range(table: str) -> tuple[int, int]:
    limits = load_thresholds()
    given = limits.value("quality_checks.row_counts").get(table)
    if given is not None:
        return int(given[0]), int(given[1])
    return int(limits.value("quality_checks.row_count_min")), int(limits.value("quality_checks.row_count_max"))


def check_table(engine: Engine, check: QualityCheck) -> list[Result]:
    """Every check of one table, in the order the Governance page lists them."""
    key = key_of(check)
    missing = "".join(f", coalesce(count_if({column} IS NULL), 0) AS missing_{number}"
                      for number, column in enumerate(key))
    contacted = f", coalesce(count_if({CONTACTS_LEFT}), 0) AS contacts" if check.contacts else ""
    params = contacts_left_params() if check.contacts else {}
    counts = engine.run(  # sql-lint: names only, the table and its columns come from config/quality_checks.toml
        f"SELECT count(*) AS n, coalesce(count_if(public_from IS NULL), 0) AS no_public_from{missing}{contacted} "
        f"FROM {check.table}", params).rows[0]
    low, high = row_range(check.table)
    results = [Result("row_count", check.table, None, int(counts[0]), low, high)]
    results += [Result("missing_key", check.table, column, int(counts[2 + number])) for number, column in enumerate(key)]
    results.append(Result("missing_public_from", check.table, None, int(counts[1])))
    if key:
        columns = ", ".join(key)
        repeated = engine.run(  # sql-lint: names only, the table and its key come from config/quality_checks.toml
            f"SELECT coalesce(sum(n - 1), 0) AS repeated FROM (SELECT {columns}, count(*) AS n FROM {check.table} "
            f"GROUP BY {columns} HAVING count(*) > 1) AS d").rows[0][0]
        results.append(Result("duplicates", check.table, None, int(repeated)))
    if check.contacts:
        results.append(Result("contacts_left", check.table, None, int(counts[-1])))
    return results


def check(engine: Engine, task_key: str) -> list[Result]:
    """Every check the registry names for the task, table by table."""
    return [result for entry in load_quality_checks() if entry.task == task_key
            for result in check_table(engine, entry)]


def record(engine: Engine, results: list[Result], run_id: str, night: dt.date, task_key: str,
           when: dt.datetime) -> int:
    """Keep each result in strata.ops.quality_checks. Returns how many rows it wrote."""
    rows = [(run_id, night, task_key, r.check_kind, r.table_name, r.key_name, r.found, r.expected_min, r.expected_max,
             r.passed, when, when.astimezone(dt.UTC).date()) for r in results]
    return engine.insert_rows("strata.ops.quality_checks", COLUMNS, rows) if rows else 0
