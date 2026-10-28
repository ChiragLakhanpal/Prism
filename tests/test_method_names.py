"""Method names in French and in older words, accepted on input and written back in the current Procurement
Regulations' names, at seam 1 (ticket 42).

Cameroon's Procurement Plan of October 10, 2018 (P143940) is in French. Its STEP tables write each method by
STEP's French name, and its list of abbreviations gives the French plan template's old names (values.toml,
plan-cm-*). The plan reader runs over the recorded plan as the fixture build runs it over the demo plan, reading
every plan version (ingestion.plan_versions = "all"): the fixture does not record the project's newest plan.
"""

import datetime as dt
import tomllib
from pathlib import Path

import pytest

from strata.config import load_method_names
from strata.fixture import recorded as fmt
from strata.lakehouse import catalog, clean, plans
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
VALUES = {value["id"]: value for value in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]}
RECORDED = ROOT / "data" / "fixture" / "recorded"


def read_cameroon_plan(engine):
    catalog.build(engine)
    plans.run_on_fixture(engine, "P143940", clock=lambda: dt.datetime(2026, 10, 23, 9, tzinfo=dt.UTC))
    result = engine.run("SELECT activity_reference_no, method, method_original, method_original_lang, method_mapped "
                        "FROM strata.silver.plan_rows ORDER BY activity_reference_no", {})
    return {row[0]: row[1:] for row in result.rows}


def test_a_french_method_name_in_a_plan_is_stored_as_the_current_regulations_name_beside_the_plan_s_words(
        every_plan_version):
    with DuckDBEngine.open() as engine:
        found = read_cameroon_plan(engine)

    bids, quotations = VALUES["plan-cm-50083-method"]["value"], VALUES["plan-cm-67752-method"]["value"]
    assert found["CM-PULCI-50083-CW-RFB"] == ("Request for Bids", bids, "fr", True)
    assert found["CM-PULCI-67752-CW-RFQ"] == ("Request for Quotations", quotations, "fr", True)
    assert {row[0] for row in found.values()} <= set(load_method_names().current)


def test_a_method_name_the_registry_does_not_list_is_kept_as_written_with_a_data_note(monkeypatch, tmp_path,
                                                                                     every_plan_version):
    """Without "Demande de prix" in the registry, the plan's words stay as written, the row is not marked mapped,
    and the plan gets a Data note for each such row instead of a guess."""
    registry = (ROOT / "config" / "method_names.toml").read_text().replace(
        'written = "Demande de prix"', 'written = "Demande de prix (not listed)"')
    (tmp_path / "method_names.toml").write_text(registry)
    trimmed = load_method_names(tmp_path / "method_names.toml")
    monkeypatch.setattr(clean, "METHOD_NAMES", trimmed)

    with DuckDBEngine.open() as engine:
        found = read_cameroon_plan(engine)
        notes = engine.run("SELECT activity_reference_no, method FROM strata.silver.plan_data_notes "
                           "WHERE note = 'method_unknown' ORDER BY activity_reference_no", {}).rows

    quotations = VALUES["plan-cm-67752-method"]["value"]
    assert found["CM-PULCI-67752-CW-RFQ"] == (quotations, quotations, None, None)
    assert ("CM-PULCI-67752-CW-RFQ", quotations) in [tuple(row) for row in notes]
    assert found["CM-PULCI-50083-CW-RFB"][0] == "Request for Bids"


def test_old_names_still_map_whatever_their_case_spaces_or_apostrophes():
    assert clean.method(name="International Competitive Bidding") == clean.Method("Request for Bids",
                                                                                 "Open - International")
    assert clean.method(code="aoi") == clean.Method("Request for Bids", "Open - International")
    assert clean.method(name="Appel d’offres") == clean.Method("Request for Bids", None)
    assert clean.method(name="Request for Bids") == clean.Method("Request for Bids", None)


@pytest.mark.parametrize("entry", [entry for entry in load_method_names().names if entry.source],
                         ids=lambda entry: entry.written)
def test_each_name_the_registry_reads_from_a_source_is_written_there(entry):
    """A registry entry with a source names a recorded file, and a document's page, that writes the name."""
    if entry.pdf_page is not None:
        text = fmt.pages(RECORDED / f"{entry.source}.pages.txt")[entry.pdf_page - 1]
    else:
        text = (RECORDED / entry.source).read_text()
    plain = clean.method_key(" ".join(text.split()))
    assert clean.method_key(entry.written) in plain


def test_the_procurement_plan_template_in_french_is_a_registered_source_under_its_own_title():
    """The source registry lists the French template among the document collections, under the title the recorded
    template prints on its first page, in French (values.toml, plan-template-fr-title)."""
    from strata.config import load_sources
    from strata.tools.data_readiness_for import registry_page

    title = VALUES["plan-template-fr-title"]
    [french] = [found for found in load_sources()["documents"].collections if found.language == "fr"]
    assert clean.method_key(french.name) == clean.method_key(title["value"])
    page = fmt.pages(RECORDED / f"{title['document']}.pages.txt")[title["pdf_page"] - 1]
    assert french.name.upper() in page.upper()
    assert {"name": french.name, "publisher": french.publisher, "origin": french.origin, "language": "fr"} in (
        registry_page()["collections"])
