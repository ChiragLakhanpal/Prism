"""The discrete-time hazard model for project delay early warning (ticket 44; docs/PLAN.md section 7) at seam 5: it
scores in shadow beside the fixed signals, nightly, and the replay harness compares the two on what happened next,
a later closing-date extension within the signals' follow-up window (brief 37). No tool, route or copy key shows it.

The hand-made set is 24 projects with loan histories, built so the answer is known: eight have moved their closing
date twice and close in two years, so the closing date check picks them out, and none extends again; eight have moved it
once and close in six months, and all of them extend; eight close in over five years and never move it. A model of
time to closing ranks the second eight first; the fixed signals pick the first eight.
"""

import datetime as dt
import json
import shutil
from pathlib import Path

import pytest

from strata.estimates import hazard
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
REPLAYED = dt.date(2024, 6, 30)
MOVED_TWICE = [f"P9100{n:02d}" for n in range(8)]  # moved twice, close in two years, never extend again
EXTEND = [f"P9101{n:02d}" for n in range(8)]  # moved once, close in six months, extend
QUIET = [f"P9102{n:02d}" for n in range(8)]  # close in over five years, never move


def history(project, *moves):
    """A project's loan history: its first month, then each month its closing date changed."""
    first, closing = moves[0]
    found = [{"project_id": project, "closing_date": closing, "previous_closing_date": None, "reported_on": first,
              "public_from": first}]
    for reported, moved_to in moves[1:]:
        found.append({"project_id": project, "closing_date": moved_to, "previous_closing_date": closing,
                      "reported_on": reported, "public_from": reported})
        closing = moved_to
    return found


def insert(engine, table, items):
    columns = tuple(items[0])
    engine.insert_rows(table, columns, [tuple(item[column] for column in columns) for item in items])


@pytest.fixture(scope="module")
def hand_made(tmp_path_factory):
    from strata.lakehouse import catalog

    path = tmp_path_factory.mktemp("hazard") / "hand-made.duckdb"
    start = dt.date(2015, 1, 31)
    rows, projects = [], []
    for project in MOVED_TWICE:
        rows += history(project, (start, dt.date(2019, 6, 30)), (dt.date(2018, 12, 31), dt.date(2021, 6, 30)),
                        (dt.date(2020, 12, 31), dt.date(2026, 6, 30)))
    for project in EXTEND:
        rows += history(project, (start, dt.date(2022, 12, 31)), (dt.date(2023, 1, 31), dt.date(2024, 12, 31)),
                        (dt.date(2024, 10, 31), dt.date(2025, 12, 31)))
    for project in QUIET:
        rows += history(project, (start, dt.date(2029, 12, 31)))
    for project in MOVED_TWICE + EXTEND + QUIET:
        projects.append({"project_id": project, "project_name": f"Hand-made project {project}", "country_code": "KE",
                         "status": "Active", "closing_date": dt.date(2029, 12, 31), "public_from": dt.date(2015, 1, 1)})
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
        insert(engine, "strata.gold.project_closing_date", rows)
        insert(engine, "strata.gold.project", projects)
    return path


def test_the_replay_harness_compares_the_hazard_model_with_the_fixed_signals_on_later_extensions(hand_made, tmp_path):
    path = tmp_path / "compared.duckdb"
    shutil.copy(hand_made, path)
    with DuckDBEngine.open(path) as engine:
        hazard.compare(engine, OfflineTracker(), ran_at=dt.datetime(2026, 10, 24, 9, tzinfo=dt.UTC), dates=(REPLAYED,))
        record = hazard.stored(engine)

    # The signals picked the eight that moved twice, and none of them extended; the model, picking as many, chose
    # the eight that close in six months, and all eight extended. McNemar's exact test on the eight discordant
    # projects: 2 x (1/2)^8 = 0.0078125, stored to six decimals.
    assert (record["cohort"], record["signals_picked"], record["extended"]) == (24, 8, 8)
    assert (record["signals_caught"], record["hazard_caught"]) == (0, 8)
    assert (record["signals_only"], record["hazard_only"]) == (0, 8)
    assert record["mcnemar_p"] == pytest.approx(0.0078125, abs=1e-6)
    assert record["beats"] == 1
    assert json.loads(record["dates"]) == [REPLAYED.isoformat()]


def test_the_hazard_model_scores_every_open_project_in_shadow_with_a_model_trained_on_earlier_periods(hand_made, tmp_path):
    path = tmp_path / "shadow.duckdb"
    shutil.copy(hand_made, path)
    night = dt.datetime(2024, 7, 1, 9, tzinfo=dt.UTC)
    with DuckDBEngine.open(path) as engine:
        written = hazard.score_in_shadow(engine, "night-1", night)
        scores = {row[0]: row[1:] for row in engine.run(
            "SELECT project_id, hazard, abstention, model FROM strata.ops.hazard_scores").rows}

    assert written == 24 and set(scores) == set(MOVED_TWICE + EXTEND + QUIET)
    assert all(abstention is None and model == "hazard-2024-07-01" for _, abstention, model in scores.values())
    assert min(scores[project][0] for project in EXTEND) > max(scores[project][0] for project in MOVED_TWICE + QUIET)


def test_the_nightly_score_task_stores_the_hazard_scores_and_the_comparison_on_the_fixture(fixture_db, tmp_path):
    from strata.lakehouse import nightly

    path = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, path)
    # A week after the fixture's own run, so the weekly comparison is due again (signals.track_record_every_days).
    night = dt.datetime(2026, 10, 30, 9, tzinfo=dt.UTC)
    with DuckDBEngine.open(path) as engine:
        nightly.run_task(engine, "score", "night-2", nightly.fetch_recorded, clock=lambda: night)
        scored = engine.run("SELECT count(*), min(model) FROM strata.ops.hazard_scores WHERE run_id = 'night-2'").rows[0]
        compared = hazard.stored(engine)

    # Every open project with a loan history is scored, with the model trained that night or its abstention.
    assert scored == (1, "hazard-2026-10-30")
    assert compared["ran_at"].replace(tzinfo=dt.UTC) == night and compared["run_id"].startswith(hazard.SCORER)


def test_no_tool_route_or_copy_shows_the_hazard_model():
    from strata.config import load_tools
    from strata.server.app import create_app

    app = create_app(engine_for=lambda viewer: None)
    paths = [getattr(route, "path", "") for route in app.routes]
    tools = load_tools()
    copy = (ROOT / "web" / "src" / "copy.ts").read_text().lower()
    server = " ".join(path.read_text() for path in (ROOT / "src" / "strata" / "server").glob("*.py"))
    tool_files = [*(ROOT / "src" / "strata" / "tools").rglob("*.py"), *(ROOT / "src" / "strata" / "tools").rglob("*.sql")]
    reads = " ".join(path.read_text() for path in tool_files).lower()

    assert not [path for path in paths if "hazard" in path]
    assert not [name for name, tool in tools.items() if "hazard" in f"{name} {tool.description} {tool.adapter}".lower()]
    assert "hazard" not in copy
    assert "hazard_scores" not in server and "hazard" not in reads


@pytest.mark.parametrize("margin, chance", [(-1000.0, 0.0), (1000.0, 1.0), (0.0, 0.5)])
def test_a_chance_far_from_the_middle_is_close_to_none_or_all_and_never_overflows(margin, chance):
    model = hazard.HazardModel((margin, 0.0, 0.0, 0.0), dt.date(2026, 1, 1), 40)

    found = model.chance({"moves": 1, "years_to_close": 2.0, "years_since_move": 1.0})

    assert found == pytest.approx(chance)
