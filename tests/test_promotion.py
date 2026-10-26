"""Promoting a challenger to champion (ticket 44; docs/PLAN.md section 11, the estimates loop's gate) at seam 5: the
promotion reads the replay harness's stored backtests, the shadow quarter's scores and the sign-offs, and refuses
unless the challenger won the backtest and the shadow quarter, held coverage for each edition, and carries a
sign-off from the model owner and from the lead. With all four it moves the champion alias, in Unity Catalog's
stand-in (the offline tracker) and in strata.gold.time_estimate_model, which the score task and the app read.

The seeded results are made up and small: each expected outcome follows from how they are made, never from the
code. The people are made up too, with the reserved example domain.
"""

import dataclasses
import datetime as dt
import json
import shutil

import pytest

from strata.config import Person, load_roles
from strata.estimates import backtest, harness, promotion
from strata.estimates.tracking import OfflineTracker
from strata.lakehouse.engine import DuckDBEngine

MODEL = "strata.gold.time_estimate"  # config/models.toml's registered_model
OWNER, LEAD = "model.owner@worldbank.example", "lead.specialist@worldbank.example"
DECIDED = dt.datetime(2026, 10, 1, 9, tzinfo=dt.UTC)
SHADOW_FROM = dt.date(2026, 6, 2)  # the challenger's first night in shadow: four months before DECIDED
DAY = dt.timedelta(days=1)
EDITION = "guidelines_2011"  # config/editions.toml


def roles():
    """The roles file, with a made-up model owner and a made-up lead procurement specialist."""
    return dataclasses.replace(load_roles(), people=(
        Person(OWNER, "Model Owner", ("model_owner",), (), ()),
        Person(LEAD, "Lead Specialist", ("lead_procurement_specialist",), ("South Asia",), ())))


def insert(engine, table, items):
    columns = tuple(items[0])
    engine.insert_rows(table, columns, [tuple(item[column] for column in columns) for item in items])


def store_backtest(engine, run_id, version, errors, n=40, m=32, editions=None, ran_at=dt.datetime(2026, 5, 1, tzinfo=dt.UTC)):
    """A backtest run that registered a version, with each test year's counts and typical error, and the counts per
    edition its packages followed, as backtest.run stores them."""
    scorer = backtest.TimeEstimateBacktest(backtest.load_time_estimate())
    found = []
    for year, error in zip((2024, 2025), errors):
        window = harness.Window(dt.date(year, 1, 1), dt.date(2026, 4, 30), backtest.TEST_YEAR, str(year))
        scores = [harness.Score("n", n), harness.Score("m", m), harness.Score("expected", round(0.8 * n)),
                  harness.Score("error_estimate_months", error)]
        scores += [harness.Score(f"edition.{key}.{measure}", value) for key, counts in (editions or {}).items()
                   for measure, value in zip(("n", "m"), counts)]
        found += [harness.row(run_id, scorer, window, score, f"mlflow-{run_id}", ran_at) for score in scores]
    registered = harness.Window(ran_at.date(), ran_at.date(), backtest.REGISTERED, str(version))
    found.append(harness.row(run_id, scorer, registered, harness.Score("version", version), f"mlflow-{run_id}", ran_at))
    harness.write(engine, found)


def kept(version, alias, registered_on):
    return {"model": MODEL, "version": version, "alias": alias, "training_through": registered_on, "booster_json": "{}",
            "state_json": "{}", "mlflow_run_id": f"mlflow-{version}",
            "registered_at": dt.datetime.combine(registered_on, dt.time(6), dt.UTC), "public_from": registered_on}


@pytest.fixture(scope="module")
def empty_catalog(tmp_path_factory):
    from strata.lakehouse import catalog

    path = tmp_path_factory.mktemp("promotion") / "empty.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


@pytest.fixture
def ready(empty_catalog, tmp_path):
    """A challenger, version 2, that won everything: a lower typical error than the champion, version 1, in both
    test years with 64 of 80 unseen packages inside its 8-in-10 range; 24 of 30 inside it for the projects that
    followed the 2011 Guidelines; and, over four months in shadow, a typical error of 3 days on 20 packages that
    signed, against the champion's 28. Both sign-offs are not given yet."""
    path = tmp_path / "ready.duckdb"
    shutil.copy(empty_catalog, path)
    with DuckDBEngine.open(path) as engine:
        store_backtest(engine, "backtest-1", 1, (3.0, 3.2), ran_at=dt.datetime(2025, 12, 1, tzinfo=dt.UTC))
        store_backtest(engine, "backtest-2", 2, (2.6, 2.8), editions={EDITION: (15, 12), "none": (25, 20)})
        insert(engine, "strata.gold.time_estimate_model", [kept(1, "champion", dt.date(2025, 12, 1)),
                                                            kept(2, "challenger", dt.date(2026, 6, 1))])
        packages, champion, challenger = [], [], []
        for n in range(20):
            notice = dt.date(2026, 5, 1) + n * DAY
            reference = f"KE-S-{n}"
            packages.append({"step_reference": reference, "project_id": "P900044", "country_code": "KE",
                             "first_notice_date": notice, "contract_signed_on": notice + 92 * DAY, "contract_count": 1,
                             "public_from": notice})
            scored = dt.datetime.combine(SHADOW_FROM + 3 * DAY, dt.time(9), dt.UTC)
            champion.append({"step_reference": reference, "run_id": "night-1", "as_described": True, "q50_days": 120,
                             "q80_days": 150, "model": MODEL, "model_version": 1, "model_alias": "champion",
                             "training_through": dt.date(2025, 12, 1), "scored_at": scored, "public_from": scored.date()})
            challenger.append({"step_reference": reference, "run_id": "night-1", "model": MODEL, "model_version": 2,
                               "q50_days": 95, "q80_days": 130, "scored_at": scored, "public_from": scored.date()})
        insert(engine, "strata.gold.package", packages)
        insert(engine, "strata.gold.time_estimate_score", champion)
        insert(engine, "strata.ops.time_estimate_shadow", challenger)
        # The first night in shadow, a package that signed before the quarter began: it is not compared.
        insert(engine, "strata.ops.time_estimate_shadow", [{**challenger[0], "step_reference": "KE-S-early",
                                                            "scored_at": dt.datetime.combine(SHADOW_FROM, dt.time(9), dt.UTC),
                                                            "public_from": SHADOW_FROM}])
    return path


def registry():
    """Unity Catalog's stand-in with both versions registered, the champion alias on version 1."""
    tracker = OfflineTracker()
    for _ in (1, 2):
        tracker.register(tracker.start_run("time_estimate model", {}), MODEL, "card", "summary")
    tracker.set_alias(MODEL, "champion", 1)
    tracker.set_alias(MODEL, "challenger", 2)
    return tracker


def sign_both(engine, owner=OWNER, lead=LEAD):
    promotion.sign_off(engine, roles(), owner, MODEL, 2, "model_owner", DECIDED - DAY)
    promotion.sign_off(engine, roles(), lead, MODEL, 2, "lead", DECIDED - DAY)


def champion_kept(engine) -> int:
    return int(engine.run("SELECT version FROM strata.gold.time_estimate_model WHERE alias = 'champion' "
                          "ORDER BY registered_at DESC LIMIT 1").rows[0][0])


def test_with_all_four_the_challenger_is_promoted_and_the_champion_alias_moves(ready):
    tracker = registry()
    with DuckDBEngine.open(ready) as engine:
        sign_both(engine)
        decision = promotion.promote(engine, tracker, MODEL, 2, DECIDED, roles=roles())
        stored = engine.run("SELECT promoted, refusals, champion_version FROM strata.ops.model_promotions").rows
        now_champion = champion_kept(engine)

    assert (decision.promoted, decision.refusals) == (True, ())
    assert tracker.alias_version(MODEL, "champion") == 2 and now_champion == 2
    assert stored == ((True, "[]", 1),)
    assert decision.evidence["shadow"]["packages"] == 20
    assert decision.evidence["editions"][EDITION] == {"n": 30, "m": 24, "judged": True, "inside": True}


def track_record_shown(engine) -> dict:
    """The track record the time estimate reports beside its answer, as of the day after DECIDED."""
    from strata.dbx import Viewer
    from strata.tools import registry

    viewer = Viewer(email="ana.example@worldbank.org", name="Ana Example", token="token-for-ana-only")
    result = registry.call("estimate_time", {"method": "Request for Bids", "category": "Works", "country": "KE",
                                             "as_of": (DECIDED + DAY).date().isoformat()},
                           registry.Context(engine=engine, viewer=viewer))
    return result["track_record"]


def test_the_time_estimate_reports_the_champions_track_record_until_the_challenger_is_promoted(ready):
    tracker = registry()
    with DuckDBEngine.open(ready) as engine:
        # The challenger's backtest is newer than the champion's and counted 50 unseen packages, not 40.
        engine.run("DELETE FROM strata.ops.evaluation_result WHERE run_id = :run_id", {"run_id": "backtest-2"})
        store_backtest(engine, "backtest-2", 2, (2.6, 2.8), n=50, m=40, editions={EDITION: (15, 12), "none": (35, 28)})
        before = track_record_shown(engine)
        sign_both(engine)
        promoted = promotion.promote(engine, tracker, MODEL, 2, DECIDED, roles=roles()).promoted
        after = track_record_shown(engine)

    assert (before["n"], before["m"], before["mlflow_run_id"]) == (40, 32, "mlflow-backtest-1")
    assert promoted
    assert (after["n"], after["m"], after["mlflow_run_id"]) == (50, 40, "mlflow-backtest-2")


def worse_backtest(engine):
    engine.run("DELETE FROM strata.ops.evaluation_result WHERE run_id = :run_id", {"run_id": "backtest-2"})
    store_backtest(engine, "backtest-2", 2, (3.5, 3.6), editions={EDITION: (15, 12)})


def too_short_in_shadow(engine):
    pass  # decided on September 1, below: all 20 packages signed by August 20, but the quarter from June 2 ends September 2


def edition_outside(engine):
    engine.run("DELETE FROM strata.ops.evaluation_result WHERE run_id = :run_id", {"run_id": "backtest-2"})
    store_backtest(engine, "backtest-2", 2, (2.6, 2.8), editions={EDITION: (15, 6)})


@pytest.mark.parametrize("change, decided, refusals", [
    (worse_backtest, DECIDED, ("no_backtest_win",)),
    (too_short_in_shadow, dt.datetime(2026, 9, 1, 9, tzinfo=dt.UTC), ("no_shadow_win",)),
    (edition_outside, DECIDED, ("edition_coverage",)),
], ids=["lost the backtest", "under a quarter in shadow", "an edition outside the band"])
def test_a_challenger_that_lacks_one_win_is_refused_and_the_champion_stays(ready, change, decided, refusals):
    tracker = registry()
    with DuckDBEngine.open(ready) as engine:
        change(engine)
        sign_both(engine)
        decision = promotion.promote(engine, tracker, MODEL, 2, decided, roles=roles())
        stored = engine.run("SELECT promoted, refusals FROM strata.ops.model_promotions").rows
        still = champion_kept(engine)

    assert (decision.promoted, decision.refusals) == (False, refusals)
    assert stored == ((False, json.dumps(list(refusals))),)
    assert tracker.alias_version(MODEL, "champion") == 1 and still == 1


def test_the_live_promotion_stops_with_one_sentence_when_there_is_no_env_file(tmp_path, capsys, monkeypatch):
    import importlib.util
    import sys
    from pathlib import Path

    monkeypatch.setattr(sys, "path", list(sys.path))  # the script adds ops/ folders to the path; undo that after
    script = Path(__file__).resolve().parents[1] / "ops" / "estimates" / "promote_live.py"
    spec = importlib.util.spec_from_file_location("promote_live", script)
    live = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(live)

    assert live.main(["--env-file", str(tmp_path / "missing.env"), "promote", "--version", "2"]) == 2
    assert "There is no env file" in capsys.readouterr().out


def test_the_nightly_score_task_scores_a_challenger_in_shadow_where_no_tool_reads_it(fixture_db, tmp_path):
    from strata.lakehouse import nightly
    from strata.tools import registry

    path = tmp_path / "fixture.duckdb"
    shutil.copy(fixture_db, path)
    night = dt.datetime(2026, 10, 24, 9, tzinfo=dt.UTC)
    with DuckDBEngine.open(path) as engine:
        before = registry.call("estimate_time", {"step_reference": "KE-NWWDA-229129-CW-RFB"},
                               registry.Context(engine, None, "staff", night.date()))
        # The fixture's champion, version 1, kept again as a challenger, version 2, as a quarterly retrain would.
        engine.run("INSERT INTO strata.gold.time_estimate_model SELECT model, 2, 'challenger', training_through, "
                   "booster_json, state_json, NULL, registered_at, public_from FROM strata.gold.time_estimate_model "
                   "WHERE alias = 'champion'")
        nightly.run_task(engine, "score", "night-2", nightly.fetch_recorded, clock=lambda: night)
        shadow = engine.run("SELECT model_version, count(*), count(q80_days) FROM strata.ops.time_estimate_shadow "
                            "GROUP BY model_version").rows
        scored = engine.run("SELECT count(DISTINCT step_reference) FROM strata.gold.time_estimate_score "
                            "WHERE run_id = 'night-2' AND as_described").rows[0][0]
        after = registry.call("estimate_time", {"step_reference": "KE-NWWDA-229129-CW-RFB"},
                              registry.Context(engine, None, "staff", night.date()))

    [(version, rows_scored, ranged)] = shadow
    assert version == 2 and rows_scored == scored and ranged > 0
    assert after["estimate"]["model_version"] == before["estimate"]["model_version"] == 1


def test_a_challenger_needs_a_sign_off_from_the_model_owner_and_a_different_person_as_the_lead(ready):
    tracker = registry()
    with DuckDBEngine.open(ready) as engine:
        unsigned = promotion.promote(engine, tracker, MODEL, 2, DECIDED, roles=roles())
        # Someone the roles file does not name as a model owner cannot sign off as one.
        with pytest.raises(promotion.Refused) as refused:
            promotion.sign_off(engine, roles(), LEAD, MODEL, 2, "model_owner", DECIDED)
        both_roles = dataclasses.replace(roles(), people=(
            Person(OWNER, "Model Owner", ("model_owner", "lead_procurement_specialist"), ("South Asia",), ()),))
        promotion.sign_off(engine, both_roles, OWNER, MODEL, 2, "model_owner", DECIDED - DAY)
        promotion.sign_off(engine, both_roles, OWNER, MODEL, 2, "lead", DECIDED - DAY)
        one_person = promotion.promote(engine, tracker, MODEL, 2, DECIDED, roles=both_roles)

    assert unsigned.refusals == ("no_model_owner_sign_off", "no_lead_sign_off")
    assert refused.value.code == "not_in_role"
    assert one_person.refusals == ("no_lead_sign_off",)
    assert tracker.alias_version(MODEL, "champion") == 1


def test_a_person_who_signed_in_both_roles_is_the_lead_when_another_model_owner_signed(ready):
    tracker = registry()
    both = dataclasses.replace(roles(), people=(
        Person(LEAD, "Lead Specialist", ("model_owner", "lead_procurement_specialist"), ("South Asia",), ()),
        Person(OWNER, "Model Owner", ("model_owner",), (), ())))
    with DuckDBEngine.open(ready) as engine:
        promotion.sign_off(engine, both, LEAD, MODEL, 2, "model_owner", DECIDED - 2 * DAY)
        promotion.sign_off(engine, both, LEAD, MODEL, 2, "lead", DECIDED - 2 * DAY)
        promotion.sign_off(engine, both, OWNER, MODEL, 2, "model_owner", DECIDED - DAY)
        decision = promotion.promote(engine, tracker, MODEL, 2, DECIDED, roles=both)

    assert decision.evidence["sign_offs"] == {"model_owner": OWNER, "lead": LEAD}
    assert (decision.promoted, decision.refusals) == (True, ())
