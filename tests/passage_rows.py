"""What the document readers wrote, as one count and one hash per table (ticket 72).

Ticket 72 changed the passage reader to write each document's passages as soon as it has read that document,
instead of writing every document's passages at the end. The rows must stay the same, so the tests hash every
table the readers write and compare the hashes with tests/fixtures/passages/rows.json, which holds the hashes the
reader gave on the fixture before that change (build/strata at 3587cc76).

A hash leaves out only the columns that hold the time a row was written (scanned_at, embedded_at, measured_at and
the like). A run's clock is read once more or once less when its work is split by document, and the fixture's
clocks move on a millisecond each time they are read, so those times may move. Every other column is hashed,
the run ids and each passage's vector included.

When a change means to change these rows, write the new hashes with this command and say why in the commit:

    uv run --frozen python tests/passage_rows.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests" / "fixtures" / "passages" / "rows.json"

# The tables the plan reader and the passage reader write, each with the rows they hold that a reader wrote.
TABLES = {
    "strata.bronze.document_lists": None,
    "strata.bronze.document_texts": None,
    "strata.bronze.document_pages": None,
    "strata.bronze.layout_pages": None,
    "strata.silver.documents": None,
    "strata.silver.document_page_routes": None,
    "strata.silver.passages": None,
    "strata.silver.passage_shields": None,
    "strata.silver.passage_embeddings": None,
    "strata.silver.isr_ratings": None,
    "strata.gold.passage": None,
    "strata.ops.parse_runs": None,
    "strata.ops.parse_failures": None,
    "strata.ops.documents_read": None,
    "strata.ops.stress_shelf": None,
    "strata.ops.passage_language_checks": None,
    "strata.ops.data_readiness": "source = 'documents'",
}
# The columns that hold when a row was written, which the hash leaves out.
WRITTEN_AT = {"scanned_at", "embedded_at", "measured_at", "parsed_at", "started_at", "finished_at", "failed_at"}


def digest(engine) -> dict[str, list]:
    """Each table's row count and the hash of its rows, sorted, with the written-at columns left out."""
    found = {}
    for table, where in TABLES.items():
        schema, name = table.split(".")[1:]
        columns = [str(row[0]) for row in engine.run(
            "SELECT column_name FROM information_schema.columns WHERE table_catalog = 'strata' AND table_schema = :schema "
            "AND table_name = :name ORDER BY ordinal_position", {"schema": schema, "name": name}).rows]
        kept = [column for column in columns if column not in WRITTEN_AT]
        sql = f"SELECT {', '.join(kept)} FROM {table}" + (f" WHERE {where}" if where else "")
        rows = sorted(repr(tuple(row)) for row in engine.run(sql).rows)
        found[table] = [len(rows), hashlib.sha256("\n".join(rows).encode("utf-8")).hexdigest()]
    return found


def golden() -> dict:
    return json.loads(GOLDEN.read_text())


def _write() -> int:
    """Write the hashes of the fixture database the gate builds, and of the nightly job's second night in
    tests/test_nightly_delta.py, as rows.json."""
    import importlib
    import subprocess
    import tempfile

    from strata.lakehouse.engine import DuckDBEngine

    fixture = ROOT / "data" / "out" / "fixture.duckdb"
    subprocess.run([sys.executable, str(ROOT / "gates" / "build_fixture.py")], check=True)
    with DuckDBEngine.open(fixture, read_only=True) as engine:
        hashes = {"fixture": digest(engine)}
    sys.path.append(str(ROOT / "tests"))  # last, so no test helper hides a module of the same name
    nightly_delta = importlib.import_module("test_nightly_delta")
    with tempfile.TemporaryDirectory() as folder, nightly_delta.two_nights(Path(folder) / "nightly.duckdb") as nights:
        hashes["nightly"] = digest(nights[0])
    GOLDEN.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN.write_text(json.dumps(hashes, indent=2, sort_keys=True) + "\n")
    print(f"Wrote {GOLDEN.relative_to(ROOT)}.")
    return 0


if __name__ == "__main__":
    sys.exit(_write())
