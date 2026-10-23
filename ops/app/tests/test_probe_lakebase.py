"""The Lakebase probe: it times a write and a read of one row in strata.ops's warehouse and in a
Lakebase database, applies docs/app-state.md's rule, and writes the times and the decision into
that document, with an ADR when Lakebase wins.

Fake stores with known times stand in for the warehouse and Lakebase. The live run is a
workspace step (docs/workspace-catchup.md).
"""

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "app"))

import probe_lakebase  # noqa: E402

BUDGET = 1000


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


class FakeStore:
    """A store whose first statement takes `first` ms and each write and read `each` ms."""

    def __init__(self, clock, first, each, unavailable=None):
        self.clock, self.first, self.each, self.unavailable = clock, first, each, unavailable
        self.rows, self.finished = {}, False

    def prepare(self):
        if self.unavailable:
            raise probe_lakebase.Unavailable(self.unavailable)
        self.clock.now += self.first / 1000

    def write(self, key, value):
        self.clock.now += self.each / 2000
        self.rows[key] = value

    def read(self, key):
        self.clock.now += self.each / 2000
        return self.rows.get(key)

    def finish(self):
        self.finished = True


@pytest.fixture
def document(tmp_path):
    path = tmp_path / "docs" / "app-state.md"
    path.parent.mkdir()
    shutil.copy(REPO / "docs" / "app-state.md", path)
    return path


def probe(document, ops, lakebase, clock):
    outcome = probe_lakebase.check({"strata.ops": ops, "Lakebase": lakebase}, BUDGET, clock)
    probe_lakebase.record(document, outcome, day="2026-10-24")
    return outcome, document.read_text()


def test_strata_ops_wins_when_its_round_trip_is_within_the_budget(document):
    clock = Clock()
    ops, lakebase = FakeStore(clock, first=6000, each=400), FakeStore(clock, first=900, each=30)

    outcome, text = probe(document, ops, lakebase, clock)

    assert outcome.chosen == "strata.ops"
    assert "- Status: run" in text
    assert "- Chosen store: strata.ops" in text
    assert "strata.ops: the first statement took 6,000 ms; a write and a read took 400 ms in the middle of 10 tries, " \
           "and 400 ms at most." in text
    assert "Lakebase: the first statement took 900 ms; a write and a read took 30 ms in the middle of 10 tries, " \
           "and 30 ms at most." in text
    assert "- Last run: October 24, 2026" in text
    assert not (document.parent / "adr").exists()
    assert ops.finished and lakebase.finished


def test_lakebase_wins_only_when_strata_ops_is_over_the_budget_and_lakebase_is_within_it(document):
    clock = Clock()

    outcome, text = probe(document, FakeStore(clock, 9000, 1800), FakeStore(clock, 900, 40), clock)

    assert outcome.chosen == "Lakebase"
    assert "- Chosen store: Lakebase" in text
    adr = (document.parent / "adr" / "0005-app-state-lives-in-lakebase.md").read_text()
    assert adr.startswith("# App state lives in Lakebase")
    assert "1,800 ms" in adr and "40 ms" in adr


def test_when_free_edition_has_no_lakebase_strata_ops_wins_and_the_reason_is_written_down(document):
    clock = Clock()

    outcome, text = probe(document, FakeStore(clock, 9000, 1800),
                          FakeStore(clock, 0, 0, unavailable="Lakebase is not enabled in this workspace."), clock)

    assert outcome.chosen == "strata.ops"
    assert "Lakebase: I could not make a database. Lakebase is not enabled in this workspace." in text
    assert not (document.parent / "adr").exists()


def test_when_neither_store_is_within_the_budget_strata_ops_wins(document):
    clock = Clock()

    outcome, _ = probe(document, FakeStore(clock, 9000, 1800), FakeStore(clock, 900, 1500), clock)

    assert outcome.chosen == "strata.ops"


def test_a_dry_run_prints_the_result_and_writes_nothing(document, capsys):
    before = document.read_text()

    code = probe_lakebase.main(["--dry-run", "--document", str(document)])

    assert code == 0
    assert "Chosen store: strata.ops" in capsys.readouterr().out
    assert document.read_text() == before


def test_the_budget_comes_from_the_thresholds_file():
    from strata.config import load_thresholds

    assert probe_lakebase.budget_ms() == load_thresholds().value("app_state.round_trip_budget_ms")
