"""Gold: the knowledge model's tables (ADR 0004), each built by one plain SQL query.

Each file in this folder, <table>.sql, holds one Databricks SQL query over silver (and over gold
tables built before it) that returns exactly the columns of strata.gold.<table>, and a
`-- key:` line that names the columns identifying a row. sync() makes the table equal the query
with one MERGE: it adds new rows, updates the rest and removes rows the query no longer returns.
The same text runs on DuckDB in the gate, through the transpile step, and on Databricks.

A query that returns no rows while its table holds some stops the run, so a broken bronze or
silver never empties gold.
"""

from __future__ import annotations

from importlib import resources

from strata.lakehouse.engine import Engine, EngineError

# The order the tables are built in: a table comes after every gold table its query reads.
ORDER = ("country", "project", "project_loan", "notice", "contract", "supplier", "contract_supplier", "package")


def _query(table: str) -> tuple[str, tuple[str, ...]]:
    # importlib.resources rather than __file__, which serverless Python tasks do not set.
    text = (resources.files("strata.lakehouse.gold") / f"{table}.sql").read_text()
    keys = [line.split(":", 1)[1] for line in text.splitlines() if line.startswith("-- key:")]
    if len(keys) != 1:
        raise EngineError(f"gold/{table}.sql needs one '-- key: column, ...' line naming the columns of a row's key.")
    query = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--")).strip()
    return query, tuple(column.strip() for column in keys[0].split(","))


def sync(engine: Engine, table: str) -> int:
    """Make strata.gold.<table> equal its query. Returns the rows the MERGE touched."""
    query, keys = _query(table)
    target = f"strata.gold.{table}"
    found = engine.run(f"SELECT count(*) AS n FROM ({query}) AS q").rows[0][0]  # sql-lint: names only
    held = engine.run(f"SELECT count(*) AS n FROM {target}").rows[0][0]  # sql-lint: names only
    if int(found) == 0 and int(held) > 0:
        raise EngineError(f"The query for {target} returned no rows, but the table holds {held}. I stopped "
                          "rather than empty it. Check that bronze and silver hold this source's pages.")
    match = " AND ".join(f"target.{key} = source.{key}" for key in keys)
    result = engine.run(  # sql-lint: names only
        f"MERGE INTO {target} AS target USING ({query}) AS source ON {match} "
        "WHEN MATCHED THEN UPDATE SET * WHEN NOT MATCHED THEN INSERT * WHEN NOT MATCHED BY SOURCE THEN DELETE")
    return int(result.rows[0][0]) if result.rows else 0


def build(engine: Engine) -> int:
    """Sync every gold table, in ORDER. Returns the rows the MERGEs touched."""
    return sum(sync(engine, table) for table in ORDER)
