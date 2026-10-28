"""The fixture database's cache (ticket 119). The build records every file and folder it reads, and
writes their hashes beside the database. A build whose inputs all hash the same keeps the database as
it is; a changed input builds it again.

Most tests here run a stand-in for gates/build_fixture.py in a throwaway tree. The stand-in uses
gates/fixture_cache.py the way the real build does, reads a recorded file and lists the table
definitions, and notes each build it makes. The last test reads the key the real build wrote.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

STAND_IN = """\
    import sys
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"

    import fixture_cache

    CACHE = fixture_cache.start(FIXTURE_DB, ROOT)

    import time
    with open(ROOT / "builds.txt", "a") as log:
        log.write("built\\n")
    recorded = (ROOT / "data" / "fixture" / "recorded" / "api" / "awards.json").read_text()
    # As strata.lakehouse.catalog finds the table definitions
    tables = [path.read_text() for path in sorted((ROOT / "src/strata/lakehouse/tables").glob("*/*.sql"))]
    time.sleep(float(sys.argv[1]) if len(sys.argv) > 1 else 0)
    FIXTURE_DB.parent.mkdir(parents=True, exist_ok=True)
    FIXTURE_DB.write_text(recorded + " ".join(tables))
    CACHE.write()
    """


def write(tree, name, text):
    path = tree / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))


def make_tree(tmp_path):
    tree = tmp_path / "tree"
    shutil.copytree(ROOT / "gates", tree / "gates", ignore=lambda folder, names: [
        name for name in names if name not in ("fixture_cache.py",)])
    write(tree, "gates/build_fixture.py", STAND_IN)
    write(tree, "data/fixture/recorded/api/awards.json", '{"data": [1245092.76]}\n')
    write(tree, "src/strata/lakehouse/tables/gold/contract.sql", "CREATE TABLE strata.gold.contract (x INT)\n")
    write(tree, "uv.lock", "version = 1\n")
    return tree


def build(tree, *args):
    done = subprocess.run([sys.executable, "gates/build_fixture.py", *args], cwd=tree, capture_output=True,
                          text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    return done.stdout


def builds(tree):
    return len((tree / "builds.txt").read_text().splitlines())


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_a_second_build_with_unchanged_inputs_keeps_the_database_and_its_bytes(tmp_path):
    tree = make_tree(tmp_path)
    database = tree / "data" / "out" / "fixture.duckdb"

    build(tree)
    first = sha256(database), database.stat().st_mtime_ns
    kept = build(tree)

    assert builds(tree) == 1
    assert (sha256(database), database.stat().st_mtime_ns) == first
    assert "so the build kept data/out/fixture.duckdb as it was" in kept
    key = json.loads((tree / "data" / "out" / "fixture.inputs.json").read_text())
    assert key["files"]["data/fixture/recorded/api/awards.json"] == sha256(tree / "data/fixture/recorded/api/awards.json")
    assert "src/strata/lakehouse/tables" in key["folders"]
    assert key["database"] == first[0]


# Edits to the throwaway tree after its first build, each of which must build the database again.
EDITS = {
    "a recorded file changed": ("data/fixture/recorded/api/awards.json", '{"data": [1245092.77]}\n'),
    "a table definition changed": ("src/strata/lakehouse/tables/gold/contract.sql", "CREATE TABLE x (y INT)\n"),
    "a table definition added": ("src/strata/lakehouse/tables/gold/supplier.sql", "CREATE TABLE x (y INT)\n"),
    "a schema of table definitions added": ("src/strata/lakehouse/tables/ops/runs.sql", "CREATE TABLE x (y INT)\n"),
    "the build script changed": ("gates/build_fixture.py", STAND_IN + "    # one more line\n"),
    "the cache's code changed": ("gates/fixture_cache.py", None),
    "the package versions changed": ("uv.lock", "version = 2\n"),
}


@pytest.mark.parametrize(("name", "text"), EDITS.values(), ids=EDITS.keys())
def test_a_changed_input_builds_the_database_again(tmp_path, name, text):
    tree = make_tree(tmp_path)
    build(tree)
    if text is None:
        text = (tree / name).read_text() + "# one more line\n"
    write(tree, name, text)

    again = build(tree)

    assert builds(tree) == 2
    assert "The build makes data/out/fixture.duckdb again, because" in again
    assert build(tree) and builds(tree) == 2


def test_a_file_the_build_never_reads_leaves_the_database_as_it_is(tmp_path):
    tree = make_tree(tmp_path)
    build(tree)
    write(tree, "tests/test_awards.py", "def test_awards():\n    pass\n")
    write(tree, "src/strata/server/home.py", "TITLE = 'Home'\n")
    # Hidden files and compiled modules beside the inputs, such as the ones macOS and Python leave
    write(tree, "src/strata/lakehouse/tables/.DS_Store", "")
    write(tree, "src/strata/lakehouse/tables/__pycache__/catalog.cpython-312.pyc", "")

    build(tree)

    assert builds(tree) == 1


def test_a_database_written_after_its_build_is_built_again(tmp_path):
    tree = make_tree(tmp_path)
    build(tree)
    with open(tree / "data" / "out" / "fixture.duckdb", "a") as database:
        database.write("a row a test should never have written")

    again = build(tree)

    assert builds(tree) == 2
    assert "because data/out/fixture.duckdb changed after its build" in again


def test_two_builds_started_together_build_the_database_once(tmp_path):
    """As the gate's two python lanes do: each starts with the build, and the second keeps what the first made."""
    tree = make_tree(tmp_path)
    started = [subprocess.Popen([sys.executable, "gates/build_fixture.py", "1"], cwd=tree, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True) for _ in range(2)]
    outputs = [process.communicate(timeout=60)[0] for process in started]

    assert [process.returncode for process in started] == [0, 0], outputs
    assert builds(tree) == 1
    assert sum("so the build kept data/out/fixture.duckdb as it was" in output for output in outputs) == 1


def test_the_real_build_s_key_holds_every_recorded_file_table_definition_and_config_file_it_read(fixture_db):
    """The gate's build wrote this key, so a change to any of these files builds the database again."""
    from strata.fixture import recorded as fmt

    key_file = fixture_db.with_name("fixture.inputs.json")
    assert key_file.is_file(), "Build the fixture database again: uv run --frozen python gates/build_fixture.py"
    key = json.loads(key_file.read_text())
    manifest = fmt.load_manifest()
    recorded = {(manifest.recorded / name).relative_to(ROOT).as_posix() for name in manifest.files()}
    tables = ROOT / "src" / "strata" / "lakehouse" / "tables"
    definitions = {path.relative_to(ROOT).as_posix() for path in tables.glob("*/*.sql")}

    assert len(recorded) > 100 and recorded <= key["files"].keys()
    assert len(definitions) > 100 and definitions <= key["files"].keys()
    assert {"data/fixture/sources.toml", "config/thresholds.toml", "config/slice.toml", "gates/build_fixture.py",
            "src/strata/lakehouse/catalog.py", "uv.lock"} <= key["files"].keys()
    assert {"src/strata/lakehouse/tables", "src/strata/lakehouse/tables/gold"} <= key["folders"].keys()
    assert key["database"] == sha256(fixture_db)
    assert not any(name.startswith(("tests/test_", "web/", ".venv/", "data/out/")) for name in key["files"])
