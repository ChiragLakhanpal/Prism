"""The review list and the labeling tool for supplier name matching (ticket 19).

- review_list(engine) reads the review list as the viewer: each candidate pair that waits for a person
  (strata.ops.supplier_review_list), with both sides' names, countries and contracts, why it waits,
  and the model's judgement when it gave one.
- labeling_list(engine, limit) reads the labeling tool's next pairs as the viewer: candidate pairs of
  the latest run with no label yet, most likely first, without where Strata sent them, and how many
  pairs are labeled of how many found, beside docs/PLAN.md section 5's aim of 1,000.
- SupplierLog writes a person's decision (merge or no merge, with the reason) to
  strata.ops.supplier_review_decisions, and a label to strata.ops.supplier_pair_labels, as the app's
  own service principal, as OpenedLog does. The reviewer or labeler is the user id of the viewer the
  Databricks App forwarded with the request, never anyone a module keeps. No roles file names the
  reviewers yet (tickets 29 and 38 bring one), so any signed-in viewer may decide or label.

A decision takes effect at the next nightly run, which applies it before the thresholds and the model
(strata.knowledge.suppliers.resolve). A label never merges or splits a pair: labels only measure how
often auto-merge is right (strata.ops.supplier_match_quality). Suppliers are never scored, ranked or
profiled here.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from functools import cache
from pathlib import Path

from strata.lakehouse.engine import Engine

SQL = Path(__file__).resolve().parent / "sql" / "suppliers"
CHOICES = ("merge", "no_merge")


@cache
def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


def _dicts(engine: Engine, name: str, params: dict | None = None) -> list[dict]:
    result = engine.run(_query(name), params)
    return [dict(zip(result.columns, row, strict=True)) for row in result.rows]


def _side(row: dict, side: str) -> dict:
    contracts = row[f"{side}_contracts"]
    return {"key": row[f"{side}_key"], "name": row[f"{side}_name"], "country": row[f"{side}_country"],
            "contracts": contracts.split(", ") if contracts else []}


def review_list(engine: Engine) -> dict:
    """Each pair that waits for a person."""
    pairs = []
    for row in _dicts(engine, "review_list"):
        model = None if row["model_decision"] is None else {
            "decision": row["model_decision"], "confidence": row["model_confidence"], "reason": row["model_reason"]}
        pairs.append({"pair_id": row["pair_id"], "left": _side(row, "left"), "right": _side(row, "right"),
                      "match_probability": row["match_probability"], "review_reason": row["review_reason"],
                      "model": model})
    return {"pairs": pairs, "count": len(pairs)}


def labeling_list(engine: Engine, limit: int, labeled_pairs_target: int) -> dict:
    """The next pairs to label, and how many are labeled."""
    pairs = [{"pair_id": row["pair_id"], "left": _side(row, "left"), "right": _side(row, "right")}
             for row in _dicts(engine, "labeling_list", {"limit": limit})]
    [counts] = _dicts(engine, "label_counts")
    return {"pairs": pairs, "labeled_pairs": int(counts["labeled_pairs"]),
            "candidate_pairs": int(counts["candidate_pairs"]), "labeled_pairs_target": labeled_pairs_target}


def _close(engine) -> None:
    close = getattr(engine, "close", None)
    if callable(close):
        close()


class UnknownPair(LookupError):
    """No candidate pair of the latest run has this pair_id."""


class SupplierLog:
    """Decisions and labels on candidate pairs. engine() opens the engine that writes them."""

    def __init__(self, engine: Callable[[], Engine], now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)):
        self.engine = engine
        self.now = now

    def _write(self, query: str, pair_id: str, values: dict, stamped: str) -> None:
        """One row about a pair of the latest run, stamped now in the column stamped names."""
        engine = self.engine()
        try:
            found = _dicts(engine, "pair", {"pair_id": pair_id})
            if not found:
                raise UnknownPair(pair_id)
            at = self.now()
            engine.run(_query(query), {"pair_id": pair_id, "left_key": found[0]["left_key"],
                                       "right_key": found[0]["right_key"], **values, stamped: at,
                                       "public_from": at.astimezone(dt.UTC).date()})
        finally:
            _close(engine)

    def decide(self, pair_id: str, decision: str, reviewer: str, reason: str) -> None:
        """Record a person's decision. Raises UnknownPair for a pair the latest run did not find."""
        self._write("record_decision", pair_id, {"decision": decision, "reviewer": reviewer, "reason": reason},
                    "decided_at")

    def label(self, pair_id: str, label: str, labeler: str) -> None:
        """Record a person's label. Raises UnknownPair for a pair the latest run did not find."""
        self._write("record_label", pair_id, {"label": label, "labeler": labeler}, "labeled_at")
