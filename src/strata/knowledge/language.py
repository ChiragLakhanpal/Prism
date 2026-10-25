"""The language of a passage or a question, read from its words (ticket 42).

Each passage takes its language from its document's record: the Documents API's lang field, mapped to an ISO
639-1 code by config/languages.toml. check() samples the passages and asks a language detector, which reads
only their words, whether it agrees, so the check never rests on how the language was set. It writes one row
per sampled passage to strata.ops.passage_language_checks, and two data readiness measures to
strata.ops.data_readiness for the whole slice: how many passages carry a language the registry knows
(passages_language_set), and how many sampled passages the detector agrees with
(passage_language_sample_agrees).

The detector is py3langid, whose model ships inside its wheel, so it runs with the network off. It chooses only
among the languages config/languages.toml lists. detect() also reads the language of a question or of an upload's
descriptions taken together; the screens set a lang attribute from it only when the detector is at least
lang.min_confidence sure (config/thresholds.toml).
"""

from __future__ import annotations

import datetime as dt
import hashlib
from collections import defaultdict
from dataclasses import dataclass
from functools import cache
from importlib import resources
from typing import Protocol

from strata.config import Thresholds, load_languages
from strata.lakehouse.engine import Engine

SOURCE = "documents"
SUBJECT = "all"  # the whole slice
CHECK_COLUMNS = ("run_id", "passage_id", "language", "detected", "confidence", "agrees", "detector", "measured_at",
                 "public_from")
MEASURE_COLUMNS = ("run_id", "source", "subject", "measure", "kind", "count", "denominator", "as_of", "detail",
                   "measured_at", "public_from")


@dataclass(frozen=True)
class Detected:
    code: str
    confidence: float


class Detector(Protocol):
    name: str

    def detect(self, text: str) -> Detected:
        """The language of the text, among the registry's languages, and how sure the detector is."""


@cache
def _identifier():
    from py3langid.langid import MODEL_FILE, LanguageIdentifier

    identifier = LanguageIdentifier.from_pickled_model(MODEL_FILE, norm_probs=True)
    identifier.set_languages([entry.code for entry in load_languages().languages])
    return identifier


class LangidDetector:
    """py3langid's model, limited to the languages config/languages.toml lists."""

    name = "py3langid 0.3.0"

    def detect(self, text: str) -> Detected:
        code, confidence = _identifier().classify(text)
        return Detected(str(code), round(float(confidence), 4))


def detect(text: str | None, thresholds: Thresholds, detector: Detector | None = None) -> str | None:
    """The language of a question or of an upload's descriptions, or None when there are no words or the detector
    is less than lang.min_confidence sure."""
    if not text or not text.strip():
        return None
    found = (detector or LangidDetector()).detect(text)
    return found.code if found.confidence >= float(thresholds.value("lang.min_confidence")) else None


def _sql(name: str) -> str:
    return (resources.files("strata.knowledge") / "sql" / "language" / f"{name}.sql").read_text()


def _stable(passage_id: str) -> str:
    return hashlib.sha256(passage_id.encode("utf-8")).hexdigest()


def sample(passages: list[dict], size: int) -> list[dict]:
    """size passages shared equally between the languages they are written in, each language's share chosen by a
    stable hash of the passage id, so every run of the same slice samples the same passages. A language with fewer
    passages than its share gives all it has, and the rest go to the others."""
    by_language: dict[str, list[dict]] = defaultdict(list)
    for passage in sorted(passages, key=lambda row: _stable(row["passage_id"])):
        by_language[passage["language"]].append(passage)
    chosen: list[dict] = []
    left = dict(by_language)
    while left and len(chosen) < size:
        share = max(1, (size - len(chosen)) // len(left))
        for code in sorted(left, key=lambda code: len(left[code])):
            take = left[code][:share]
            chosen += take[:size - len(chosen)]
            left[code] = left[code][len(take):]
        left = {code: rows for code, rows in left.items() if rows}
    return chosen


def check(engine: Engine, run_id: str, when: dt.datetime, thresholds: Thresholds,
          detector: Detector | None = None) -> tuple[int, int]:
    """Check a sample of the slice's passages against the detector, and write what it found. Returns how many
    sampled passages agree, and how many were sampled."""
    detector = detector or LangidDetector()
    known = {entry.code for entry in load_languages().languages}
    counts = engine.run(_sql("counts"), {})
    by_language = {str(code): int(count) for code, count in counts.rows}
    result = engine.run(_sql("passages"), {"min_chars": int(thresholds.value("lang.min_sample_chars"))})
    passages = [dict(zip(result.columns, row, strict=True)) for row in result.rows]
    chosen = sample([row for row in passages if row["language"] in known], int(thresholds.value("lang.sample_size")))
    rows = []
    for passage in chosen:
        found = detector.detect(passage["text"])
        rows.append((run_id, passage["passage_id"], passage["language"], found.code, found.confidence,
                     found.code == passage["language"], detector.name, when, when.date()))
    engine.insert_rows("strata.ops.passage_language_checks", CHECK_COLUMNS, rows)
    total, set_ = sum(by_language.values()), sum(count for code, count in by_language.items() if code in known)
    agree = sum(1 for row in rows if row[5])
    shares = ", ".join(f"{sum(1 for row in rows if row[2] == code)} in {code}" for code in sorted({r[2] for r in rows}))
    engine.insert_rows("strata.ops.data_readiness", MEASURE_COLUMNS, [
        (run_id, SOURCE, SUBJECT, "passages_language_set", "coverage", set_, total, None,
         "This counts the passages that carry a language config/languages.toml lists, from their document's record "
         "in the Documents API, out of every passage.", when, when.date()),
        (run_id, SOURCE, SUBJECT, "passage_language_sample_agrees", "read_well", agree, len(rows), None,
         f"This counts the sampled passages whose language {detector.name} read the same from their words alone, "
         f"out of the {len(rows)} passages sampled ({shares or 'none'}).", when, when.date()),
    ])
    return agree, len(rows)
