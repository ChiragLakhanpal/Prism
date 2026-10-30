"""The assertions pass reads the SQL warehouse within its inline limit, and ops/assertions/batch_live.py runs it for
the projects it is given: seam 1, the pass over the fixture (ticket 135).

On October 29, 2026 the owner ran ops/assertions/batch_live.py on the workspace and it stopped at once: "Inline byte
limit exceeded. Statements executed with disposition=INLINE can have a result size of at most 26214400 bytes." The
pass read each family of rows with one statement for every project the workspace holds. Here the fixture plays a
workspace bigger than the limit: it holds the contracts of many projects the run does not read, and a warehouse
that refuses any result over a small limit, as the workspace refuses one over 25 MiB.
"""

import importlib.util
import json
import shutil
import sys
import types
from pathlib import Path

import pytest
from warehouse_over_fixture import WarehouseOverFixture

from strata.knowledge import assertions, batch
from strata.lakehouse.engine import DuckDBEngine, EngineError, WarehouseEngine

ROOT = Path(__file__).resolve().parents[1]
# The limit this warehouse keeps, scaled down from the workspace's 26,214,400 bytes as the fixture is scaled down
# from the workspace: above what any one project's rows or any one report's passages can take, below what the run's
# assertions, its reports' passages and the contracts of every project take together.
SMALL_CAP = 600_000
COPIES = 40  # projects the run does not read, each with a copy of P176758's contracts
REFUSAL = ("Inline byte limit exceeded. Statements executed with disposition=INLINE can have a result size of at "
           "most {cap} bytes.")
TABLES = ("SELECT * FROM strata.gold.assertion ORDER BY assertion_id",
          "SELECT * FROM strata.gold.disagreement ORDER BY disagreement_id")


class CappedWarehouse(WarehouseOverFixture):
    """The SQL warehouse over a copy of the fixture, which refuses a statement whose result passes its limit, with
    the workspace's own words, and keeps the bytes of each result it returned."""

    def __init__(self, database: Path, cap: int):
        super().__init__(database)
        self.cap, self.sizes, self.refused = cap, [], []

    def _answer(self, fixture, body):
        reply = super()._answer(fixture, body)
        size = len(json.dumps((reply.get("result") or {}).get("data_array") or []).encode())
        if size > self.cap:
            self.refused.append(body["statement"])
            return {"statement_id": reply["statement_id"],
                    "status": {"state": "FAILED", "error": {"message": REFUSAL.format(cap=self.cap)}}}
        self.sizes.append((body["statement"], size))
        return reply

    def engine(self, fixture: DuckDBEngine) -> WarehouseEngine:
        return WarehouseEngine("fixture", lambda method, path, body: self.answer(fixture, method, path, body),
                               result_bytes=self.cap)


def grown(fixture_db: Path, folder: Path) -> Path:
    """A copy of the fixture whose gold.contract also holds COPIES projects the run does not read, each with its own
    copy of P176758's contracts, as the workspace holds the contracts of every project the World Bank has."""
    copy = folder / "workspace.duckdb"
    shutil.copy(fixture_db, copy)
    with DuckDBEngine.open(copy) as workspace:
        for number in range(COPIES):
            workspace.run("INSERT INTO strata.gold.contract SELECT * REPLACE ("
                          ":project_id AS project_id, contract_id || :suffix AS contract_id, "
                          "step_reference || :suffix AS step_reference) "
                          "FROM strata.gold.contract WHERE project_id = :template",
                          {"project_id": f"P9{number:05d}", "suffix": f"-{number}", "template": "P176758"})
    return copy


def held(engine) -> list[list[tuple]]:
    return [engine.run(sql).rows for sql in TABLES]


def test_the_pass_reads_a_workspace_bigger_than_the_limit_in_parts_and_keeps_what_one_read_gave(
        fixture_db, tmp_path, monkeypatch):
    """The nightly run reads every project the workspace holds in each statement (NAMED_MAX). Over this workspace one
    such statement passes the warehouse's limit and is refused, as on October 29; the pass measures each family
    first and reads it in parts that fit, so it finishes with no statement refused, and it finds every assertion
    and disagreement the fixture's own run wrote, changing no row."""
    monkeypatch.setattr(assertions, "NAMED_MAX", 2)  # the fixture's eight projects take the workspace's path
    copy = grown(fixture_db, tmp_path)
    with DuckDBEngine.open(fixture_db, read_only=True) as fixture:
        projects = assertions.default_projects(fixture)
        written = held(fixture)
    warehouse = CappedWarehouse(copy, SMALL_CAP)

    with DuckDBEngine.open(copy) as workspace:
        unaware = warehouse.engine(workspace)
        unaware.result_bytes = None  # an engine that does not know the limit reads each family in one statement
        with pytest.raises(EngineError, match="Inline byte limit exceeded"):
            assertions.run(unaware, projects, model=batch.RecordedBatch(), run_id="as-on-october-29")
        [refused] = warehouse.refused
        assert "AS signed_on" in refused  # the records of every project, in one statement
        warehouse.refused.clear()

        report = assertions.run(warehouse.engine(workspace), projects, model=batch.RecordedBatch(), run_id="capped")
        after = held(workspace)

    assert warehouse.refused == []
    assert max(size for _, size in warehouse.sizes) <= SMALL_CAP
    reads = [statement for statement, _ in warehouse.sizes if "part_bytes" not in statement]
    assert len([read for read in reads if "p.section_path" in read]) > 1  # the reports' passages, in parts
    assert len([read for read in reads if read.startswith("SELECT assertion_id")]) > 1  # the assertions held, in parts
    assert (report.assertions, report.disagreements) == (len(written[0]), len(written[1]))
    assert report.changed == 0 and report.left_out == ()
    assert after == written


# ── ops/assertions/batch_live.py --projects ──

ENV = {"DATABRICKS_HOST": "https://example.cloud.databricks.com", "DATABRICKS_WAREHOUSE_ID": "0123456789abcdef",
       "DATABRICKS_TOKEN": "not-a-real-key", "AZURE_OPENAI_ENDPOINT": "https://wb-strata.openai.azure.com/openai/v1",
       "AZURE_OPENAI_API_KEY": "not-a-real-key-either"}
REBUILT = ("strata.gold.assertion", "strata.gold.disagreement", "strata.ops.assertion_rejections")
BY_PROJECT = """SELECT project_id, count(*) AS assertions,
  count_if(read_by = 'isr_ratings') AS isr, count_if(evidence_tier = 'record') AS records,
  count_if(read_by = 'strata.gold.ieg_rating') AS ieg
FROM strata.gold.assertion GROUP BY project_id"""


@pytest.fixture
def batch_live(monkeypatch):
    """ops/assertions/batch_live.py as a module, as uv runs it; sys.path goes back after."""
    monkeypatch.setattr(sys, "path", list(sys.path))
    spec = importlib.util.spec_from_file_location("strata_ops_assertions_batch_live",
                                                  ROOT / "ops" / "assertions" / "batch_live.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def by_project(engine) -> dict[str, tuple]:
    return {row[0]: row[1:] for row in engine.run(BY_PROJECT).rows}


def test_batch_live_runs_the_pass_for_the_projects_it_is_given_and_says_what_each_became(
        batch_live, fixture_db, tmp_path, monkeypatch, capsys):
    """The owner's command for the demo projects: --projects names them, the pass rebuilds their assertions and no
    other project's, and it prints for each project what became assertions and what went to the batch model. Without
    --projects the run is the nightly's, over every project with documents or records."""
    copy = tmp_path / "workspace.duckdb"
    shutil.copy(fixture_db, copy)
    env_file = tmp_path / "workspace.env"
    env_file.write_text("".join(f"{key}={value}\n" for key, value in ENV.items()))
    with DuckDBEngine.open(fixture_db, read_only=True) as fixture:
        written = by_project(fixture)
    with DuckDBEngine.open(copy) as engine:
        for table in REBUILT:
            engine.run(f"DELETE FROM {table} WHERE project_id IS NOT NULL")
        monkeypatch.setitem(sys.modules, "bundle_live", types.SimpleNamespace(
            LiveWorkspace=lambda env: types.SimpleNamespace(engine=lambda: engine)))
        monkeypatch.setattr(batch, "from_environment", lambda env: batch.RecordedBatch())
        monkeypatch.setattr(batch_live, "WarehouseEngine", lambda *args, **kwargs: engine)  # the viewer's warehouse
        monkeypatch.setattr(batch_live, "http_transport", lambda *args, **kwargs: None)

        scoped = batch_live.main(["--env-file", str(env_file), "--projects", "P130164, P176758"])
        after_scoped = by_project(engine)
        printed = capsys.readouterr().out
        every = batch_live.main(["--env-file", str(env_file)])
        after_every = by_project(engine)

    assert scoped == every == 0  # and the showcase disagreement came back
    assert after_scoped == {project_id: written[project_id] for project_id in ("P130164", "P176758")}
    for project_id in ("P130164", "P176758"):
        total, isr, records, ieg = written[project_id]
        assert (f"{project_id}: {total} assertions ({isr} from ISR ratings, {records} from records, {ieg} from the IEG "
                f"ratings dataset, {total - isr - records - ieg} read from reports)") in printed, printed
    assert "P176758 has no report for the batch model." in printed
    assert "Of P130164's 4 reports, the batch model had answered 4 before, 0 went to it in this run" in printed
    assert after_every == written  # the nightly's default: every project with documents or records
