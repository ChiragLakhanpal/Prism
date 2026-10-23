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

    def __init__(self, clock, first, each, unavailable=None, breaks_on_write=None):
        self.clock, self.first, self.each, self.unavailable = clock, first, each, unavailable
        self.breaks_on_write = breaks_on_write
        self.rows, self.finished = {}, False

    def prepare(self):
        if self.unavailable:
            raise probe_lakebase.Unavailable(self.unavailable)
        self.clock.now += self.first / 1000

    def write(self, key, value):
        if self.breaks_on_write:
            raise probe_lakebase.Unavailable(self.breaks_on_write)
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
    assert "strata.ops: getting ready, with its first statement, took 6,000 ms. Of 10 tries at a write and a read, the middle time was " \
           "400 ms and the longest was 400 ms." in text
    assert "Lakebase: getting ready, with its first statement, took 900 ms. Of 10 tries at a write and a read, the middle time was " \
           "30 ms and the longest was 30 ms." in text
    assert "- Last run: October 24, 2026" in text
    assert not (document.parent / "adr").exists()
    assert ops.finished and lakebase.finished


def test_lakebase_wins_only_when_strata_ops_is_over_the_budget_and_lakebase_is_within_it(document):
    clock = Clock()

    outcome, text = probe(document, FakeStore(clock, 9000, 1800), FakeStore(clock, 900, 40), clock)

    assert outcome.chosen == "Lakebase"
    assert "- Chosen store: Lakebase" in text
    adr = (document.parent / "adr" / "0001-app-state-lives-in-lakebase.md").read_text()
    assert adr.startswith("# App state lives in Lakebase")
    assert "1,800 ms" in adr and "40 ms" in adr
    assert "Ticket 15 designs how the app reaches Lakebase as each viewer" in adr


def test_the_lakebase_adr_takes_the_next_free_number_and_never_overwrites_one(document):
    adrs = document.parent / "adr"
    adrs.mkdir()
    (adrs / "0004-the-knowledge-graph-is-unity-catalog-tables.md").write_text("# Kept\n")
    (adrs / "0005-another-ticket-took-this-number.md").write_text("# Also kept\n")
    clock = Clock()

    probe(document, FakeStore(clock, 9000, 1800), FakeStore(clock, 900, 40), clock)

    assert (adrs / "0005-another-ticket-took-this-number.md").read_text() == "# Also kept\n"
    assert (adrs / "0006-app-state-lives-in-lakebase.md").read_text().startswith("# App state lives in Lakebase")

    outcome, _ = probe(document, FakeStore(clock, 9000, 1800), FakeStore(clock, 900, 40), clock)

    assert outcome.chosen == "Lakebase"
    # A second run that Lakebase wins finds its ADR already written and leaves it as it is.
    assert sorted(path.name for path in adrs.iterdir()) == [
        "0004-the-knowledge-graph-is-unity-catalog-tables.md", "0005-another-ticket-took-this-number.md",
        "0006-app-state-lives-in-lakebase.md"]


def test_when_free_edition_has_no_lakebase_strata_ops_wins_and_the_reason_is_written_down(document):
    clock = Clock()

    outcome, text = probe(document, FakeStore(clock, 9000, 1800),
                          FakeStore(clock, 0, 0, unavailable="Lakebase is not enabled in this workspace."), clock)

    assert outcome.chosen == "strata.ops"
    assert "Lakebase: I could not make a database. Lakebase is not enabled in this workspace." in text
    assert not (document.parent / "adr").exists()


def test_a_lakebase_that_fails_after_it_was_made_is_written_down_and_strata_ops_wins(document):
    clock = Clock()

    outcome, text = probe(document, FakeStore(clock, 9000, 1800),
                          FakeStore(clock, 900, 40, breaks_on_write="The connection closed."), clock)

    assert outcome.chosen == "strata.ops"
    assert "Lakebase: I made a database, but a write or a read failed. The connection closed." in text


def test_a_lakebase_error_during_the_tries_becomes_the_reason_it_was_unavailable():
    import app_live

    class Broken:
        def execute(self, *args):
            raise OSError("server closed the connection\n   unexpectedly")

    store = app_live.LakebaseStore(w=None)
    store.connection = Broken()

    with pytest.raises(probe_lakebase.Unavailable, match="^server closed the connection unexpectedly$"):
        store.write("key", "probe")
    with pytest.raises(probe_lakebase.Unavailable, match="^server closed the connection unexpectedly$"):
        store.read("key")


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
