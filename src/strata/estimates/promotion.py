"""Promoting a challenger to champion (ticket 44; docs/PLAN.md section 11: the estimates loop's gate is "wins the
backtest and a quarter in shadow, and coverage holds for each Regulations edition", and its owner is "the model
owner co-signed by the lead").

A quarterly retrain, or the next one after the monthly watch raised a retrain (strata.estimates.watch), runs ticket
25's backtest (strata.estimates.backtest.run), which registers its model as the challenger while a champion holds the
alias. From then on the nightly score task scores every package with the challenger too, in shadow
(strata.ops.time_estimate_shadow), which no tool and no screen reads. promote() then decides, from stored results
only, and refuses with every reason code that applies, in this order:

- no_backtest_win: over the test years both backtests scored, the challenger's typical error (the median of its
  yearly error_estimate_months) is not lower than the champion's, or its unseen packages, pooled over its test years,
  did not finish inside its 8-in-10 range at a share inside time_estimate.coverage_low to coverage_high, or there
  were fewer than estimates_loop.min_cases of them.
- no_shadow_win: the challenger has not been in shadow for estimates_loop.shadow_quarter_months, or fewer than
  min_cases packages signed in that time with an estimate from both models, or its typical error on them, in days
  from first notice to signing, is not lower than the champion's.
- edition_coverage: an edition of the procurement rules (config/editions.toml, by the edition each project's PAD
  names, ticket 29's tag) with min_cases unseen packages or more in the challenger's backtest had its coverage outside
  the band, or no edition had that many. Packages whose project names no edition are counted, never judged.
- no_model_owner_sign_off, no_lead_sign_off: no sign-off in that role (strata.ops.model_signoffs) from a person the
  roles file still names in its group ([model_sign_off] in config/roles.toml). The lead must be a different person
  from the model owner who signed.

With none, the champion alias moves to the challenger in Unity Catalog (the tracker's set_alias: MLflow on the
workspace, the offline stand-in in the gate), and the version is kept again under the champion alias in
strata.gold.time_estimate_model, which the score task and the app read. Every decision is a row in
strata.ops.model_promotions with its evidence. Reason codes are stored, never sentences: ticket 45's copy words them.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import statistics
from collections.abc import Iterable
from dataclasses import dataclass
from fractions import Fraction
from importlib import resources

from strata.config import Roles, Thresholds, load_roles, load_thresholds
from strata.estimates.past_range import as_date
from strata.lakehouse.engine import Engine

log = logging.getLogger("strata.estimates.promotion")
REFUSALS = ("no_backtest_win", "no_shadow_win", "edition_coverage", "no_model_owner_sign_off", "no_lead_sign_off")
ROLES = ("model_owner", "lead")
CHAMPION, CHALLENGER = "champion", "challenger"
SIGNOFFS_TABLE = "strata.ops.model_signoffs"
SIGNOFFS_COLUMNS = ("model", "version", "role", "signed_by", "signed_at", "public_from")
PROMOTIONS_TABLE = "strata.ops.model_promotions"
PROMOTIONS_COLUMNS = ("model", "version", "champion_version", "promoted", "refusals", "evidence", "decided_at",
                      "public_from")
SHADOW_TABLE = "strata.ops.time_estimate_shadow"
SHADOW_COLUMNS = ("step_reference", "run_id", "model", "model_version", "feature_date", "q50_days", "q80_days",
                  "abstention", "scored_at", "public_from")


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "promotion" / f"{name}.sql").read_text()


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


class Refused(Exception):
    """A sign-off the roles file does not allow, with its reason code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Settings:
    min_cases: int
    shadow_months: int
    low: Fraction
    high: Fraction

    @classmethod
    def read(cls, thresholds: Thresholds) -> Settings:
        value = thresholds.value
        return cls(int(value("estimates_loop.min_cases")), int(value("estimates_loop.shadow_quarter_months")),
                   Fraction(str(value("time_estimate.coverage_low"))), Fraction(str(value("time_estimate.coverage_high"))))

    def inside(self, m: int, n: int) -> bool:
        return n > 0 and self.low <= Fraction(m, n) <= self.high


@dataclass(frozen=True)
class Decision:
    model: str
    version: int
    champion_version: int | None
    promoted: bool
    refusals: tuple[str, ...]
    evidence: dict


# ── Sign-offs ────────────────────────────────────────────────────────────

def sign_off(engine: Engine, roles: Roles, email: str, model: str, version: int, role: str,
             signed_at: dt.datetime) -> dict:
    """Record a person's sign-off on a challenger version in a role, model_owner or lead. Refused with not_in_role
    for anyone the roles file does not name in that role's group, and unknown_role for any other role."""
    if role not in ROLES:
        raise Refused("unknown_role")
    if not roles.signs_off_as(email, role):
        raise Refused("not_in_role")
    day = signed_at.astimezone(dt.UTC).date()
    engine.insert_rows(SIGNOFFS_TABLE, SIGNOFFS_COLUMNS, [(model, int(version), role, email, signed_at, day)])
    return {"model": model, "version": int(version), "role": role, "signed_by": email, "signed_on": day.isoformat()}


def sign_off_check(engine: Engine, roles: Roles, model: str, version: int) -> dict:
    """Who signed off in each role and still holds it: the first model owner who signed with a lead who is a
    different person, oldest first. With no such pair, the first model owner and the first lead who is not them."""
    given = _rows(engine, "sign_offs", model=model, version=int(version))

    def signed(role: str) -> list[str]:
        return list(dict.fromkeys(row["signed_by"] for row in given
                                  if row["role"] == role and roles.signs_off_as(row["signed_by"], role)))

    owners, leads = signed("model_owner"), signed("lead")
    for owner in owners:
        lead = next((person for person in leads if person != owner), None)
        if lead is not None:
            return {"model_owner": owner, "lead": lead}
    owner = owners[0] if owners else None
    return {"model_owner": owner, "lead": next((person for person in leads if person != owner), None)}


# ── The backtest, each edition, and the shadow quarter ──────────────────

def backtest_years(engine: Engine, version: int, as_of: dt.date | None = None) -> dict[int, dict]:
    """The test years of the backtest run that registered a version, public on as_of when given, or none."""
    from strata.estimates import backtest

    run_id = backtest.registered_run(engine, version, as_of)
    return backtest.stored_years(engine, run_id) if run_id else {}


def _typical(years: dict[int, dict], shared: Iterable[int]) -> float | None:
    errors = [float(years[year]["error_estimate_months"]) for year in shared]
    return float(statistics.median(errors)) if errors else None


def backtest_check(challenger: dict[int, dict], champion: dict[int, dict], settings: Settings) -> tuple[bool, dict]:
    shared = sorted(year for year in challenger if year in champion
                    and challenger[year].get("error_estimate_months") is not None
                    and champion[year].get("error_estimate_months") is not None)
    n = sum(int(record.get("n") or 0) for record in challenger.values())
    m = sum(int(record.get("m") or 0) for record in challenger.values())
    mine, theirs = _typical(challenger, shared), _typical(champion, shared)
    won = (mine is not None and theirs is not None and mine < theirs and n >= settings.min_cases
           and settings.inside(m, n))
    return won, {"years": shared, "error_challenger_months": mine, "error_champion_months": theirs, "n": n, "m": m}


def edition_check(challenger: dict[int, dict], settings: Settings) -> tuple[bool, dict]:
    from strata.estimates.backtest import NO_EDITION

    counts: dict[str, dict[str, int]] = {}
    for record in challenger.values():
        for measure, value in record.items():
            parts = measure.split(".")
            if len(parts) == 3 and parts[0] == "edition" and parts[2] in ("n", "m") and value is not None:
                counts.setdefault(parts[1], {"n": 0, "m": 0})[parts[2]] += int(value)
    found = {}
    for key, count in sorted(counts.items()):
        judged = key != NO_EDITION and count["n"] >= settings.min_cases
        found[key] = {**count, "judged": judged, "inside": settings.inside(count["m"], count["n"]) if judged else None}
    judged = [entry for entry in found.values() if entry["judged"]]
    return bool(judged) and all(entry["inside"] for entry in judged), found


def shadow_check(engine: Engine, model: str, challenger: int, champion: int | None, today: dt.date,
                 settings: Settings) -> tuple[bool, dict]:
    from strata.tools.project_signals import months_after

    started = as_date(_rows(engine, "shadow_start", model=model, version=int(challenger))[0]["started_on"])
    if started is None or champion is None:
        return False, {"started_on": None, "packages": 0}
    long_enough = months_after(started, settings.shadow_months) <= today
    pairs = _rows(engine, "shadow_pairs", model=model, challenger=int(challenger), champion=int(champion),
                  start=started, as_of=today)
    errors = {"challenger": [], "champion": []}
    for row in pairs:
        days = (as_date(row["contract_signed_on"]) - as_date(row["first_notice_date"])).days
        errors["challenger"].append(abs(days - int(row["challenger_q50_days"])))
        errors["champion"].append(abs(days - int(row["champion_q50_days"])))
    mine = float(statistics.median(errors["challenger"])) if pairs else None
    theirs = float(statistics.median(errors["champion"])) if pairs else None
    won = long_enough and len(pairs) >= settings.min_cases and mine < theirs
    return won, {"started_on": started.isoformat(), "months": settings.shadow_months, "long_enough": long_enough,
                 "packages": len(pairs), "error_challenger_days": mine, "error_champion_days": theirs}


# ── Scoring in shadow ────────────────────────────────────────────────────

def score_in_shadow(engine: Engine, run_id: str, scored_at: dt.datetime) -> int:
    """The nightly score task's shadow scores: every package Strata knows, as described, with the newest challenger
    kept in strata.gold.time_estimate_model, while it is newer than the champion. Returns the rows it appended to
    strata.ops.time_estimate_shadow, which no tool and no screen reads."""
    from strata.config import load_time_estimate
    from strata.estimates import portable, scoring, watch
    from strata.estimates.harness import Reader
    from strata.estimates.time_estimate import packages_as_of

    settings, thresholds = load_time_estimate(), load_thresholds()
    day = scored_at.astimezone(dt.UTC).date()
    held = watch.champion(engine, day)
    kept = portable.latest(engine, settings.registered_model, day, alias=CHALLENGER, learner="xgboost")
    if kept is None or (held is not None and kept.version <= int(held["version"])):
        return 0
    known = packages_as_of(Reader(engine, day, thresholds), settings)
    rows = [(item["package"].step_reference, run_id, kept.name, kept.version, item["package"].feature_date,
             None if item.get("days") is None else int(item["days"]["q50"]),
             None if item.get("days") is None else int(item["days"]["q80"]), item["abstention"], scored_at, day)
            for item in scoring.scored(kept.model, [known[key] for key in sorted(known)], ())]
    return engine.insert_rows(SHADOW_TABLE, SHADOW_COLUMNS, rows) if rows else 0


# ── The decision ─────────────────────────────────────────────────────────

def promote(engine: Engine, tracker, model: str, version: int, decided_at: dt.datetime, *,
            roles: Roles | None = None, thresholds: Thresholds | None = None) -> Decision:
    """Decide whether a challenger version becomes the champion, record the decision and, when it does, move the
    champion alias."""
    settings = Settings.read(thresholds or load_thresholds())
    roles = roles or load_roles()
    today = decided_at.astimezone(dt.UTC).date()
    champion = tracker.alias_version(model, CHAMPION)
    mine = backtest_years(engine, version, today)
    theirs = backtest_years(engine, champion, today) if champion is not None else {}
    won_backtest, backtest = backtest_check(mine, theirs, settings)
    won_shadow, shadow = shadow_check(engine, model, version, champion, today, settings)
    editions_hold, editions = edition_check(mine, settings)
    signed = sign_off_check(engine, roles, model, version)
    held = {"no_backtest_win": won_backtest, "no_shadow_win": won_shadow, "edition_coverage": editions_hold,
            "no_model_owner_sign_off": signed["model_owner"] is not None, "no_lead_sign_off": signed["lead"] is not None}
    refusals = tuple(code for code in REFUSALS if not held[code])
    evidence = {"backtest": backtest, "shadow": shadow, "editions": editions, "sign_offs": signed}
    promoted = not refusals and champion != version
    if promoted:
        tracker.set_alias(model, CHAMPION, version)
        engine.run(_sql("keep_champion"), {"alias": CHAMPION, "registered_at": decided_at, "public_from": today,
                                           "model": model, "version": int(version), "from_alias": CHALLENGER})
    engine.insert_rows(PROMOTIONS_TABLE, PROMOTIONS_COLUMNS, [(
        model, int(version), champion, promoted, json.dumps(list(refusals)),
        json.dumps(evidence, sort_keys=True, default=str), decided_at, today)])
    return Decision(model, int(version), champion, promoted, refusals, evidence)
