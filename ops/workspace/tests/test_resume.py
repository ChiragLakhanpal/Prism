"""The pause and resume command (ops/workspace/resume.py): resume starts what is stopped in the order the parts need
each other and skips what runs; pause stops what bills while idle and deletes the search endpoint only when asked;
status changes nothing. A fake workspace stands in for Databricks; the names come from the real registries."""

import itertools
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "workspace"))

import resume  # noqa: E402

NAMES = {"app": "strata", "instance": "strata-state", "endpoint": "strata-search", "endpoint_type": "STANDARD",
         "index": "strata.gold.passage_index", "dimensions": 1024, "source_table": "strata.gold.passage",
         "primary_key": "passage_id", "embedding_column": "embedding"}
URL = "https://strata-1.example.azure.databricksapps.com"
INDEXES = ["strata.gold.passage_index", "workspace.strata_dayone.passages_index"]


class Fake:
    """The workspace's parts, each with a state a test sets; None means missing. tick() stands in for sleep and moves
    a part that is coming up along, as the workspace would while the script waits."""

    def __init__(self, endpoint="ONLINE", index=(True, 4154), lakebase="AVAILABLE", app="ACTIVE", warehouse="RUNNING"):
        self.calls = []
        self.endpoint_state, self.index_state = endpoint, index
        self.lakebase_state, self.app_state, self.warehouse_state = lakebase, app, warehouse
        self.index_names = list(INDEXES) if endpoint else []

    def tick(self, seconds):
        self.calls.append(("sleep", seconds))
        if self.endpoint_state == "PROVISIONING":
            self.endpoint_state = "ONLINE"
        elif self.index_state == (False, 0):
            self.index_state = (True, 4154)
        if self.lakebase_state == "STOPPING":
            self.lakebase_state = "STOPPED"

    def endpoint(self, name):
        return None if self.endpoint_state is None else {"state": self.endpoint_state}

    def make_endpoint(self, name, endpoint_type):
        self.calls.append(("make_endpoint", name, endpoint_type))
        self.endpoint_state, self.index_names = "PROVISIONING", []

    def indexes(self, endpoint):
        return list(self.index_names)

    def index(self, name):
        if self.index_state is None:
            return None
        ready, rows = self.index_state
        return {"ready": ready, "rows": rows, "message": ""}

    def make_index(self, n):
        self.calls.append(("make_index", n["index"], n["source_table"], n["dimensions"]))
        self.index_state = (False, 0)

    def delete_index(self, name):
        self.calls.append(("delete_index", name))
        self.index_names.remove(name)

    def delete_endpoint(self, name):
        self.calls.append(("delete_endpoint", name))
        self.endpoint_state = None

    def lakebase(self, name):
        if self.lakebase_state is None:
            return None
        return {"state": self.lakebase_state, "stopped": self.lakebase_state == "STOPPED"}

    def start_lakebase(self, name):
        self.calls.append(("start_lakebase", name))
        self.lakebase_state = "AVAILABLE"

    def stop_lakebase(self, name):
        self.calls.append(("stop_lakebase", name))
        self.lakebase_state = "STOPPING"

    def app(self, name):
        if self.app_state is None:
            return None
        return {"compute": self.app_state, "app": "RUNNING" if self.app_state == "ACTIVE" else "UNAVAILABLE", "url": URL}

    def start_app(self, name):
        self.calls.append(("start_app", name))
        self.app_state = "ACTIVE"

    def stop_app(self, name):
        self.calls.append(("stop_app", name))
        self.app_state = "STOPPED"

    def warehouse(self):
        return {"id": "wh-1", "state": self.warehouse_state, "message": ""}

    def start_warehouse(self):
        self.calls.append(("start_warehouse",))
        self.warehouse_state = "STARTING"

    def stop_warehouse(self):
        self.calls.append(("stop_warehouse",))
        self.warehouse_state = "STOPPED"

    def jobs(self):
        return [{"name": "strata nightly", "pause": "PAUSED"}, {"name": "strata cost pull", "pause": "PAUSED"}]


def changes(fake):
    return [call for call in fake.calls if call[0] != "sleep"]


def test_resume_after_a_full_pause_starts_each_part_in_order():
    fake = Fake(endpoint=None, index=None, lakebase="STOPPED", app="STOPPED", warehouse="STOPPED")
    lines = []
    assert resume.resume(fake, NAMES, say=lines.append, sleep=fake.tick, clock=lambda: 0) == 0
    assert changes(fake) == [("make_endpoint", "strata-search", "STANDARD"), ("start_lakebase", "strata-state"),
                             ("start_app", "strata"), ("start_warehouse",),
                             ("make_index", "strata.gold.passage_index", "strata.gold.passage", 1024)]
    assert "   It is ready with 4154 rows." in lines
    assert f"6. Prism is running at {URL}" in lines
    assert "   strata nightly: PAUSED." in lines


def test_resume_when_everything_runs_changes_nothing():
    fake = Fake()
    lines = []
    assert resume.resume(fake, NAMES, say=lines.append, sleep=fake.tick, clock=lambda: 0) == 0
    assert changes(fake) == []
    assert "   It is online." in lines and "   It is available." in lines
    assert "   Its compute is active and the app is RUNNING." in lines


def test_resume_gives_up_when_the_endpoint_stays_offline():
    fake = Fake(endpoint="OFFLINE")
    minutes = itertools.count(0, 60 * 10)  # each read of the clock is ten minutes later
    lines = []
    assert resume.resume(fake, NAMES, say=lines.append, sleep=lambda s: None, clock=lambda: next(minutes)) == 2
    assert lines[-1].startswith("   The endpoint is OFFLINE after 40 minutes")
    assert resume.AGAIN in lines[-1]


def test_pause_stops_the_three_and_keeps_the_endpoint():
    fake = Fake()
    lines = []
    assert resume.pause(fake, NAMES, say=lines.append, sleep=fake.tick, clock=lambda: 0) == 0
    assert changes(fake) == [("stop_app", "strata"), ("stop_lakebase", "strata-state"), ("stop_warehouse",)]
    assert fake.endpoint_state == "ONLINE"
    assert any("--delete-search" in line for line in lines)
    assert "   It is STOPPED. Its data stays." in lines


def test_pause_with_delete_search_deletes_the_indexes_before_the_endpoint():
    fake = Fake(lakebase="STOPPED", app="STOPPED", warehouse="STOPPED")
    lines = []
    assert resume.pause(fake, NAMES, say=lines.append, delete_search=True, sleep=fake.tick, clock=lambda: 0) == 0
    assert changes(fake) == [("delete_index", INDEXES[0]), ("delete_index", INDEXES[1]),
                             ("delete_endpoint", "strata-search")]
    assert fake.endpoint_state is None
    assert "   Its compute is already stopped." in lines and "   It is already stopped." in lines


def test_status_reads_and_changes_nothing():
    fake = Fake(app="STOPPED", lakebase="STOPPED", warehouse="STOPPED")
    lines = []
    assert resume.status(fake, NAMES, say=lines.append) == 0
    assert changes(fake) == []
    assert "   The search endpoint strata-search: ONLINE." in lines
    assert "   The index strata.gold.passage_index: ready, 4154 rows." in lines
    assert "   The Lakebase instance strata-state: STOPPED." in lines
    assert "   The App strata: compute STOPPED, app UNAVAILABLE." in lines
    assert "   The SQL warehouse wh-1: STOPPED." in lines
    assert "   The job strata cost pull: PAUSED." in lines


def test_names_come_from_the_registries():
    found = resume.names()
    assert found == NAMES


def test_delete_search_needs_pause():
    with pytest.raises(SystemExit):
        resume.main(["--delete-search"], workspace=Fake())
