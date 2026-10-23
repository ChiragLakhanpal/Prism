"""The four single places this ticket adds (spec, "Ten single places"): the source registry, the
slice file, the model file and the thresholds file. Each loads through one function in
strata.config, and a file that does not follow its shape stops with a sentence that names the
file and the fix.

Expected values come from docs/PLAN.md sections 2 and 3 and the ticket, never from the files.
"""

import datetime as dt
import shutil
from pathlib import Path

import pytest

from strata import config
from strata.config import ConfigError

ROOT = Path(__file__).resolve().parents[1]


def copy(name, tmp_path, old=None, new=None):
    """A copy of a config file, with one piece of text replaced."""
    target = tmp_path / name
    shutil.copy(ROOT / "config" / name, target)
    if old is not None:
        text = target.read_text()
        assert old in text, f"{old!r} is not in config/{name}"
        target.write_text(text.replace(old, new, 1))
    return target


# ── The slice file ───────────────────────────────────────────────────────

def test_the_slice_file_names_the_pilot_countries_sectors_and_fiscal_years():
    pilot = config.load_slice()

    assert [country.name for country in pilot.countries] == ["Kenya", "Bangladesh", "Vietnam", "Pakistan"]
    assert [(country.iso2, country.iso3) for country in pilot.countries] == [
        ("KE", "KEN"), ("BD", "BGD"), ("VN", "VNM"), ("PK", "PAK")]
    assert pilot.sectors == ("water", "transport")
    assert (pilot.first_fiscal_year, pilot.last_fiscal_year) == (2012, 2025)
    assert list(pilot.fiscal_years) == list(range(2012, 2026))


def test_the_slice_file_names_the_showcase_project_and_the_demo_plan():
    pilot = config.load_slice()

    assert pilot.showcase.project_id == "P130164"
    assert pilot.demo_plan.project_id == "P156634"
    assert pilot.demo_plan.implementing_agency == "Northern Water Works Development Agency"
    assert pilot.demo_plan.agency_short_name == "NWWDA"
    assert pilot.demo_plan.plan_date == dt.date(2026, 10, 9)
    assert ("P130164", "PAD") in [(item.project_id, item.document_type) for item in pilot.stress_shelf]


def test_adding_a_country_to_the_slice_is_one_entry(tmp_path):
    path = copy("slice.toml", tmp_path)
    path.write_text(path.read_text() + '\n[[countries]]\nname = "Nepal"\niso2 = "NP"\niso3 = "NPL"\n')

    assert config.load_slice(path).countries[-1].name == "Nepal"


def test_a_slice_file_with_a_malformed_project_id_says_which_one(tmp_path):
    path = copy("slice.toml", tmp_path, old='"P130164"', new='"130164"')

    with pytest.raises(ConfigError, match=r"slice\.toml.*showcase\.project_id.*P followed by six digits"):
        config.load_slice(path)


def test_a_slice_file_whose_years_run_backwards_is_refused(tmp_path):
    path = copy("slice.toml", tmp_path, old="last_fiscal_year = 2025", new="last_fiscal_year = 2011")

    with pytest.raises(ConfigError, match="first_fiscal_year"):
        config.load_slice(path)


# ── The source registry ──────────────────────────────────────────────────

def test_the_source_registry_loads_with_no_sources_until_the_first_is_added():
    assert config.load_sources() == {}


AWARDS = """
[sources.awards]
dataset_name = "Contract awards since FY2020"
endpoint = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice"
dataset_id = "DS00005"
resource_id = "RS00005"
watermark_field = "as_of_date"
cadence = "daily"
license = "CC BY 4.0"
silver_transform = "silver/awards.sql"
stratum = "What"
known_gaps = ["Awards for FY2017 to FY2019 are in neither dataset."]
"""


def test_a_source_is_one_entry_in_the_registry(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS)

    awards = config.load_sources(path)["awards"]

    assert awards.dataset_id == "DS00005"
    assert awards.cadence == "daily"
    assert awards.known_gaps == ("Awards for FY2017 to FY2019 are in neither dataset.",)


def test_a_source_without_its_watermark_field_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS.replace('watermark_field = "as_of_date"\n', ""))

    with pytest.raises(ConfigError, match=r"sources\.toml.*awards.*watermark_field"):
        config.load_sources(path)


def test_a_source_with_a_misspelled_key_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS.replace("cadence =", "cadance ="))

    with pytest.raises(ConfigError, match="cadance"):
        config.load_sources(path)


# ── The model file ───────────────────────────────────────────────────────

def test_the_model_file_names_the_deployment_for_each_role():
    models = config.load_models()

    # docs/PLAN.md section 2: the agent, drafting and hard questions, bulk extraction, embeddings.
    assert {role: model.deployment for role, model in models.items()} == {
        "agent": "gpt-5.4-mini",
        "draft": "gpt-5.4",
        "batch": "gpt-5.4-nano",
        "embed": "text-embedding-3-large",
    }
    assert models["embed"].dimensions == 1024


def test_swapping_a_model_is_one_line(tmp_path):
    path = copy("models.toml", tmp_path, old='deployment = "gpt-5.4-mini"', new='deployment = "gpt-5.5-mini"')

    assert config.load_models(path)["agent"].deployment == "gpt-5.5-mini"


def test_a_model_file_missing_a_role_is_refused(tmp_path):
    path = copy("models.toml", tmp_path, old="[roles.batch]", new="[roles.bulk]")

    with pytest.raises(ConfigError, match=r"models\.toml.*batch"):
        config.load_models(path)


def test_the_model_file_and_env_example_name_the_same_deployments():
    """The wizard from ticket 03 writes .env.example's defaults, so the two must not drift apart."""
    example = dict(line.split("=", 1) for line in (ROOT / ".env.example").read_text().splitlines()
                   if line.startswith("STRATA_MODEL_"))
    models = config.load_models()

    assert {f"STRATA_MODEL_{role.upper()}": model.deployment for role, model in models.items()} == example


# ── The thresholds file ──────────────────────────────────────────────────

def test_the_thresholds_file_loads_and_a_missing_threshold_says_where_to_add_it():
    thresholds = config.load_thresholds()

    with pytest.raises(ConfigError, match=r"plan_check\.days_before_closing.*config/thresholds\.toml"):
        thresholds.value("plan_check.days_before_closing")


def test_a_threshold_added_to_the_file_is_read(tmp_path):
    path = copy("thresholds.toml", tmp_path, old="[plan_check]", new="[plan_check]\ndays_before_closing = 30")

    assert config.load_thresholds(path).value("plan_check.days_before_closing") == 30
