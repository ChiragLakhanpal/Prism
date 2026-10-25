"""The time estimate's model card: a document, kept in MLflow as model_card.md beside the model, which the
registered model's description in Unity Catalog points to.

render() writes it from the stored backtest results (strata.ops.evaluation_result) and the model the
run trained, so every number in it, the track record's included, comes from a run and none is typed.
It is a document about Strata, so it speaks of Strata in the third person. Its sections: what the
model is for, the data, the features, what it never reads (the leakage exclusions), the backtests,
coverage of the 8-in-10 range year by year with the likely cause of any year outside the band, the
track record, and when it gives no range (the abstention rule).
"""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal
from fractions import Fraction

from strata.config import Thresholds, TimeEstimateSettings

# Why a model could not size its ranges, by the code the backtest stores.
NO_MODEL = {
    "too_few_calibration_packages": "it had fewer than {fewest} packages to size its ranges on",
    "range_not_reached": "too many of the packages that sized its ranges were still open, so the 8-in-10 point "
                         "could not be found",
}


def _date(day: dt.date | str) -> str:
    day = day if isinstance(day, dt.date) else dt.date.fromisoformat(str(day)[:10])
    return f"{day:%B} {day.day}, {day.year}"


def _percent(value: float) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal(1), ROUND_HALF_UP))


# The features a package must sit inside the training range of, by their names in the documents.
FEATURE_NAMES = {"estimated_amount_usd": "Estimated Amount (US$)", "planned_days": "planned duration"}
WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
ORDINALS = {2: "second", 3: "third", 4: "fourth", 5: "fifth", 6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth"}


def _words(count: int) -> str:
    """One to nine in words, larger counts in numerals (DESIGN.md section 7, rule 12)."""
    return WORDS.get(count, str(count))


def _share_sentence(k: int, n: int, all_of: str, none_of: str, some_of: str) -> str:
    return all_of if k == n else none_of if k == 0 else some_of.format(k=_words(k), n=n)


def _cell(record: dict, key: str) -> str:
    """A table cell: a count as it is, months to one decimal, and "none" when the year has no value."""
    value = record.get(key)
    if value is None:
        return "none"
    return f"{float(value):.1f}" if key.endswith("_months") else str(value)


# The card names still-open packages as the likely cause of a short range when at least this share of the
# packages that sized it were still open at the cutoff.
MANY_STILL_OPEN = Fraction(1, 4)


def _cause(year: int, record: dict, high: float) -> str:
    """The likely cause of a year outside the coverage band, from the year's own stored counts."""
    if record["coverage"] > high:
        return (f"the range was wider than it needed to be: packages advertised in {year} took less time than the "
                "packages before the cutoff that sized it.")
    still_open, sized_on = record.get("calibration_still_open", 0), record.get("calibration_packages", 0)
    if sized_on and Fraction(still_open, sized_on) >= MANY_STILL_OPEN:
        return (f"{still_open} of the {sized_on} packages that sized the range were still open at the cutoff. Kaplan-Meier "
                "keeps them as not signed yet, but the range still rests mostly on packages that signed quickly, so "
                "it came out short.")
    return (f"packages advertised in {year} took longer than the packages advertised before the cutoff that sized the "
            "range. A range sized on earlier years is short when cycle times grow.")


def _coverage(years: dict[int, dict], thresholds: Thresholds) -> list[str]:
    low, high = (float(thresholds.value("time_estimate.coverage_low")),
                 float(thresholds.value("time_estimate.coverage_high")))
    fewest = int(thresholds.value("time_estimate.min_unseen_packages"))
    lines = [f"The 8-in-10 range should hold from {_percent(low)} to {_percent(high)} percent of the packages "
             "Strata had not seen in each test year.", ""]
    for year, record in sorted(years.items()):
        if "abstention" in record:
            lines.append(f"- {year}: the model gave no ranges, so coverage could not be measured.")
        elif record.get("n", 0) < fewest:
            count = record.get("n", 0)
            scored = ("no package Strata had not seen could be scored" if count == 0 else
                      f"only {_words(count)} package{'s' if count > 1 else ''} Strata had not seen could be "
                      "scored")
            lines.append(f"- {year}: {scored}, fewer than {fewest}, too few to judge coverage.")
        elif record["in_band"]:
            lines.append(f"- {year}: {record['m']} of {record['n']} finished inside the 8-in-10 range "
                         f"({_percent(record['coverage'])} percent), inside the band.")
        else:
            lines.append(f"- {year}: {record['m']} of {record['n']} finished inside the 8-in-10 range "
                         f"({_percent(record['coverage'])} percent), outside the band. Shortfall: "
                         f"{abs(_percent(record['coverage']) - _percent(low if record['coverage'] < low else high))} "
                         f"percentage points. A likely cause: {_cause(year, record, high)}")
    return lines


def track_record(years: dict[int, dict], thresholds: Thresholds) -> dict | None:
    """The latest test year's track record from stored test years, or an abstention when that year had
    fewer than time_estimate.min_unseen_packages packages the model had not seen. None with no years."""
    if not years:
        return None
    year = max(years)
    record = years[year]
    fewest = int(thresholds.value("time_estimate.min_unseen_packages"))
    if "abstention" in record or record.get("n", 0) < fewest:
        return {"year": year, "abstention": {"reason": "too_few_unseen_packages", "n": record.get("n", 0),
                                             "min_unseen_packages": fewest}}
    ran_at = record.get("ran_at")
    return {"year": year, "n": record["n"], "m": record["m"], "expected": record["expected"],
            "misses_early": record.get("misses_early"), "misses_late": record.get("misses_late"),
            "ran_on": ran_at.date() if isinstance(ran_at, dt.datetime) else ran_at,
            "mlflow_run_id": record.get("mlflow_run_id"), "abstention": None}


def sentence(record: dict | None) -> str:
    """The track-record sentence, in the third person, filled from a track record."""
    if record is None:
        return "Strata has no backtest results yet, so it gives no track record."
    if record["abstention"] is not None:
        return (f"Strata has fewer than {record['abstention']['min_unseen_packages']} packages from {record['year']} "
                "that it had not seen, so it gives no track record yet.")
    return (f"Of {record['n']} packages from {record['year']} that Strata had not seen, {record['m']} finished inside "
            f"its 8-in-10 range, where a well-sized range catches about {record['expected']}.")


def render(years: dict[int, dict], model, no_model, settings: TimeEstimateSettings, thresholds: Thresholds,
           trained_on: dt.date) -> str:
    """The model card for the model a run trained, from that run's stored test years."""
    value = thresholds.value
    canceled = ("left out, and named in the coverage line" if not value("past_range.canceled_as_still_open")
                else "kept as still open")
    lines = [
        f"# Model card: {settings.registered_model}",
        "",
        "## What it is for",
        "",
        "This model gives Strata's time estimate: a range for how long one package's procurement takes, from its "
        "specific procurement notice to its signed contract. It gives the months by which a quarter, half, three "
        "quarters and 8 in 10 of packages like it were signed. The package workspace shows it beside the past "
        "range of comparable packages.",
        "",
        f"The model is XGBoost's survival model (accelerated failure time), learner {settings.learner}, with "
        f"conformal ranges. Settings: {', '.join(f'{k} {v}' for k, v in settings.learner_settings.items())}.",
        "",
        "## Data",
        "",
        f"- Every package Strata could measure as of {_date(trained_on)}: procurement notices and contract awards "
        "for every country (strata.gold.notice, strata.gold.contract and strata.gold.package), joined on the STEP "
        "reference. A signed package counts its days from its specific procurement notice to its signed contract.",
        "- A package still open counts its days so far, kept as not signed yet (censored), as in the past range. "
        f"A canceled package is {canceled} (config/thresholds.toml, past_range.canceled_as_still_open).",
        "- The Procurement Plans Strata has read (strata.silver.plan_rows and strata.silver.plan_step_delays), and "
        "the CPIA and WGI scores (strata.gold.governance_score), each version as published.",
    ]
    if model is not None:
        every = ORDINALS.get(settings.calibration_every, f"{settings.calibration_every}th")
        total, still_open = model.training_packages, model.calibration_still_open
        lines.append(f"- Strata could measure {total} packages. Every {every} one, in the order they were advertised, "
                     f"sized the ranges: {model.calibration_packages} packages, "
                     + ("none of them still open" if not still_open else f"{_words(still_open)} of them still open")
                     + f". The model learned from the other {total - model.calibration_packages}.")
        lines.append("- " + _share_sentence(
            model.listed_packages, total,
            all_of="A Procurement Plan Strata has read listed every one of them when it was advertised.",
            none_of="No Procurement Plan Strata has read listed any of them when it was advertised, so none has plan "
                    "features.",
            some_of="A Procurement Plan Strata has read listed {k} of the {n} when they were advertised; the others "
                    "have no plan features."))
        lines.append("- " + _share_sentence(
            model.governance_packages, total,
            all_of="Every one of them had a governance score published by the day it was advertised.",
            none_of="None of them had a governance score published by the day it was advertised, so the governance "
                    "features were empty: the versions Strata holds were published after every one was advertised.",
            some_of="Of them, {k} had a governance score published by the day they were advertised; for the others "
                    "the governance features were empty."))
    else:
        lines.append(f"- No model was trained: {NO_MODEL.get(no_model.reason, no_model.reason).format(fewest=value('time_estimate.min_calibration_packages'))}.")
    lines += [
        "",
        "## Features",
        "",
        "Each feature is taken as the package stood on the day it was advertised, or, for a package not yet "
        "advertised, as planned on the day the model was frozen:",
        "",
        "- Method, category (the plan table), Market Approach, Review Type, Prequalification and Estimated Amount "
        "(US$), from the newest Procurement Plan version public that day. A package no plan listed takes its "
        "method, category and market approach from its specific procurement notice.",
        "- The plan's own planned duration: from the planned notice to the planned signed contract in the "
        "package's first listing.",
        "- Country and region.",
        f"- Governance scores, as the Indicators API had published them that day: {', '.join(settings.governance_indicators)}.",
        "- The implementing agency's history: how many of its packages were signed by that day, and their middle "
        "number of days.",
        "",
        "## What it never reads",
        "",
        "- Signed amounts, or anything else from a contract, since a contract comes after the time being estimated.",
        "- The same project's ICR, or any completion report.",
        "- Revised dates: the planned duration comes from the first listing, and plan rows from the version public "
        "when the package was advertised. Actual Amount and Process Status are never read.",
        "- Later ratings: governance scores come as published on the day, never a later revision.",
        "- Anything public after the day the model was frozen. The replay harness refuses any such row.",
        "",
        "## Backtests",
        "",
        "Each test year's model learned only from packages Strata could measure by January 1 of that year. It was "
        "tested on the packages a Procurement Plan public then listed and that were advertised during the year. "
        "Errors are medians in months: half of the packages were closer than this.",
        "",
        "| Test year | Packages it had not seen | Inside the 8-in-10 range | A well-sized range catches about | "
        "8-in-10 point (months) | Middle half width (months) | Typical error (months) | Past range's typical "
        "error (months) | Plans' typical error (months) | MLflow run |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for year, record in sorted(years.items()):
        if "abstention" in record:
            reason = NO_MODEL.get(record["abstention"], record["abstention"]).format(
                fewest=value("time_estimate.min_calibration_packages"))
            lines.append(f"| {year} | no model: {reason} | | | | | | | | {record['mlflow_run_id']} |")
            continue
        lines.append("| " + " | ".join([str(year), *(_cell(record, key) for key in (
            "n", "m", "expected", "width_80_months", "width_50_months", "error_estimate_months",
            "error_past_range_months", "error_plan_months")), record["mlflow_run_id"] or ""]) + " |")
    lines += ["", "## Coverage", "", *_coverage(years, thresholds), "",
              "## Track record", "", sentence(track_record(years, thresholds)), "",
              "## When it gives no range", "",
              f"- Fewer than {value('time_estimate.min_comparables')} comparable packages, subgroups included: a "
              f"what-if option needs {value('what_if.min_subgroup')} comparable packages that went with it. Strata "
              "shows the comparable packages instead.",
              "- An as-of date before the end of its training data"
              + (f", {_date(model.training_through)}" if model is not None else "") + ".",
              f"- A package whose {' or '.join(FEATURE_NAMES.get(name, name) for name in settings.range_checked)} lies outside "
              "the values it learned from.",
              "- Fewer than " + str(value("time_estimate.min_unseen_packages")) + " packages in the latest test year "
              "means no track record.", ""]
    return "\n".join(lines)
