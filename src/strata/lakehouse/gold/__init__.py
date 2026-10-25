"""Gold: the knowledge model's tables (ADR 0004), each built by one plain SQL query.

Each file in this folder, <table>.sql, holds one Databricks SQL query over silver (and over gold
tables built before it) that returns exactly the columns of strata.gold.<table>, in the table's
order, and a `-- key:` line that names the columns identifying a row. sync() makes the table equal
the query with one MERGE: it adds new rows, updates changed ones and removes rows the query no
longer returns. It counts those first, comparing whole rows column by column in order, and runs the
MERGE only when there are any, so a night that changed nothing counts no rows and rewrites none.
The same text runs on DuckDB in the gate, through the transpile step, and on Databricks.

A query that returns no rows while its table holds some stops the run, so a broken bronze or
silver never empties gold.
"""

from __future__ import annotations

from importlib import resources

from strata.lakehouse.engine import Engine, EngineError

# The order the tables are built in: a table comes after every gold table its query reads.
ORDER = ("country", "project", "project_loan", "project_isr_rating", "notice", "contract", "supplier",
         "contract_supplier", "package", "ieg_rating", "loan", "project_closing_date", "governance_score")


def _query(table: str) -> tuple[str, tuple[str, ...]]:
    # importlib.resources rather than __file__, which serverless Python tasks do not set.
    text = (resources.files("strata.lakehouse.gold") / f"{table}.sql").read_text()
    keys = [line.split(":", 1)[1] for line in text.splitlines() if line.startswith("-- key:")]
    if len(keys) != 1:
        raise EngineError(f"gold/{table}.sql needs one '-- key: column, ...' line naming the columns of a row's key.")
    query = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--")).strip()
    return query, tuple(column.strip() for column in keys[0].split(","))


def key(table: str) -> tuple[str, ...] | None:
    """The columns that identify a row of strata.gold.<table>, from its query's "-- key:" line, or None when
    no query in this folder builds it."""
    if not (resources.files("strata.lakehouse.gold") / f"{table}.sql").is_file():
        return None
    return _query(table)[1]


def sync(engine: Engine, table: str) -> int:
    """Make strata.gold.<table> equal its query. Returns the rows it added, changed or removed."""
    query, keys = _query(table)
    target = f"strata.gold.{table}"
    found = engine.run(f"SELECT count(*) AS n FROM ({query}) AS q").rows[0][0]  # sql-lint: names only
    held = engine.run(f"SELECT count(*) AS n FROM {target}").rows[0][0]  # sql-lint: names only
    if int(found) == 0 and int(held) > 0:
        raise EngineError(f"The query for {target} returned no rows, but the table holds {held}. I stopped "
                          "rather than empty it. Check that bronze and silver hold this source's pages.")
    twice = duplicate_keys(engine, query, keys)
    if twice:
        raise EngineError(f"The query for {target} gives {twice} keys ({', '.join(keys)}) more than one row. A MERGE "
                          "with such a source puts two rows in the table or fails, so I stopped. Make the query "
                          "give each key one row.")
    match = " AND ".join(f"target.{key} = source.{key}" for key in keys)
    # Count what the MERGE would change first, and run it only when something changes: a MERGE updates every row
    # it matches, so its own count is the whole table on a night that changed nothing (ticket 07's review, P3).
    added_or_changed = engine.run(  # sql-lint: names only
        f"SELECT count(*) AS n FROM (SELECT * FROM ({query}) AS q EXCEPT SELECT * FROM {target}) AS c").rows[0][0]
    removed = engine.run(  # sql-lint: names only
        f"SELECT count(*) AS n FROM {target} AS target "
        f"WHERE NOT EXISTS (SELECT 1 FROM ({query}) AS source WHERE {match})").rows[0][0]
    changed = int(added_or_changed) + int(removed)
    if changed:
        engine.run(  # sql-lint: names only
            f"MERGE INTO {target} AS target USING ({query}) AS source ON {match} "
            "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT * WHEN NOT MATCHED BY SOURCE THEN DELETE")
    return changed


def duplicate_keys(engine: Engine, query: str, keys: tuple[str, ...]) -> int:
    """How many keys the query gives more than one row. On October 24, 2026 the notice query gave 943
    notices two rows each, and the first MERGE put both in the table because nothing matched yet."""
    columns = ", ".join(keys)
    result = engine.run(f"SELECT count(*) AS n FROM (SELECT {columns} FROM ({query}) AS q "  # sql-lint: names only
                        f"GROUP BY {columns} HAVING count(*) > 1) AS d")
    return int(result.rows[0][0])


def build(engine: Engine) -> int:
    """Sync every gold table, in ORDER. Returns the rows they added, changed or removed."""
    return sum(sync(engine, table) for table in ORDER)
