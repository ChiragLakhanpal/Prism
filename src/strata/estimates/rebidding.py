"""Rebidding labels (ticket 28): whether a package was advertised again, as the records public on a date say.

No field in the records says a package was advertised again, so three sources say it (docs/PLAN.md section 7,
the spec's "Estimates"), each read as it stood on the date (sql/rebidding/labels.sql):

- no_award: no contract in the awards dataset and no Contract Award notice with a signature date, by the date,
  rebidding.no_award_after_days or more after its bids were due (config/thresholds.toml). A package still
  inside that wait may yet be signed, so it is undecided, never "not advertised again".
- same_reference: a later notice of the same type under the same STEP reference (is_readvertised, the one rule
  for a re-advertisement, which the contract trail can read too).
- canceled_row: Process Status Canceled in the newest Procurement Plan version public on the date that lists
  it, and no signed contract. Terminated means a signed contract, so only Canceled counts, and a plan row
  repeated in every version is one package.

A package one source names was advertised again. A package no source names that was signed by the date was not.
Any other package is undecided on that date: the backtests leave it out, and rebidding_risk counts it among the
packages with no sign of being advertised again, which its words say.

reason() finds, in a package's notices, the first sentence that gives a reason in words, by the patterns in
config/rebidding_reasons.toml, and returns it word for word. record_label_counts() writes how many packages each
source names to strata.ops.rebidding_labels, as the nightly job's score task does.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.config import RebiddingReason, Thresholds, load_rebidding_reasons, load_thresholds
from strata.lakehouse.passages import LANGUAGES

NO_AWARD, SAME_REFERENCE, CANCELED_ROW = "no_award", "same_reference", "canceled_row"
SOURCES = (NO_AWARD, SAME_REFERENCE, CANCELED_ROW)
ANY = "any"  # the label counts' row for packages any source names
CANCELED = "Canceled"
EARLIEST = dt.date(1900, 1, 1)
NOTICE_TABLE, PLAN_ROW_TABLE = "strata.silver.notices", "strata.silver.plan_rows"
COUNTS_TABLE = "strata.ops.rebidding_labels"
COUNT_COLUMNS = ("run_id", "source", "count", "denominator", "as_of", "measured_at", "public_from")
LANGUAGE_CODES = {name.lower(): code for name, code in LANGUAGES.items()}

Rows = Callable[..., list[dict]]


def sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "rebidding" / name).read_text()


def as_date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) and not isinstance(value, dt.datetime) else dt.date.fromisoformat(str(value)[:10])


def iso(value) -> str | None:
    day = as_date(value)
    return day.isoformat() if day else None


def engine_rows(engine, as_of: dt.date) -> Rows:
    """A query's rows as dicts, with :as_of bound to the date: how rebidding_risk and the score task read."""
    def rows(query: str, **params) -> list[dict]:
        result = engine.run(query, {"as_of": as_of, **params})
        return [dict(zip(result.columns, row, strict=True)) for row in result.rows]
    return rows


def notice_evidence_id(notice_id: str) -> str:
    return f"{NOTICE_TABLE}:{notice_id}"


def plan_row_evidence_id(document_id: str, step_reference: str) -> str:
    """check_plan's form for a plan row, so one plan row has one evidence id on every page."""
    return f"{PLAN_ROW_TABLE}:{document_id}/{step_reference}"


@dataclass(frozen=True)
class Evidence:
    """A record that says a package was advertised again: a notice or a plan row."""

    evidence_id: str
    public_from: str
    record_kind: str  # notice, award_notice or plan_row
    reference: str  # the notice's id, or the plan row's STEP reference
    date: str  # the notice's date, or the plan version's date
    agency: str | None = None  # a plan row's implementing agency

    def as_row(self) -> dict:
        return {"evidence_id": self.evidence_id, "public_from": self.public_from, "record_kind": self.record_kind,
                "reference": self.reference, "date": self.date, "agency": self.agency}


@dataclass
class Label:
    """One package as the records public on a date say: the sources that name it, if any."""

    step_reference: str
    project_id: str | None
    country_code: str | None
    country_name: str | None
    category: str | None
    method: str | None
    notice_id: str
    notice_date: dt.date
    notice_public_from: str
    bids_due: dt.date | None
    signed_on: dt.date | None
    process_status: str | None
    public_from: dt.date
    sources: dict[str, Evidence] = field(default_factory=dict)

    def notice(self) -> Evidence:
        """Its specific procurement notice, as a record."""
        return Evidence(notice_evidence_id(self.notice_id), self.notice_public_from, "notice", self.notice_id,
                        iso(self.notice_date))

    @property
    def advertised_again(self) -> bool:
        return bool(self.sources)

    @property
    def decided(self) -> bool:
        """Whether the records say either way: advertised again, or signed."""
        return self.advertised_again or self.signed_on is not None


def is_readvertised(row: dict) -> bool:
    """The one rule for a re-advertisement: a later notice of the same type under the same STEP reference, which
    labels.sql finds (again_notice_id)."""
    return bool(row.get("again_notice_id"))


def _label(row: dict, as_of: dt.date, wait: int) -> Label:
    signed_on = as_date(row["signed_on"])
    notice_date = as_date(row["notice_date"])
    label = Label(row["step_reference"], row["project_id"], row["country_code"], row["country_name"],
                  row["procurement_category"], row["procurement_method"], row["notice_id"], notice_date,
                  iso(row["notice_public_from"]), as_date(row["bids_due"]), signed_on, row["process_status"],
                  as_date(row["public_from"]))
    notice = label.notice()
    due = label.bids_due or notice_date
    if signed_on is None and due + dt.timedelta(days=wait) <= as_of:
        label.sources[NO_AWARD] = notice
    if is_readvertised(row):
        label.sources[SAME_REFERENCE] = Evidence(notice_evidence_id(row["again_notice_id"]), iso(row["again_public_from"]),
                                                 "notice", row["again_notice_id"], iso(row["again_notice_date"]))
    if signed_on is None and row["process_status"] == CANCELED:
        label.sources[CANCELED_ROW] = Evidence(plan_row_evidence_id(row["plan_document_id"], row["step_reference"]),
                                               iso(row["plan_public_from"]), "plan_row", row["step_reference"],
                                               iso(row["plan_date"]), row["implementing_agency"])
    return label


def labels(rows: Rows, as_of: dt.date, thresholds: Thresholds | None = None, refs: list[str] | None = None,
           period_from: dt.date | None = None) -> dict[str, Label]:
    """Every package advertised from period_from (past_range.period_from unless given; refs alone when given) as the
    records public on the as-of date say, keyed by STEP reference. rows runs a query with :as_of bound to the date:
    engine_rows(), or the replay harness's reader, which also refuses any row public after its date."""
    limits = thresholds or load_thresholds()
    start = period_from or as_date(limits.value("past_range.period_from"))
    wait = int(limits.value("rebidding.no_award_after_days"))
    if refs is not None and not refs:
        return {}
    found = rows(sql("labels.sql"), period_from=start, refs=",".join(refs) if refs is not None else None)
    return {row["step_reference"]: _label(row, as_of, wait) for row in found}


# ── A reason in words ────────────────────────────────────────────────────

# A sentence ends at a full stop, question mark or exclamation mark that a capital letter follows, with or
# without a space between them: "posted on 4th February,2020.The Request for Bids has been cancelled."
SENTENCE_END = re.compile(r"(?<=[.!?])\s*(?=[A-Z])")


def sentences(text: str) -> list[str]:
    """A notice's sentences, in order: each line split where a sentence ends, word for word."""
    found = []
    for line in text.splitlines():
        found += [part.strip() for part in SENTENCE_END.split(line) if part.strip()]
    return found


@dataclass(frozen=True)
class Reason:
    code: str
    text: str
    lang: str
    notice_id: str
    notice_type: str
    notice_date: str
    public_from: str


def reason_in(text: str, reasons: tuple[RebiddingReason, ...] | None = None) -> tuple[str, str] | None:
    """The first sentence of a notice's text that gives a reason in words, with its reason's code, or None."""
    for sentence in sentences(text or ""):
        for reason in reasons if reasons is not None else load_rebidding_reasons():
            if any(pattern.search(sentence) for pattern in reason.patterns):
                return reason.code, sentence
    return None


def reasons(rows: Rows, refs: list[str]) -> dict[str, Reason]:
    """For each named package, the first sentence of its notices, oldest first, that gives a reason in words."""
    if not refs:
        return {}
    registry = load_rebidding_reasons()
    found: dict[str, Reason] = {}
    for notice in rows(sql("notice_texts.sql"), refs=",".join(refs)):
        if notice["step_reference"] in found:
            continue
        given = reason_in(notice["notice_text"], registry)
        if given:
            language = LANGUAGE_CODES.get(str(notice["notice_language"] or "").strip().lower(), "en")
            found[notice["step_reference"]] = Reason(given[0], given[1], language, notice["notice_id"],
                                                     notice["notice_type"], iso(notice["notice_date"]),
                                                     iso(notice["public_from"]))
    return found


# ── The label counts in strata.ops ───────────────────────────────────────

def label_counts(found: dict[str, Label]) -> dict[str, int]:
    """How many packages each source names, and any of them, each package once."""
    counts = {source: sum(1 for label in found.values() if source in label.sources) for source in SOURCES}
    return {**counts, ANY: sum(1 for label in found.values() if label.advertised_again)}


def record_label_counts(engine, run_id: str, clock: Callable[[], dt.datetime],
                        thresholds: Thresholds | None = None) -> int:
    """Write how many packages each source names, out of every package advertised from past_range.period_from, as
    the records public today say, to strata.ops.rebidding_labels. Rows are only added."""
    measured_at = clock()
    as_of = measured_at.astimezone(dt.UTC).date()
    found = labels(engine_rows(engine, as_of), as_of, thresholds)
    rows = [(run_id, source, count, len(found), as_of, measured_at, as_of) for source, count in label_counts(found).items()]
    return engine.insert_rows(COUNTS_TABLE, COUNT_COLUMNS, rows)


# ── The champion's natural frequency ─────────────────────────────────────
# What rebidding_risk reads, kept apart from the models (strata.estimates.rebidding_model), so the app's server
# never imports numpy or XGBoost. The backtests write these rows (strata.estimates.rebidding_backtest).

SCORER = "rebidding_backtest"
REGISTERED = "registered_model"
CHAMPION = "champion"
# The baseline each model must beat: the share advertised again among a package's comparable packages, as
# rebidding_risk counted them on the cutoff (the 28 design brief, section 7.2).
BASELINE = "comparables_rate"


def in10(probability: float) -> int:
    """A chance as a whole number in 10, rounded half up."""
    return int((Decimal(str(probability)) * 10).quantize(Decimal(1), ROUND_HALF_UP))


def band(k: int) -> str:
    """The words that go with k in 10: fewer than 1, about k, or more than 9 (find_comparables' rule)."""
    return "below_1" if k == 0 else "above_9" if k == 10 else "about"


def champion(rows: Rows) -> dict | None:
    """The latest champion registered by a run public on the reader's date, as one record, or None."""
    found = rows(sql("champion.sql"), scorer=SCORER)
    if not found:
        return None
    record = {"run_id": found[0]["run_id"], "model": found[0]["model"], "version": int(found[0]["segment"]),
              "run_date": iso(found[0]["public_from"])}
    for row in found:
        value = row["value"]
        record[row["measure"]] = row["value_text"] if value is None else (int(value) if float(value).is_integer() else float(value))
    return record


def natural_frequency(call, m: int, floor: int, step_reference: str | None) -> dict:
    """The model block of rebidding_risk's result, as of the call's date."""
    block = {"shown": False, "in10": None, "band": None, "not_shown_reason": None, "min_comparables": floor,
             "learner": None, "track_record": None, "score_date": None}
    if m < floor:
        return {**block, "not_shown_reason": "too_few"}
    rows = engine_rows(call.engine, call.as_of)
    held = champion(rows)
    if held is None:
        return {**block, "not_shown_reason": "no_results"}
    track = {"n_test": int(held["n_test"]), "test_year": int(held["test_year"]),
             "beat_baseline": bool(held["beat_baseline"]), "baseline_code": BASELINE, "run_date": held["run_date"]}
    block = {**block, "learner": held["learner"], "track_record": track}
    if not track["beat_baseline"]:
        return {**block, "not_shown_reason": "not_better"}
    scored = rows(sql("score.sql"), step_reference=step_reference, model=held["model"],
                  version=held["version"]) if step_reference else []
    if not scored:
        return {**block, "not_shown_reason": "not_scored"}
    k = int(scored[0]["in10"])
    return {**block, "shown": True, "in10": k, "band": band(k), "score_date": iso(scored[0]["scored_on"])}
