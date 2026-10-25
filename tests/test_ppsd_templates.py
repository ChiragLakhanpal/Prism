"""The PPSD template registry and Table I (ticket 36): config/ppsd_templates.toml and config/thresholds.toml's
[ppsd_table_i].

Every column name, rating, stage and Table I amount is checked against tests/ground_truth/values.toml, whose
quotes tests/test_ground_truth_values.py finds word for word on the recorded templates' and guidance's pages.
Nothing here is typed from memory: a value that differs from the template fails here.
"""

import tomllib
from decimal import Decimal
from pathlib import Path

import pytest

from strata import config
from strata.config import ConfigError
from strata.drafts import ppsd_rows

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}


def test_the_short_form_has_exactly_the_template_s_three_columns_word_for_word():
    short = config.load_ppsd_templates().forms["short"]

    assert [column.header for column in short.columns] == ["Risk Description", "Description of mitigation", "Risk Owner"]
    for column in short.columns:
        source = VALUES[column.value]
        assert column.header == source["value"]
        assert (source["document"], source["pdf_page"]) == (short.document, short.pdf_page)


def test_the_long_form_has_the_template_s_seven_columns_in_its_order_word_for_word():
    long = config.load_ppsd_templates().forms["long"]

    assert [column.key for column in long.columns] == [
        "risk_description", "likelihood", "impact", "score", "mitigation", "risk_owner", "stage"]
    for column in long.columns:
        source = VALUES[column.value]
        assert column.header == source["value"]
        assert (source["document"], source["pdf_page"]) == (long.document, long.pdf_page)
    assert [(column.key, column.letter) for column in long.columns if column.letter] == [("likelihood", "A"), ("impact", "B")]


def test_strata_fills_only_the_risk_description_and_the_mitigation_and_people_fill_the_rest():
    templates = config.load_ppsd_templates()

    for form in templates.forms.values():
        assert [column.key for column in form.columns if column.filled_by == "strata"] == ["risk_description", "mitigation"]
    people = {column.key: column for form in templates.forms.values() for column in form.columns if column.filled_by == "people"}
    assert set(people) == {"risk_owner", "likelihood", "impact", "score", "stage"}
    # Export waits for every owner, and in the Long Form for every rating; the stage is optional (the 36 brief, 5.3).
    assert {key: column.hold for key, column in people.items()} == {
        "risk_owner": "owners", "likelihood": "ratings", "impact": "ratings", "score": "ratings", "stage": None}
    assert templates.default_form == "short"


def test_the_ratings_and_the_stages_are_the_guidance_s_own():
    templates = config.load_ppsd_templates()

    rated = " ".join(f"{level.value} = {level.label} ({level.short})" for level in templates.ratings)
    assert rated == VALUES["ppsd-ratings"]["quote"]
    assert [level.value for level in templates.ratings] == [1, 2, 3, 4, 5]
    assert list(templates.stages) == [VALUES[f"ppsd-stage-{n}"]["value"] for n in range(1, 7)]
    # The score's bounds follow from the template's own definition, A times B, with A and B from 1 to 5.
    assert (templates.score.minimum, templates.score.maximum) == (1, 25)
    assert templates.score.definition in VALUES["ppsd-long-score"]["value"]


def table_i_row(value_id: str) -> list[Decimal]:
    return [Decimal(part) for part in VALUES[value_id]["value"].split("≥")[1:]]


@pytest.mark.parametrize("category, value_id", [
    ("Works", "ppsd-table-i-works"),
    ("Goods", "ppsd-table-i-goods"),
    ("Non-consulting Services", "ppsd-table-i-goods"),
    ("Consultant Services", "ppsd-table-i-consultants"),
])
def test_the_thresholds_file_holds_table_i_word_for_word_in_us_dollars(category, value_id):
    limits = config.load_thresholds()
    levels = VALUES["ppsd-table-i-risk-levels"]["value"].removeprefix("Procurement Risk ").split()

    assert limits.value("ppsd_table_i.risk_levels") == levels
    row = limits.value(f"ppsd_table_i.from_usd.{limits.value(f'ppsd_table_i.row.{category}')}")
    assert [Decimal(row[level]) / 1_000_000 for level in levels] == table_i_row(value_id)


def test_the_long_form_is_offered_from_the_lowest_table_i_threshold_of_the_package_s_category():
    """Table I's thresholds depend on the procurement risk the Borrower and the World Bank agree, which Strata
    cannot see, so it offers the Long Form from the lowest one: the High risk column."""
    limits = config.load_thresholds()

    assert limits.value("ppsd_table_i.offer_long_form_at") == "High"
    below = ppsd_rows.table_i(limits, "Works", Decimal("15000000"))
    assert (below["applies"], below["threshold"], below["amount"], below["risk_level"]) == (False, "50000000.00", "15000000.00", "High")
    at = ppsd_rows.table_i(limits, "Works", Decimal("50000000"))
    assert at["applies"] is True
    assert ppsd_rows.table_i(limits, "Consultant Services", Decimal("16000000"))["applies"] is True
    assert ppsd_rows.table_i(limits, "Goods", None) == {"applies": False, "amount": None, "threshold": None,
                                                       "currency": "USD", "category": "Goods", "risk_level": "High"}


def test_a_registry_column_without_its_ground_truth_entry_is_refused(tmp_path):
    source = (ROOT / "config" / "ppsd_templates.toml").read_text()
    broken = tmp_path / "ppsd_templates.toml"
    broken.write_text(source.replace('filled_by = "strata"', 'filled_by = "model"', 1))

    with pytest.raises(ConfigError, match="filled_by"):
        config.load_ppsd_templates(broken)
