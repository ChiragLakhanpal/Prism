"""The gate runs the tests under tests/ on pytest-xdist workers, so each test must be safe beside
the others. A worker is its own process: it has its own environment and working folder, but it
shares the files and ports of this computer with the other workers.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# A stand-in for gates/build_fixture.py: it notes each build, takes its time, and writes the
# database the way the real build does, into a new file that it then swaps in.
SLOW_BUILD = """\
    import os, time
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    with open(root / "builds.txt", "a") as log:
        log.write(f"{os.getpid()}\\n")
    out = root / "data" / "out" / "fixture.duckdb"
    out.parent.mkdir(parents=True, exist_ok=True)
    building = out.with_name("fixture.building.duckdb")
    building.write_text("built")
    time.sleep(1)
    os.replace(building, out)
    """

NEEDS_THE_DATABASE = """\
    def test_one_reads_the_fixture_database(fixture_db):
        assert fixture_db.read_text() == "built"

    def test_two_reads_the_fixture_database(fixture_db):
        assert fixture_db.read_text() == "built"
    """


def write(tree, name, text):
    path = tree / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(text))


def test_workers_that_need_a_missing_fixture_database_at_once_build_it_once(tmp_path):
    tree = tmp_path / "tree"
    write(tree, "pytest.ini", "[pytest]\n")
    write(tree, "tests/conftest.py", (ROOT / "tests" / "conftest.py").read_text())
    write(tree, "tests/test_reads.py", NEEDS_THE_DATABASE)
    write(tree, "gates/build_fixture.py", SLOW_BUILD)
    # The run below starts its own workers, so it must not look like one of this run's workers.
    env = {key: value for key, value in os.environ.items() if not key.startswith("PYTEST_")}

    # --dist each runs both tests on both workers, so the two workers need the database at the same time.
    done = subprocess.run([sys.executable, "-m", "pytest", "-p", "no:cacheprovider", "--numprocesses", "2",
                           "--dist", "each", "--basetemp", str(tmp_path / "basetemp"), "tests"],
                          cwd=tree, capture_output=True, text=True, env=env, timeout=60)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "4 passed" in done.stdout, done.stdout
    assert len((tree / "builds.txt").read_text().splitlines()) == 1
