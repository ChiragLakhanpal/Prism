"""Assertions and disagreements at seam 1, the lakehouse run over the fixture (ticket 20).

Ratings, dates and amounts from records and documents become dated assertions in strata.gold.assertion,
and the run finds the disagreements between them in strata.gold.disagreement, with the assertion the
evidence ladder (config/evidence_ladder.toml) leans on. Expected values come from
tests/ground_truth/values.toml, which quotes each ISR, the ICR and the ICR Reviews with their pages,
never from the code.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
TRUTH = {entry["id"]: entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
ISR = "Implementation Status and Results Report"


def value(key: str):
    return TRUTH[key]["value"]


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


def rows(engine, sql: str, **params) -> list[dict]:
    result = engine.run(sql, params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def isr_assertions(engine, attribute="pdo_progress") -> list[dict]:
    return rows(engine, "SELECT * FROM strata.gold.assertion WHERE subject_id = :subject AND attribute = :attribute "
                        "AND document_type = :isr ORDER BY made_at", subject="P130164", attribute=attribute, isr=ISR)


# ── Assertions ───────────────────────────────────────────────────────────

def test_each_isr_rates_progress_for_the_period_since_the_isr_before_it(engine):
    found = isr_assertions(engine)

    assert [row["value"] for row in found] == [value(f"isr-{n}-rating") for n in range(1, 14)]
    assert [row["made_at"] for row in found] == [value(f"isr-{n}-date") for n in range(1, 14)]
    assert [row["sequence"] for row in found] == list(range(1, 14))
    isr_7 = found[6]
    assert isr_7["field_name"] == "Progress towards achievement of PDO"
    assert (isr_7["period_start"], isr_7["period_end"]) == (value("isr-6-date") + dt.timedelta(days=1),
                                                            value("isr-7-date"))
    assert isr_7["public_from"] == value("isr-7-date")
    assert (isr_7["evidence_tier"], isr_7["form"]) == ("isr", "rating_field")
    # The passage ticket 18 issued for ISR 7's overall ratings, on its first page, which a claim cites.
    assert isr_7["evidence_id"] == "strata.gold.passage:26733307/v1/s4"
    assert isr_7["pdf_page"] == TRUTH["isr-7-rating"]["pdf_page"]


def test_every_assertion_has_its_subject_attribute_value_period_dates_source_and_evidence_tier(engine):
    """Criterion 8: the schema every assertion keeps (spec, "The knowledge model")."""
    required = ("assertion_id", "subject_kind", "subject_id", "project_id", "attribute", "attribute_kind",
                "field_name", "value", "value_form", "period_event", "period_start", "period_end", "made_at",
                "public_from", "evidence_tier", "form", "source_key", "document_id", "passage_id", "evidence_id",
                "read_by")
    found = rows(engine, "SELECT * FROM strata.gold.assertion")

    assert len(found) > 13
    missing = [(row["assertion_id"], column) for row in found for column in required if row[column] in (None, "")]
    assert missing == []
    assert {row["evidence_tier"] for row in found} <= {"pad", "isr", "icr", "ieg", "record"}
    assert {row["subject_kind"] for row in found} <= {"project", "package"}
    assert all(row["period_start"] <= row["period_end"] for row in found)
    assert len({row["assertion_id"] for row in found}) == len(found)
