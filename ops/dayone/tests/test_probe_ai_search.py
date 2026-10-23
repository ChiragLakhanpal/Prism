"""The AI Search probe (test 4): an endpoint, a hybrid index of passages, and one hybrid query."""

import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_ai_search  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402

from strata.config import load_models  # noqa: E402

RESULTS = REPO / "docs" / "day-one-results.md"


class FakeSearch:
    def __init__(self, state="ONLINE", ready=True, rows=None, refuse_at=None, setup_fails_at=None):
        self.state, self.ready, self.refuse_at, self.setup_fails_at = state, ready, refuse_at, setup_fails_at
        self.rows = rows if rows is not None else [["p1", "The contracts were advertised again.", 0.03]]
        self.calls = []

    def _maybe_refuse(self, name):
        if self.setup_fails_at == name:
            raise SetupError(f"Running \"CREATE TABLE IF NOT EXISTS ...\" on the warehouse failed: {name} PERMISSION_DENIED")
        if self.refuse_at == name:
            raise ProbeError(f"{name} failed: RESOURCE_EXHAUSTED")

    def ensure_endpoint(self, name):
        self.calls.append(("endpoint", name))
        self._maybe_refuse("endpoint")
        return self.state

    def ensure_index(self, endpoint, table, index, dimensions, passages):
        self.calls.append(("index", endpoint, table, index, dimensions, len(passages)))
        self._maybe_refuse("index")
        return {"ready": self.ready, "rows": len(passages) if self.ready else 0, "message": "Index is syncing."}

    def hybrid_query(self, index, text, vector):
        self.calls.append(("query", index, text, len(vector)))
        self._maybe_refuse("query")
        return self.rows


@pytest.fixture
def place(tmp_path):
    shutil.copy(RESULTS, tmp_path / "results.md")
    (tmp_path / "probe.env").write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n"
                                        "DATABRICKS_TOKEN='dapi-x'\nDATABRICKS_WAREHOUSE_ID='wh1'\n"
                                        "AI_SEARCH_ENDPOINT='strata-search'\n")
    return tmp_path


def run(place, search):
    code = probe_ai_search.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                                service=search)
    return code, dayone.read_results(place / "results.md")["test-4"]


def test_an_online_endpoint_and_a_hybrid_answer_pass(place):
    size = load_models()["embed"].dimensions
    search = FakeSearch()
    code, test4 = run(place, search)
    assert code == 0
    assert test4["Status"] == "passed"
    assert search.calls[0] == ("endpoint", "strata-search")
    assert search.calls[1][1:] == ("strata-search", "workspace.strata_dayone.passages",
                                   "workspace.strata_dayone.passages_index", size, 3)
    assert search.calls[2][3] == size
    assert any("p1" in line for line in test4["Evidence"])


def test_an_endpoint_that_never_comes_online_fails(place):
    search = FakeSearch(state="PROVISIONING")
    code, test4 = run(place, search)
    assert code == 1
    assert test4["Status"] == "failed"
    assert "PROVISIONING" in test4["Result"]
    assert [call[0] for call in search.calls] == ["endpoint"]


def test_an_index_that_is_not_ready_fails(place):
    code, test4 = run(place, FakeSearch(ready=False))
    assert test4["Status"] == "failed"
    assert any("Index is syncing." in line for line in test4["Evidence"])


def test_a_refused_hybrid_query_fails_with_its_reason(place):
    code, test4 = run(place, FakeSearch(refuse_at="query"))
    assert test4["Status"] == "failed"
    assert test4["Chosen path"].startswith("Undecided")
    assert any("RESOURCE_EXHAUSTED" in line for line in test4["Evidence"])


def test_a_hybrid_query_with_no_rows_fails(place):
    code, test4 = run(place, FakeSearch(rows=[]))
    assert test4["Status"] == "failed"


def test_a_passage_table_the_warehouse_refuses_leaves_test_4_not_run(place):
    code, test4 = run(place, FakeSearch(setup_fails_at="index"))
    assert code == 1
    assert test4["Status"] == "not run"
    assert any("Endpoint strata-search: ONLINE" in line for line in test4["Evidence"])
    assert any("PERMISSION_DENIED" in line for line in test4["Evidence"])


def test_the_result_counts_passages_in_words_and_says_whether_the_index_is_ready(place):
    three = [["p1", "a", 0.03], ["p2", "b", 0.02], ["p3", "c", 0.01]]
    code, test4 = run(place, FakeSearch(rows=three))
    assert "with three passages" in test4["Result"]
    index_line = next(line for line in test4["Evidence"] if line.startswith("Index "))
    assert ": ready, three rows" in index_line and "True" not in index_line
    code, test4 = run(place, FakeSearch())
    assert "with one passage." in test4["Result"]
