"""estimate_time: Strata's time estimate for one package, its what-ifs, its track record and its plan dates.

The registry (config/tools.toml) defines the tool's parameters and result shape; this module is its adapter
(ticket 26). It answers in one response everything the package workspace's lane 2, "Compare with", the track
record, the plan-date choice and section 4 need, so no comparison and no choice calls the network again.

- The comparable packages are find_comparables' for the same criteria and as-of date: the tool calls its
  adapter and counts its rows, so its n is always lane 1's total. find_comparables' abstentions for a package
  it cannot measure pass through, and below time_estimate.min_comparables comparable packages it abstains
  (too_few_comparables).
- The time estimate comes from the nightly batch: the latest scoring run public on the as-of date
  (strata.gold.time_estimate_score, src/strata/estimates/scoring.py), as described and for each combination
  of market approach and qualification. A package the batch has not scored, such as one planned from a
  sentence a moment ago, is scored on the request with the newest champion public that day, kept in
  strata.gold.time_estimate_model and read with no XGBoost (strata.estimates.portable). As of a day before
  the model's training data ended it abstains (asof_before_training), and with no model at all (no_model).
  A package outside what the model learned from abstains as the batch stored it (outside_training).
- Why the lanes differ: how far the estimate's middle is from the past range's, and the package's size as
  the reason only when the model's own middle, with the package's estimated amount set to its comparable
  packages' middle signed amount, moves at least time_estimate.reason_min_share of the gap; the reason comes
  with its counts ("larger than k of the n").
- The track record, the test years and the plan dates' "ran longer" counts come from the latest backtest run
  public on the as-of date (strata.ops.evaluation_result, ticket 25).
- The comparisons, by config/models.toml's [what_if] levers in order: for each lever whose value the package
  as described records, the value most comparable packages went with other than its own, among the values the
  batch scores for a lever the model reads (rule 1), offered
  only when at least one went with it (rule 2) and the thresholds file allows it (rule 3,
  strata.packages.compute.allows). Review type is never a lever (rule 4). Its estimate is the stored
  combination's, or why there is none: fewer than what_if.min_subgroup went with it, or the model reads no
  such feature (lots, not_in_model).
- Section 4's approaches: the combinations of market approach, lots and qualification that comparable packages
  whose records give all three went with, most first, up to what_if.max_approaches, leaving out what the
  thresholds rule out.

- The planned date for each STEP step (ticket 27, section 2 of the workspace) comes back in step_dates, from the
  same comparable packages: strata.estimates.step_dates picks the package's method family from the step-label
  registry and holds that model, its thresholds and its rules. Both choices, middle and cautious, come in one
  answer, so the screen switches between them with no second call. The step dates come back whatever the time
  estimate does, since section 2 stands on its own; they are left out only for a package no record holds.

Every number is a tool column at its rounding: days whole, months to one decimal. The browser counts nothing.
The public view gives no time estimate for a package of a project still under way (ticket 40; strata.tools.withheld).
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import statistics
from collections import Counter
from collections.abc import Mapping
from decimal import Decimal
from importlib import resources

from strata.config import Lever, load_sources, load_time_estimate, load_tools, load_what_if
from strata.estimates import backtest, model_card, portable, scoring
from strata.estimates import step_dates as steps
from strata.estimates.harness import Reader
from strata.estimates.past_range import QUARTERS, months, whole
from strata.estimates.time_estimate import described_features, packages_as_of
from strata.packages import compute
from strata.lakehouse.engine import EngineError
from strata.tools.find_comparables import find_comparables, read_package
from strata.tools.registry import Call, ToolError
from strata.tools.withheld import WITHHELD, withheld

TOOL = "estimate_time"
log = logging.getLogger("strata.tools.estimate_time")
POINTS = tuple(QUARTERS)  # q25, q50, q75, q80
# find_comparables' abstentions for a package with nothing to compare, which this tool gives too.
FROM_COMPARABLES = ("unknown_package", "no_public_notice", "no_comparables", "none_measurable")


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "estimate_time" / name).read_text()


def _rows(engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    return str(value)[:10]


def _months(days: int) -> float:
    return float(months(days))


# ── The package as described ─────────────────────────────────────────────

def _flag(value) -> str | None:
    """Prequalification (Y/N) as STEP writes it, from Y, N, Yes or No in any case."""
    if value is None:
        return None
    text = str(value).strip().upper()
    return {"Y": "Y", "YES": "Y", "N": "N", "NO": "N"}.get(text)


def _described(found: dict, cells: dict | None, criteria: dict, given: dict) -> dict:
    """The package's own values: from its stored features for a STEP row, else as the call described it."""
    package = found["package"]
    features = json.loads(cells["features_json"]) if cells and cells.get("features_json") else None
    if features is not None:
        return {"market_approach": features.get("market_approach"), "prequalification": _flag(features.get("prequalification")),
                "lots": given.get("lots"), "review_type": features.get("review_type"),
                "estimated_amount_usd": features.get("estimated_amount_usd"), "category": features.get("category"),
                "method": features.get("method"), "country_code": features.get("country_code")}
    if package is not None:
        amount = package.get("estimated_amount_usd")
        return {"market_approach": package.get("market_approach"), "prequalification": _flag(given.get("prequalification")),
                "lots": given.get("lots"), "review_type": package.get("review_type"),
                "estimated_amount_usd": None if amount is None else float(amount), "category": package.get("category"),
                "method": package.get("method"), "country_code": package.get("country_code")}
    amount = given.get("amount_usd")
    return {"market_approach": given.get("market_approach"), "prequalification": _flag(given.get("prequalification")),
            "lots": given.get("lots"), "review_type": given.get("review_type"),
            "estimated_amount_usd": None if amount is None else float(amount), "category": criteria.get("category"),
            "method": criteria.get("method"), "country_code": criteria.get("country")}


# ── The cells: stored, or scored on the request ──────────────────────────

def _stored_cell(row: dict) -> dict:
    days = None if row["q50_days"] is None else {name: int(row[f"{name}_days"]) for name in POINTS}
    key = f"{row['run_id']}/{row['step_reference']}/{row['market_approach'] or '-'}/{row['prequalification'] or '-'}"
    return {
        "evidence_id": f"strata.gold.time_estimate_score:{key}", "public_from": _iso(row["public_from"]),
        "source": {"model": row["model"], "model_version": int(row["model_version"]), "run_id": row["run_id"],
                   "scored": "batch"},
        "as_described": bool(row["as_described"]), "market_approach": row["market_approach"],
        "prequalification": row["prequalification"], "review_type": row["review_type"],
        **{name: None if days is None else float(row[f"{name}_months"]) for name in POINTS},
        "days": days, "abstention": row["abstention"],
        "detail": json.loads(row["abstention_detail"]) if row["abstention_detail"] else None,
    }


def _requested_cells(kept: portable.Kept, features: dict, levers: tuple[Lever, ...], key: str, as_of: dt.date,
                     public_from: str) -> list[dict]:
    """A package the batch has not scored, scored now with the champion, as the batch would have stored it."""
    found = []
    for row in scoring.with_days(kept.model, scoring.grid(kept.model, features, levers)):
        days = row.get("days")
        values = row["features"]
        found.append({
            "evidence_id": f"strata.tools.{TOOL}:{key}/{values.get('market_approach') or '-'}/"
                           f"{values.get('prequalification') or '-'}@{as_of.isoformat()}",
            "public_from": public_from,
            "source": {"model": kept.name, "model_version": kept.version, "run_id": None, "scored": "request"},
            "as_described": row["as_described"], "market_approach": values.get("market_approach"),
            "prequalification": values.get("prequalification"), "review_type": values.get("review_type"),
            **{name: None if days is None else _months(days[name]) for name in POINTS},
            "days": days, "abstention": row["abstention"], "detail": row["detail"]})
    return found


ROW_FIELDS = ("evidence_id", "public_from", "source", "as_described", "market_approach", "prequalification",
              "review_type", "q25", "q50", "q75", "q80", "days", "abstention")


def _row(cell: dict) -> dict:
    return {field: cell[field] for field in ROW_FIELDS}


def _estimate(cell: dict, kept_name: str, version: int, alias: str, training_through, scored_on) -> dict:
    return {**{name: cell[name] for name in POINTS}, "days": cell["days"], "model": kept_name, "model_version": version,
            "model_alias": alias, "training_through": _iso(training_through), "scored_on": _iso(scored_on),
            "scored": cell["source"]["scored"]}


def _coverage(cells: list[dict]) -> dict:
    left_out: dict[str, list[str]] = {}
    for cell in cells:
        if cell["abstention"]:
            left_out.setdefault(cell["abstention"], []).append(cell["evidence_id"])
    return {"matched": len(cells), "used": sum(1 for cell in cells if not cell["abstention"]),
            "not_used": [{"reason": reason, "count": len(ids), "evidence_ids": ids} for reason, ids in left_out.items()]}


# ── What the comparable packages went with ───────────────────────────────

def _went_with(engine, comparables: list[dict], criteria: dict, as_of: dt.date) -> dict[str, dict]:
    """Each comparable package's market approach, lots and qualification, and its signed amount, from its records."""
    wanted = {row["step_reference"] for row in comparables}
    rows = _rows(engine, "levers.sql", as_of=as_of, country=criteria.get("country"), method=criteria.get("method"),
                 category=criteria.get("category"))
    found = {row["step_reference"]: {"market_approach": row["market_approach"],
                                      "prequalification": _flag(row["prequalification"]),
                                      "lots": None if row["lots"] is None else int(row["lots"]),
                                      "amount_usd": None if row["amount_usd"] is None else float(row["amount_usd"])}
             for row in rows if row["step_reference"] in wanted}
    return {reference: found.get(reference, {"market_approach": None, "prequalification": None, "lots": None,
                                             "amount_usd": None}) for reference in sorted(wanted)}


def _cell_for(cells: dict[tuple, dict], described: dict, changes: dict) -> dict | None:
    key = (changes.get("market_approach", described["market_approach"]),
           changes.get("prequalification", described["prequalification"]))
    return cells.get(key)


def _cell_estimate(cell: dict | None) -> tuple[dict | None, dict | None]:
    """A cell's points, or why it has none."""
    if cell is None:
        return None, {"reason": "value_not_learned"}
    if cell["abstention"]:
        return None, {"reason": cell["abstention"], **(cell["detail"] or {})}
    return {**{name: cell[name] for name in POINTS}, "days": cell["days"]}, None


def _comparisons(levers: tuple[Lever, ...], described: dict, went: dict[str, dict], cells: dict[tuple, dict],
                 thresholds, values: dict) -> list[dict]:
    fewest = int(thresholds.value("what_if.min_subgroup"))
    n = len(went)
    found = []
    for lever in levers:
        own = described.get(lever.key)
        if own is None:  # nothing to compare a value with: the package as described records none
            continue
        counts = Counter(record[lever.key] for record in went.values() if record[lever.key] is not None)
        # A lever the model reads offers only a value the nightly batch scores ([what_if] values), so no
        # comparison says the model never learned from a value it was simply never asked about.
        others = sorted(((count, str(value), value) for value, count in counts.items()
                         if value != own and (lever.feature is None or value in lever.values)),
                        key=lambda item: (-item[0], item[1]))
        if not others:
            continue
        k, _, value = others[0]
        if not compute.allows(thresholds, values, lever.key, value):
            continue
        matching = sorted(reference for reference, record in went.items() if record[lever.key] == value)
        # Those whose records give no value for the lever: the chart counts them among the others, and the table
        # twin says "Not recorded" for them rather than "No".
        unrecorded = sorted(reference for reference, record in went.items() if record[lever.key] is None)
        if lever.feature is None:
            estimate, abstention = None, {"reason": "not_in_model", "lever": lever.key}
        elif k < fewest:
            estimate, abstention = None, {"reason": "too_few_in_subgroup", "k": k, "n": n, "min_subgroup": fewest}
        else:
            estimate, abstention = _cell_estimate(_cell_for(cells, described, {lever.feature: value}))
        found.append({"lever": lever.key, "value": value, "own": own, "k": k, "rest": n - k, "n": n,
                      "matching_ids": matching, "unrecorded_ids": unrecorded, "estimate": estimate,
                      "abstention": abstention})
    return found


def _options(described: dict, went: dict[str, dict], cells: dict[tuple, dict], thresholds, values: dict) -> dict:
    fewest = int(thresholds.value("what_if.min_subgroup"))
    n = len(went)
    approach_of = {reference: (record["market_approach"], record["lots"], record["prequalification"])
                   for reference, record in went.items()
                   if None not in (record["market_approach"], record["lots"], record["prequalification"])}
    whole_records = list(approach_of.values())
    allowed = [approach for approach in whole_records if compute.allows(thresholds, values, "market_approach", approach[0])]
    counts = Counter(allowed)
    ranked = sorted(counts.items(), key=lambda item: (-item[1], str(item[0])))
    own = (described["market_approach"], described["lots"], described["prequalification"])
    approaches = []
    for (approach, lots, qualification), k in ranked[:int(thresholds.value("what_if.max_approaches"))]:
        if k < fewest:
            estimate, abstention = None, {"reason": "too_few_in_subgroup", "k": k, "n": n, "min_subgroup": fewest}
        elif described["lots"] is None or lots != described["lots"]:
            estimate, abstention = None, {"reason": "not_in_model", "lever": "lots"}
        else:
            estimate, abstention = _cell_estimate(
                _cell_for(cells, described, {"market_approach": approach, "prequalification": qualification}))
        matching = sorted(reference for reference, whole in approach_of.items() if whole == (approach, lots, qualification))
        approaches.append({"market_approach": approach, "lots": lots, "prequalification": qualification, "k": k,
                           "matching_ids": matching, "is_as_described": (approach, lots, qualification) == own,
                           "estimate": estimate, "abstention": abstention})
    # Every count section 4's sentences give, so the screen works out none: those whose records give the whole
    # approach, those of them the thresholds rule out for this package, and those whose records don't give it.
    return {"approaches": approaches, "count": len(ranked), "recorded": len(whole_records),
            "ruled_out": len(whole_records) - len(allowed), "unrecorded": n - len(whole_records), "n": n,
            "review_type": described["review_type"]}


# ── Why the lanes differ ─────────────────────────────────────────────────

def _difference(estimate: dict, past_range: dict | None, described: dict, went: dict[str, dict], features: dict | None,
                model, thresholds) -> dict | None:
    if past_range is None or past_range.get("q50") is None:
        return None
    gap = Decimal(str(estimate["q50"])) - Decimal(str(past_range["q50"]))
    same = abs(gap) < Decimal(str(thresholds.value("time_estimate.same_middle_months")))
    direction = "same" if same else "later" if gap > 0 else "earlier"
    reasons = [] if same or features is None or model is None else _size_reason(direction, gap, described, went,
                                                                               features, model, thresholds)
    return {"middle_diff_months": float(abs(gap)), "direction": direction, "reasons": reasons}


def _size_reason(direction: str, gap: Decimal, described: dict, went: dict[str, dict], features: dict, model,
                 thresholds) -> list[dict]:
    """The package's size as the reason, with its counts, when the model's own middle shows it: with the
    estimated amount set to the comparable packages' middle signed amount, the middle moves at least
    time_estimate.reason_min_share of the gap toward the past range."""
    amount = described.get("estimated_amount_usd")
    amounts = [record["amount_usd"] for record in went.values() if record["amount_usd"] is not None]
    if amount is None or not amounts:
        return []
    middle_amount = float(statistics.median(amounts))
    larger = amount > middle_amount
    if (direction == "later") != larger or amount == middle_amount:
        return []
    as_described, sized = model.days([features, {**features, "estimated_amount_usd": middle_amount}])
    middle, moved = as_described["q50"], sized["q50"]
    shift = Decimal(str(_months(middle))) - Decimal(str(_months(moved)))
    share = Decimal(str(thresholds.value("time_estimate.reason_min_share")))
    toward = shift if direction == "later" else -shift
    if toward < share * abs(gap):
        return []
    k = sum(1 for value in amounts if (value < amount if larger else value > amount))
    return [{"code": "size_larger" if larger else "size_smaller", "k": k, "n": len(went)}]


# ── The track record and the plan dates ──────────────────────────────────

def _backtests(engine, as_of: dt.date, thresholds, viewer, model: str,
               version: int | None = None) -> tuple[dict | None, list[dict], dict | None]:
    """The track record, each test year and the latest test year of the version the estimate comes from: the
    champion on as_of, unless version names another (a score stored before a promotion). They come from the backtest
    run that registered that version, so a challenger's newer run changes nothing until it is promoted (ticket 44)."""
    try:
        if version is None:
            version = portable.version_on(engine, model, as_of)
        years = backtest.version_years(engine, version, as_of)
    except EngineError:  # a viewer who cannot read strata.ops still gets the estimate, with no track record
        # The user id, never the name, which falls back to the viewer's email when no name header arrives.
        log.warning("I could not read the time estimate's backtests for %s.", viewer.user_id, exc_info=True)
        # Not None, which the screen reads as "no backtest results yet": the results may exist unread.
        return {"year": None, "abstention": {"reason": "not_readable"}}, [], None
    record = model_card.track_record(years, thresholds)
    track = None
    if record is not None:
        track = {key: (_iso(value) if key == "ran_on" else value) for key, value in record.items()}
        if record["abstention"] is None:  # the misses clause's count, so the screen works out none
            track["misses"] = record["n"] - record["m"]
    test_years = []
    for year, stored in sorted(years.items()):
        test_years.append({"year": year, "n": stored.get("n"), "m": stored.get("m"), "expected": stored.get("expected"),
                           "error_estimate_months": stored.get("error_estimate_months"),
                           "error_past_range_months": stored.get("error_past_range_months"),
                           "error_plan_months": stored.get("error_plan_months"),
                           "mlflow_run_id": stored.get("mlflow_run_id"), "abstention": stored.get("abstention")})
    return track, test_years, years[max(years)] if years else None


def _plan_dates(estimate: dict, latest: dict | None) -> dict:
    def point(name: str, months_value: float) -> dict:
        if latest is None or latest.get(f"{name}_total") is None:
            return {"months": months_value, "ran_longer": None, "total": None, "in10": None}
        return {"months": months_value, "ran_longer": latest.get(f"{name}_ran_longer"), "total": latest.get(f"{name}_total"),
                "in10": latest.get(f"{name}_in10")}

    return {"middle": point("middle", estimate["q50"]), "eight_in_ten": point("eight_in_ten", estimate["q80"]),
            "default": "eight_in_ten"}


# ── The planned date for each step (ticket 27) ──────────────────────────

def _sources() -> list[dict]:
    registry = load_sources()
    return [{"key": key, "dataset_name": registry[key].dataset_name} for key in load_tools()[TOOL].sources]


def _step_dates(call: Call, found: dict, criteria: dict, start_date: dt.date | None, settings: steps.Settings,
                sources: list[dict], own: steps.Activity | None = None, method: str | None = None) -> dict:
    """Section 2's planned date for each step, as of call.as_of, from find_comparables' comparable packages. With
    no STEP row, for a package someone is planning, the category and method come from the criteria. An upload's row
    (ticket 38) gives its own dates as the baseline (own) and its own Method."""
    package = found["package"]
    category_now = package["category"] if package else criteria.get("category")
    method_now = method or (package["method"] if package else criteria.get("method"))

    def rows(sql: str, **params) -> list[dict]:
        result = call.engine.run(sql, {**params, "as_of": call.as_of})
        return [dict(zip(result.columns, values)) for values in result.rows]

    comparables = [row["step_reference"] for row in found["rows"]]
    try:
        track = steps.track_record(call.engine, call.as_of, settings)
    except EngineError:  # a viewer who cannot read strata.ops still gets the dates, with no track record line
        log.warning("I could not read the step backtests' track record for %s.", call.viewer.user_id, exc_info=True)
        track = None
    dated = steps.step_dates(rows, category=category_now, method=method_now,
                             package_reference=package["step_reference"] if package else None,
                             comparables=comparables, as_of=call.as_of, start_date=start_date, settings=settings,
                             track=track, sources=[source["key"] for source in sources], own=own)
    # The comparable packages whose plans dated none of the family's steps: step_dates' own coverage counts them.
    dated.pop("not_used", None)
    return dated


# ── An implementing agency's upload (ticket 38) ──────────────────────────

def _upload_row(call: Call, upload_row: str) -> tuple[Mapping | None, Mapping | None]:
    """The upload and its row that upload_row names ({upload_id}:{position}), as the viewer may read them through the
    server's team rule, or (None, None)."""
    upload_id, _, position = upload_row.rpartition(":")
    upload = call.uploads(upload_id) if call.uploads is not None and position.isdigit() else None
    row = next((row for row in upload["rows"] if int(row["position"]) == int(position)), None) if upload else None
    return (upload, row) if row is not None else (None, None)


def _upload_activity(upload: Mapping, row: Mapping) -> steps.Activity:
    """An upload's row as the step dates read a package's own plan: its dates as the officer's file gives them are its
    first published dates, since the upload is the plan they are checking (the 38 brief, 6.7: "In your plan")."""
    uploaded_on = dt.date.fromisoformat(upload["uploaded_on"])
    dated = {}
    for name, dates in (row.get("steps") or {}).items():
        planned, actual = (dt.date.fromisoformat(dates[key]) if dates.get(key) else None for key in ("planned", "actual"))
        dated[name] = steps.StepRow(planned, actual, planned, uploaded_on if planned else None, None)
    section = row.get("section")
    if not section:
        # A row whose file names no STEP table: the family whose methods alone hold its Method, when only one does, so
        # its steps can still be chosen. Direct Selection sits in several families, so it needs its table.
        method = (row.get("fields") or {}).get("method")
        holding = [family for family in steps.families().values() if method in family["methods"]]
        section = holding[0]["sections"][0] if len(holding) == 1 else None
    return steps.Activity(row.get("reference") or f"row-{row['position']}", section,
                          (row.get("fields") or {}).get("process_status"), uploaded_on, dated)


def _upload_criteria(call: Call, upload: Mapping, row: Mapping) -> dict:
    """find_comparables' criteria for an upload row whose reference no record holds: its Method, the category its
    STEP table stands for in the step-label registry, and its project's country."""
    fields = row.get("fields") or {}
    category = None
    for family in steps.families().values():
        category = dict(zip(family["sections"], family["categories"])).get(row.get("section")) or category
    country = _rows(call.engine, "project_country.sql", project_id=upload["project_id"])
    return {"method": fields.get("method"), "category": category,
            "country": country[0]["country_code"] if country else None}


def _amount(value) -> float | None:
    return None if value in (None, "") else float(value)


def _thresholds(thresholds) -> dict:
    return {"min_comparables": int(thresholds.value("time_estimate.min_comparables")),
            "min_subgroup": int(thresholds.value("what_if.min_subgroup")),
            "min_unseen_packages": int(thresholds.value("time_estimate.min_unseen_packages"))}


def _nothing(thresholds, abstention: dict, step_reference: str | None = None) -> dict:
    """An answer with no estimate and nothing read, for the abstention given."""
    return {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []},
            "package": {"step_reference": step_reference, "described": None},
            "comparables": {"n": 0, "signed": 0, "still_open": 0},
            "estimate": None, "difference": None, "track_record": None, "test_years": [], "plan_dates": None,
            "comparisons": [], "options": None, "axis_max_months": None, "thresholds": _thresholds(thresholds),
            "step_dates": None, "sources": _sources(), "records_through": None, "abstention": abstention}


def _unknown_upload(call: Call, thresholds) -> dict:
    """The answer for an upload row the viewer may not read, or that does not exist: the same for both, with no
    rows and nothing of the upload."""
    return _nothing(thresholds, {"reason": "unknown_upload"})


# ── The tool ─────────────────────────────────────────────────────────────

def estimate_time(call: Call, step_reference: str | None = None, method: str | None = None,
                  category: str | None = None, market_approach: str | None = None, review_type: str | None = None,
                  size_from_usd: float | None = None, size_to_usd: float | None = None, country: str | None = None,
                  notice_from: dt.date | None = None, notice_to: dt.date | None = None,
                  described_amount_usd: float | None = None, described_market_approach: str | None = None,
                  described_review_type: str | None = None, described_prequalification: str | None = None,
                  described_lots: int | None = None, start_date: dt.date | None = None,
                  upload_row: str | None = None) -> dict:
    """The time estimate for one package as of call.as_of, with everything section 1's lane 2 and section 4 show,
    and section 2's planned date for each step. An upload's row (ticket 38), which only the server's team rule
    reads, is the package: its reference when a record holds it, otherwise its own values, with its own dates as
    the baseline of its step dates."""
    thresholds, settings, levers = call.thresholds, load_time_estimate(), load_what_if()
    step_settings = steps.Settings.read(thresholds)
    window = step_settings.start_range(call.as_of)
    if start_date is not None and not window["from"] <= start_date.isoformat() <= window["to"]:
        raise ToolError(f"estimate_time takes a start_date from {window['from']} to {window['to']}, not {start_date}.")
    own = own_method = None
    if upload_row is not None:
        upload, row = _upload_row(call, upload_row)
        if row is None:
            return _unknown_upload(call, thresholds)
        own, fields = _upload_activity(upload, row), row.get("fields") or {}
        own_method = fields.get("method")
        known = row.get("reference") and read_package(call.engine, row["reference"], call.as_of)
        if known:
            step_reference = row["reference"]
        else:
            asked = _upload_criteria(call, upload, row)
            method, category, country = method or asked["method"], category or asked["category"], country or asked["country"]
            described_amount_usd = described_amount_usd or _amount(fields.get("estimated_amount_usd"))
            described_market_approach = described_market_approach or fields.get("market_approach")
            described_review_type = described_review_type or fields.get("review_type")
            described_prequalification = described_prequalification or fields.get("prequalification")
    # The public view gives no time estimate on a project still under way (the roles file's [views], ticket 40).
    package = read_package(call.engine, step_reference, call.as_of) if step_reference else None
    if package is not None and withheld(call, "time_estimates_on_active_projects", package["project_id"]):
        return _nothing(thresholds, {"reason": WITHHELD, "step_reference": step_reference}, step_reference)
    criteria = {"method": method, "category": category, "market_approach": market_approach, "review_type": review_type,
                "size_from_usd": size_from_usd, "size_to_usd": size_to_usd, "country": country,
                "notice_from": notice_from, "notice_to": notice_to}
    given = {"amount_usd": described_amount_usd, "market_approach": described_market_approach,
             "review_type": described_review_type, "prequalification": described_prequalification, "lots": described_lots}
    found = find_comparables(call, step_reference=step_reference, **criteria)
    used = found["criteria"] or {}
    sources = _sources()
    unknown = found["abstention"] is not None and found["abstention"]["reason"] == "unknown_package"
    dated = None if unknown else _step_dates(call, found, used, start_date, step_settings, sources, own, own_method)
    comparables = found["rows"]
    n = len(comparables)
    counts = found["counts"]
    fewest = int(thresholds.value("time_estimate.min_comparables"))
    track, test_years, latest_year = _backtests(call.engine, call.as_of, thresholds, call.viewer,
                                                settings.registered_model)
    result = {"rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []},
              "package": {"step_reference": step_reference, "described": None},
              "comparables": {"n": n, "signed": counts["signed"] if counts else 0,
                              "still_open": counts["still_open"] if counts else 0},
              "estimate": None, "difference": None, "track_record": track, "test_years": test_years, "plan_dates": None,
              "comparisons": [], "options": None, "axis_max_months": None,
              "thresholds": {"min_comparables": fewest, "min_subgroup": int(thresholds.value("what_if.min_subgroup")),
                             "min_unseen_packages": int(thresholds.value("time_estimate.min_unseen_packages"))},
              "step_dates": dated, "sources": sources, "records_through": found["records_through"],
              "abstention": None}
    abstention = found["abstention"]
    if abstention is not None and abstention["reason"] in FROM_COMPARABLES:
        return {**result, "abstention": abstention}
    if n < fewest:
        return {**result, "abstention": {"reason": "too_few_comparables", "count": n, "min_comparables": fewest}}

    kept = portable.latest(call.engine, settings.registered_model, call.as_of)
    stored = _rows(call.engine, "scores.sql", step_reference=step_reference, as_of=call.as_of) if step_reference else []
    if kept is None and not stored:
        # A model registered later says only that one exists: its training date was not public on the as-of date.
        if portable.latest(call.engine, settings.registered_model, dt.date.max) is None:
            return {**result, "abstention": {"reason": "no_model"}}
        return {**result, "abstention": {"reason": "asof_before_training", "as_of": call.as_of.isoformat()}}
    described_row = next((row for row in stored if row["as_described"]), None)
    training_through = described_row["training_through"] if described_row else kept.model.training_through
    if call.as_of < (training_through if isinstance(training_through, dt.date) else dt.date.fromisoformat(str(training_through))):
        return {**result, "abstention": {"reason": "asof_before_training", "as_of": call.as_of.isoformat()}}

    described = _described(found, described_row, used, given)
    if stored:
        cells = [_stored_cell(row) for row in stored]
        features = json.loads(described_row["features_json"]) if described_row and described_row["features_json"] else None
        name, version, alias = described_row["model"], int(described_row["model_version"]), described_row["model_alias"]
        scored_on = described_row["public_from"]
    else:
        reader = Reader(call.engine, call.as_of, thresholds)
        if step_reference:
            features = packages_as_of(reader, settings, only=step_reference)[step_reference].features
        else:
            features = described_features(reader, {**described, "prequalification": described["prequalification"]},
                                          settings)
        key = step_reference or "described"
        cells = _requested_cells(kept, features, levers, key, call.as_of, call.as_of.isoformat())
        name, version, alias, scored_on = kept.name, kept.version, kept.alias, call.as_of
    model = kept.model if kept is not None and kept.version == version else None
    if kept is None or kept.version != version:  # scored by an earlier champion: that version's own track record
        track, test_years, latest_year = _backtests(call.engine, call.as_of, thresholds, call.viewer,
                                                    settings.registered_model, version)
        result = {**result, "track_record": track, "test_years": test_years}
    described_cell = next(cell for cell in cells if cell["as_described"])
    values = {"country": described["country_code"], "category": described["category"],
              "estimated_amount_usd": described["estimated_amount_usd"]}
    went = _went_with(call.engine, comparables, used, call.as_of)
    by_key = {}
    for cell in cells:  # the as-described row wins over a combination with the same values
        by_key.setdefault((cell["market_approach"], cell["prequalification"]), cell)
    by_key[(described_cell["market_approach"], described_cell["prequalification"])] = described_cell
    options = _options(described, went, by_key, thresholds, values)
    result = {**result, "package": {"step_reference": step_reference, "described": described}, "options": options,
              "rows": [_row(cell) for cell in cells], "coverage": _coverage(cells)}
    if described_cell["abstention"]:
        return {**result, "rows": [], "coverage": {"matched": 0, "used": 0, "not_used": []},
                "abstention": {"reason": described_cell["abstention"], **(described_cell["detail"] or {})}}

    estimate = _estimate(described_cell, name, version, alias, training_through, scored_on)
    comparisons = _comparisons(levers, described, went, by_key, thresholds, values)
    shown = [estimate["q80"]] + [cell["q80"] for cell in cells if cell["q80"] is not None]
    return {**result, "estimate": estimate,
            "difference": _difference(estimate, found["past_range"], described, went, features, model, thresholds),
            "plan_dates": _plan_dates(estimate, latest_year), "comparisons": comparisons,
            "axis_max_months": max(shown)}
