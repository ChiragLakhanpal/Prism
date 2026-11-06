"""The nightly job (seam 1): the bundle's tasks run in docs/PLAN.md section 11's order, and each
one records its run in strata.ops.pipeline_runs.

The local run reads the job from the bundle and calls the same entry point the job calls on
Databricks, with the same parameters, against DuckDB. The workspace step
`ops/bundle/check.py job-run` checks the same rows after a manual run on the workspace.
"""

import datetime as dt
import shutil
from pathlib import Path

import pytest
import yaml

from strata import config
from strata.lakehouse import bundle, catalog, nightly, schedule
from strata.lakehouse.engine import DuckDBEngine

# docs/PLAN.md section 11, "Nightly job", in its order: fetch by watermark, bronze to gold, parse and
# embed only what changed, sync the index, re-link, propose lessons, detect disagreements, score,
# measure data readiness, and refresh drafts that cite changed lessons.
PLAN_ORDER = [
    "fetch_by_watermark",
    "bronze_to_gold",
    "parse_and_embed",
    "sync_index",
    "relink",
    "propose_lessons",
    "detect_disagreements",
    "score",
    "measure_data_readiness",
    "refresh_drafts",
]

WASHINGTON = "America/New_York"
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def engine():
    with DuckDBEngine.open() as engine:
        catalog.build(engine)
        yield engine


def runs(engine, run_id):
    return engine.run("SELECT task_key, status, rows_changed, started_at, finished_at, public_from "
                      "FROM strata.ops.pipeline_runs WHERE run_id = :run_id ORDER BY started_at",
                      {"run_id": run_id}).rows


def test_the_job_runs_its_tasks_one_after_another_in_plan_order():
    tasks = nightly.job_tasks()

    assert [task.key for task in tasks] == PLAN_ORDER
    assert [task.depends_on for task in tasks] == [()] + [(key,) for key in PLAN_ORDER[:-1]]
    assert list(nightly.TASKS) == PLAN_ORDER  # so nightly.LAST_TASK is the task that ends the night


def no_pages(source, engine):
    return ()


# The tasks that change rows on a first run over the recorded fixture: every task but two. sync_index finds
# strata.gold.passage already equal to the passages, because the passage reader syncs it before it measures, and
# refresh_drafts finds no draft to mark (tests/test_refresh_drafts.py marks some). score scores every package's time
# estimate and counts the rebidding labels on every run, and scores rebidding only with a champion from the live
# MLflow.
WORKING = set(PLAN_ORDER) - {"sync_index", "refresh_drafts"}


def with_a_plan_read(engine, project_id="P156634"):
    """One Procurement Plan version of the project, as the plan reader leaves it. detect_disagreements rebuilds
    the assertions of the projects with documents or a plan read, and a local run over the recorded pages
    reads neither, so the row brings the project's contracts into the run."""
    engine.run("INSERT INTO strata.silver.plan_versions VALUES (:document_id, :project_id, 'NWWDA', DATE '2026-10-09', "
               "DATE '2026-10-09', 1, NULL, true, 12, 6, 'latest', 'text', 'pdf', DATE '2026-10-09')",
               {"document_id": "40132287", "project_id": project_id})


def test_a_run_of_the_job_writes_one_pipeline_run_row_per_task_in_plan_order(engine):
    with_a_plan_read(engine)
    run_id = nightly.run_locally(engine)  # over the recorded fixture

    rows = runs(engine, run_id)
    assert [row[0] for row in rows] == PLAN_ORDER
    assert {status for _, status, *_ in rows} == {"succeeded"}
    assert {task for task, _, changed, *_ in rows if changed > 0} == WORKING
    for _, _, _, started, finished, public_from in rows:
        assert started <= finished
        assert public_from == finished.astimezone(dt.UTC).date()


def test_the_disagreements_task_reads_the_records_assertions_and_asks_the_live_model_only_on_a_live_run(
        engine, monkeypatch):
    """detect_disagreements rebuilds the assertions and disagreements of every project with documents or a plan. A run
    that fetches from the live APIs asks the live batch model. When the job has no Azure OpenAI keys there is
    none, and the run replays the answers bronze holds from the batch role's deployment, so it keeps what the
    live model read. Any other run uses the recorded answers."""
    from strata.knowledge import batch

    asked, replayed = [], []

    class Replays(batch.HeldAnswers):
        def __init__(self, deployment=None):
            super().__init__(deployment)
            replayed.append(self.name)

    monkeypatch.setattr("strata.knowledge.batch.from_environment", lambda: asked.append("live"))
    monkeypatch.setattr("strata.knowledge.batch.HeldAnswers", Replays)
    with_a_plan_read(engine)
    nightly.run_locally(engine, readers_for=nightly.no_documents)  # the records' assertions need no document

    assert asked == [] and replayed == []
    held = engine.run("SELECT count(*) FROM strata.gold.assertion WHERE form = :form",
                      {"form": "contract_record"}).rows[0][0]
    assert held > 0

    nightly.main(["--task", "detect_disagreements", "--run-id", "2", "--src", "src"], engine)

    assert asked == ["live"]
    assert replayed == [config.load_models()["batch"].deployment]
    assert engine.run("SELECT count(*) FROM strata.gold.assertion WHERE form = :form",
                      {"form": "contract_record"}).rows[0][0] == held


def test_two_runs_keep_their_rows_apart(engine):
    first, second = nightly.run_locally(engine, fetch=no_pages), nightly.run_locally(engine, fetch=no_pages)

    assert first != second
    assert len(runs(engine, first)) == len(runs(engine, second)) == len(PLAN_ORDER)


def test_the_data_go_stale_a_day_and_a_half_after_the_last_night_that_finished(engine):
    """Briefs 06, 37 and 41: the freshness stamp and the stale alerts read when the job last finished its last task,
    after every quality check, against config/thresholds.toml's nightly.stale_after_hours (36)."""
    finished = dt.datetime(2026, 10, 24, 7, 30, tzinfo=dt.UTC)

    assert nightly.freshness(engine, finished) == nightly.Freshness(None, True)

    nightly.main(["--task", "refresh_drafts", "--run-id", "1", "--src", "src"], engine, no_pages, lambda: finished)

    assert nightly.freshness(engine, finished + dt.timedelta(hours=36)) == nightly.Freshness(finished, False)
    assert nightly.freshness(engine, finished + dt.timedelta(hours=37)).stale


def test_a_task_run_as_the_job_runs_it_fetches_from_the_live_apis(engine, monkeypatch):
    """nightly_task.py calls main() with the task's arguments and an engine, as this test does. With
    no fetch given, the task asks the live APIs, here a fake that records the URLs and has no rows."""
    asked = []

    def fake_fetch_url(url):
        asked.append(url)
        return b"{}"

    monkeypatch.setattr("strata.fixture.record.fetch_url", fake_fetch_url)

    nightly.main(["--task", "fetch_by_watermark", "--run-id", "1", "--src", "src"], engine)

    assert asked[0].startswith(config.load_sources()["awards"].endpoint)


def test_a_task_the_job_does_not_have_is_refused(engine):
    with pytest.raises(SystemExit, match="no task called polish_gold"):
        nightly.main(["--task", "polish_gold", "--run-id", "42", "--src", "/tmp/src"], engine, no_pages)

    assert engine.run("SELECT count(*) AS n FROM strata.ops.pipeline_runs").as_text() == [("0",)]


def test_the_job_s_name_comes_from_the_bundle(tmp_path):
    """The deploy and the checks find the job by this name, so renaming it in nightly.yml is enough."""
    shutil.copy(ROOT / "databricks.yml", tmp_path)
    shutil.copytree(ROOT / "bundle", tmp_path / "bundle")
    job_file = tmp_path / "bundle" / "nightly.yml"
    job_file.write_text(job_file.read_text().replace("name: strata nightly\n", "name: strata overnight\n"))

    assert nightly.job_name() == "strata nightly"
    assert nightly.job_name(bundle.load(tmp_path)) == "strata overnight"


def test_the_bundle_syncs_the_config_files_beside_the_package():
    # strata.config.CONFIG_DIR finds config/ beside src/, so the tasks read the source registry there.
    assert {"src", "config"} <= set(bundle.load().data["sync"]["paths"])


def test_the_jobs_entry_script_does_without_a_file_location():
    """Serverless Python tasks have no __file__ (docs/PLAN.md section 12), so the job passes --src."""
    script = Path(nightly.__file__).with_name("nightly_task.py").read_text()

    assert "__file__" not in script.replace('"__file__"', "")
    assert all("--src" in task.parameters for task in nightly.job_tasks())


def test_each_task_reads_its_keys_from_the_job_s_secret_scope_and_never_from_its_parameters():
    """A job reads its Azure OpenAI key from the secret scope (ops/dayone/dayone.toml), never from the env file or
    the job's parameters. A key the task's environment already holds stays as it is, and one the scope lacks is
    left out."""
    held = {"AZURE_OPENAI_ENDPOINT": "https://wb-strata.openai.azure.com/openai/v1",
            "AZURE_OPENAI_API_KEY": "not-a-real-key", "FOUNDRY_TENANT_ID": "from-the-scope"}

    def get(scope, key):
        if scope != "strata" or key not in held:
            raise LookupError(f"Secret does not exist with scope: {scope} and key: {key}")
        return held[key]

    environment = {"FOUNDRY_TENANT_ID": "already-set"}
    found = nightly.keys_from_scope(get, "strata", environment)

    assert found == ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY"]
    assert environment == {**held, "FOUNDRY_TENANT_ID": "already-set"}
    for task in nightly.job_tasks():
        assert task.parameters[task.parameters.index("--secret-scope") + 1] == "${var.secret_scope}"
    assert bundle.load().data["variables"]["secret_scope"]["default"] == "strata"


def test_sync_index_on_the_workspace_syncs_the_ai_search_index_the_bundle_names(engine, monkeypatch):
    """The AI Search endpoint is no secret, so the job passes it as a parameter from the bundle variable the deploy
    fills (review B4), and sync_index asks that index to sync from strata.gold.passage."""
    from strata.lakehouse import readers

    synced = []
    monkeypatch.setattr(readers, "_index", lambda endpoint: lambda engine: synced.append(endpoint))
    nightly.main(["--task", "sync_index", "--run-id", "1", "--src", "src", "--secret-scope", "strata",
                  "--search-endpoint", "strata-search"], engine)

    assert synced == ["strata-search"]
    for task in nightly.job_tasks():
        assert task.parameters[task.parameters.index("--search-endpoint") + 1] == "${var.ai_search_endpoint}"
    assert "AI_SEARCH_ENDPOINT" not in nightly.SCOPE_KEYS


@pytest.mark.parametrize("held, posted", [
    (False, ["/api/2.0/vector-search/indexes"]),
    (True, ["/api/2.0/vector-search/indexes/strata.gold.passage_index/sync"]),
])
def test_sync_index_makes_a_missing_index_without_asking_it_to_sync_and_syncs_one_it_finds(held, posted):
    """A new TRIGGERED Delta Sync index runs its first sync as it is made, and the workspace refuses a sync
    request while the index is still being made. So the job asks only an index it found to sync, as
    ops/documents/run_live.py does, and the first live night does not stop at sync_index (review r2 B1)."""
    from strata.lakehouse import readers

    requests, statements = [], []

    def workspace(method, path, body=None):
        requests.append((method, path))
        if method == "GET" and not held:
            raise LookupError("Vector search index strata.gold.passage_index does not exist")
        return {}

    class Engine:
        def run(self, sql):
            statements.append(sql)

    readers._index("strata-search", transport=workspace)(Engine())

    assert [path for method, path in requests if method == "POST"] == posted
    assert statements == ["ALTER TABLE strata.gold.passage SET TBLPROPERTIES (delta.enableChangeDataFeed = true)"]


def test_a_live_score_task_replays_the_signals_on_their_weekly_day_and_an_offline_one_does_not(engine, monkeypatch):
    """Ticket 37 left the signals' track record to the score task (strata.estimates.signals_track), and the hazard
    model's comparison with the signals shares its dates (strata.estimates.hazard). Both replay fixed past dates, so
    their counts change only when a newly fetched record turns out public before one of them, and both run once a
    week, on the night config/thresholds.toml names (signals.track_record_day), instead of filling the job's window
    every night (ticket 89). A record never replayed is replayed the first live night. A fake clock walks the nights
    from Monday, October 26, 2026 to Monday, November 2."""
    from strata.estimates import hazard, signals_track, tracking

    experiments = []

    class Tracker(tracking.OfflineTracker):
        def __init__(self, experiment, mkdirs=None):
            super().__init__()
            experiments.append(experiment)

    monkeypatch.setattr(tracking, "MlflowTracker", Tracker)
    first = dt.datetime(2026, 10, 26, 7, tzinfo=dt.UTC)  # 03:00 in Washington, a Monday

    nightly.main(["--task", "score", "--run-id", "offline", "--src", "src"], engine, no_pages, lambda: first)
    assert signals_track.stored(engine) is None and experiments == []

    # The offline run stored a comparison, so a live night that compares again shows as a new run id (ticket 89's
    # review, F2).
    nights = [first + dt.timedelta(days=n) for n in range(8)]
    replayed, compared, seen = [], [], (None, hazard.stored(engine)["run_id"])
    for night in nights:
        nightly.main(["--task", "score", "--run-id", f"{night:%m%d}", "--src", "src"], engine, clock=lambda: night)
        now = (signals_track.stored(engine)["run_id"], hazard.stored(engine)["run_id"])
        if now[0] != seen[0]:
            replayed.append(f"{night:%A %B} {night.day}")
        if now[1] != seen[1]:
            compared.append(f"{night:%A %B} {night.day}")
        seen = now

    # The nights each replay is due, from the day the thresholds file names, so moving the day is one edit there
    # (ticket 89's review, F3): the signals were never replayed, and the comparison last ran offline on the first night.
    day = config.load_thresholds().value("signals.track_record_day")
    assert day in schedule.WEEKDAYS

    def due(last):
        found = []
        for night in nights:
            if schedule.weekly_due(last, night.date(), day):
                found.append(f"{night:%A %B} {night.day}")
                last = night.date()
        return found

    assert replayed == due(None) and compared == due(first.date())
    assert replayed[0] == "Monday October 26" and compared[0] != "Monday October 26"
    assert config.load_time_estimate().experiment in experiments
    assert signals_track.stored(engine)["ran_on"] == "2026-11-01"
    assert runs(engine, "1101")[0][2] > runs(engine, "1031")[0][2]  # the replays' rows count as rows changed


# ── Concurrency ──────────────────────────────────────────────────────────

def test_the_job_never_runs_more_tasks_at_once_than_the_workspace_allows():
    """docs/PLAN.md section 2: the shared workspace runs five job tasks at once, for Prism and fairshare together.
    The tasks form one chain and the job allows one run at a time, so it never runs more than one."""
    allowed = config.load_thresholds().value("nightly.max_concurrent_tasks")

    assert (nightly.most_at_once(), allowed) == (1, 5)
    assert bundle.load().resources("jobs")[nightly.JOB]["max_concurrent_runs"] == 1


def test_a_job_whose_tasks_fan_out_past_the_limit_is_caught(tmp_path):
    """Six tasks that each wait only on the fetch could all run at once, one more than the workspace allows."""
    shutil.copy(ROOT / "databricks.yml", tmp_path)
    shutil.copytree(ROOT / "bundle", tmp_path / "bundle")
    job_file = tmp_path / "bundle" / "nightly.yml"
    declared = yaml.safe_load(job_file.read_text())
    for task in declared["resources"]["jobs"]["nightly"]["tasks"]:
        if task["task_key"] in ("sync_index", "relink", "propose_lessons", "detect_disagreements", "score"):
            task["depends_on"] = [{"task_key": "bronze_to_gold"}]
    job_file.write_text(yaml.safe_dump(declared))

    assert nightly.most_at_once(bundle.load(tmp_path)) == 6


# ── The window ───────────────────────────────────────────────────────────

def days_of_a_year():
    start = dt.date(2026, 10, 23)
    return [start + dt.timedelta(days=n) for n in range(366)]


def test_the_window_starts_at_three_in_the_morning_in_washington_and_lasts_two_and_a_half_hours():
    window = nightly.window()

    assert (window.start, window.timezone, window.minutes) == (dt.time(3, 0), WASHINGTON, 150)


def test_the_window_misses_fairshare_s_job_at_six_in_chicago_even_if_it_ran_four_hours():
    """fairshare's job runs at 06:00 in Chicago, 07:00 in Washington; its longest run took 21 minutes."""
    fairshare = schedule.Window("fairshare nightly", dt.time(6, 0), "America/Chicago", 240)

    assert schedule.overlapping_days(nightly.window(), fairshare, days_of_a_year()) == []


@pytest.mark.parametrize("hour", [18, 19, 20, 21, 22])
def test_the_window_misses_a_four_hour_job_that_starts_any_evening_hour_in_washington(hour):
    """23:00 is left out: on the night the clocks go forward, four hours from 23:00 end at 04:00."""
    other = schedule.Window("an evening job", dt.time(hour, 0), WASHINGTON, 240)

    assert schedule.overlapping_days(nightly.window(), other, days_of_a_year()) == []


def test_the_window_misses_a_four_hour_job_that_starts_at_midnight_utc():
    other = schedule.Window("a midnight UTC job", dt.time(0, 0), "UTC", 240)

    assert schedule.overlapping_days(nightly.window(), other, days_of_a_year()) == []


def test_the_window_ends_before_review_hours_in_washington():
    review_hours = schedule.Window("review hours", dt.time(8, 0), WASHINGTON, 600)

    assert schedule.overlapping_days(nightly.window(), review_hours, days_of_a_year()) == []


def test_a_job_that_runs_into_the_window_is_caught():
    other = schedule.Window("an eight-hour evening job", dt.time(23, 0), WASHINGTON, 480)

    assert len(schedule.overlapping_days(nightly.window(), other, days_of_a_year())) == 366


def test_midnight_utc_moves_against_washington_time_and_the_check_follows_it():
    """Midnight UTC is 20:00 in Washington in summer and 19:00 in winter; check both sides of the change.

    A seven-and-a-half-hour job from midnight UTC ends at 03:30 in summer, inside the window, and
    at 02:30 in winter, before it. A seven-hour job ends at 03:00 in summer, as the window opens.
    """
    days = [dt.date(2026, 10, 30), dt.date(2026, 11, 2)]
    seven = schedule.Window("a seven-hour job at midnight UTC", dt.time(0, 0), "UTC", 7 * 60)
    longer = schedule.Window("a seven-and-a-half-hour job at midnight UTC", dt.time(0, 0), "UTC", 450)

    assert schedule.overlapping_days(nightly.window(), seven, days) == []
    assert schedule.overlapping_days(nightly.window(), longer, days) == [dt.date(2026, 10, 30)]
