"""The four single places this ticket adds (spec, "Ten single places"): the source registry, the
slice file, the model file and the thresholds file. Each loads through one function in
strata.config, and a file that does not follow its shape stops with a sentence that names the
file and the fix.

Expected values come from docs/PLAN.md sections 2 and 3 and the ticket, never from the files.
"""

import datetime as dt
import shutil
import tomllib
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

    # The four pilot countries stay; adding a country is one entry and keeps the gate green.
    pilot_countries = {("Kenya", "KE", "KEN"), ("Bangladesh", "BD", "BGD"), ("Vietnam", "VN", "VNM"),
                       ("Pakistan", "PK", "PAK")}
    assert pilot_countries <= {(country.name, country.iso2, country.iso3) for country in pilot.countries}
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
    assert pilot.planned_projects == 128  # docs/PLAN.md section 3


# The stress shelf (docs/PLAN.md section 3, and the 18 design brief, section 4.1): the P130164 PAD with its
# two-column risk annex, the longest PAD, a long Procurement Plan, a completion report in French and a
# document over the layout parser's limit, in that order. The hand count of the annex's risks is
# tests/ground_truth/values.toml's.
SHELF_TRUTH = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["stress_shelf"]


def test_the_stress_shelf_names_five_entries_each_with_a_kind_and_a_document_or_a_rule():
    shelf = config.load_slice().stress_shelf

    assert [item.kind for item in shelf] == ["scan_annex", "longest_pad", "large_plan", "other_language",
                                             "over_parser_limit"]
    assert len({item.key for item in shelf}) == 5
    annex = SHELF_TRUTH["pad_risk_annex"]
    pad = shelf[0]
    assert (pad.project_id, pad.document_id, pad.part) == ("P130164", annex["document_id"], "risk_annex")
    assert (pad.first_page, pad.last_page) == (annex["first_pdf_page"], annex["last_pdf_page"])
    assert (pad.expected_rows, pad.counted_on) == (annex["risks"], annex["counted_on"])
    assert (shelf[1].rule, shelf[1].document_type, shelf[1].document_id) == (
        "longest", "Project Appraisal Document", None)
    assert (shelf[2].project_id, shelf[2].document_id) == ("P161305", SHELF_TRUTH["long_plan"]["document_id"])
    assert (shelf[3].document_id, shelf[3].language) == (SHELF_TRUTH["french_report"]["document_id"], "fr")
    assert (shelf[4].rule, shelf[4].document_id) == ("over_parser_limit", None)


@pytest.mark.parametrize(("old", "new", "says"), [
    ('kind = "scan_annex"', 'kind = "a_hard_one"', r"stress_shelf\[1\]\.kind must be one of"),
    ('rule = "longest"', 'rule = "longest"\ndocument_id = "18381488"\nproject_id = "P130164"',
     r"stress_shelf\[2\] names a document_id and a rule"),
    ('expected_rows = ', 'not_expected_rows = ', r"stress_shelf\[1\] has keys I do not know: not_expected_rows"),
    ('part = "risk_annex"\n', '', r"stress_shelf\[1\]\.part is missing"),
    ('language = "fr"', 'language = "French"', r"stress_shelf\[4\]\.language must be a two-letter"),
])
def test_a_stress_shelf_entry_of_the_wrong_shape_is_refused_with_a_sentence(tmp_path, old, new, says):
    path = copy("slice.toml", tmp_path, old=old, new=new)

    with pytest.raises(ConfigError, match=says):
        config.load_slice(path)


def test_a_hand_count_needs_the_day_it_was_counted(tmp_path):
    path = copy("slice.toml", tmp_path, old="counted_on = ", new="# counted_on = ")

    with pytest.raises(ConfigError, match=r"stress_shelf\[1\]\.counted_on.*the day a person counted"):
        config.load_slice(path)


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

# docs/PLAN.md section 3's structured sources: each Finances One dataset with its dataset and
# resource ids, and the search and indicator APIs.
FINANCES_ONE = {
    "awards": ("DS00005", "RS00005"),
    "awards_fy2001_2016": ("DS01004", "RS00934"),
    "ieg_ratings": ("DS00053", "RS00055"),
    "ida_credits": ("DS00001", "RS00001"),
    "ibrd_loans": ("DS00047", "RS00047"),
    "ida_credit_history": ("DS00976", "RS00976"),
    "ibrd_loan_history": ("DS00975", "RS00975"),
}


def test_the_source_registry_holds_every_structured_source_in_plan_section_3():
    sources = config.load_sources()

    assert {key: (sources[key].dataset_id, sources[key].resource_id) for key in FINANCES_ONE} == FINANCES_ONE
    assert sources["notices"].endpoint.startswith("https://search.worldbank.org/api/")
    assert sources["projects"].endpoint.startswith("https://search.worldbank.org/api/v3/projects")
    assert {sources["cpia"].api, sources["wgi"].api} == {"indicators"}
    assert all(source.license == "CC BY 4.0" for source in sources.values())


def test_the_frozen_awards_dataset_says_so_and_the_cpia_and_wgi_sources_name_their_indicators():
    """PLAN.md section 3: the FY2001 to FY2016 awards have been frozen since March 2022; CPIA is the
    IQ.CPA codes (21 on the Indicators API on October 23, 2026) and WGI the GOV_WGI codes, whose six
    estimates are its six dimensions. The old GE.EST code no longer works."""
    sources = config.load_sources()

    assert sources["awards_fy2001_2016"].cadence == "frozen"
    assert len(sources["cpia"].indicators) == 21
    assert all(code.startswith("IQ.CPA.") for code in sources["cpia"].indicators)
    assert sorted(sources["wgi"].indicators) == ["GOV_WGI_CC.EST", "GOV_WGI_GE.EST", "GOV_WGI_PV.EST",
                                                 "GOV_WGI_RL.EST", "GOV_WGI_RQ.EST", "GOV_WGI_VA.EST"]


def test_the_nightly_job_fetches_every_structured_source_page_by_page_and_the_plan_reader_fetches_the_documents():
    sources = config.load_sources()

    assert {key for key, source in sources.items() if source.paged} == set(FINANCES_ONE) | {
        "notices", "projects", "cpia", "wgi"}
    assert not sources["documents"].paged


def test_structured_sources_cover_every_country_and_the_monthly_history_covers_the_slice():
    """PLAN.md section 3: structured data for every country; the monthly loan history for the slice only."""
    sources = config.load_sources()
    slice_countries = config.load_slice().countries
    histories = {"ida_credit_history", "ibrd_loan_history"}

    for key, source in sources.items():
        if not source.paged:
            continue
        if key in histories:
            assert source.countries == slice_countries, key
        else:
            assert source.countries == (), key  # one request series with no country filter


def test_the_source_registry_loads_and_names_the_documents_api_that_plan_versions_come_from():
    documents = config.load_sources()["documents"]

    assert documents.endpoint == "https://search.worldbank.org/api/v3/wds"
    assert documents.stratum == "How"


def test_each_source_leaves_out_the_same_keys_as_the_recording_of_its_fixture_dataset():
    """config/sources.toml's ignore_keys keep a key out of a page's content hash, and
    data/fixture/sources.toml's keep it out of the recording's diff. They name the same keys, so
    the two lists cannot drift apart."""
    datasets = tomllib.loads((ROOT / "data" / "fixture" / "sources.toml").read_text())["datasets"]

    for source in (source for source in config.load_sources().values() if source.paged):
        recorded = tuple(datasets[source.fixture_dataset].get("ignore_keys", ()))
        assert tuple(source.ignore_keys) == recorded, source.key


AWARDS_COPY = """
[sources.awards_copy]
dataset_name = "Contract awards since FY2020"
endpoint = "https://datacatalogapi.worldbank.org/dexapps/fone/api/apiservice?datasetId=DS00005&resourceId=RS00005&type=json"
dataset_id = "DS00005"
resource_id = "RS00005"
api = "finances_one"
records = "data"
scope = "every country"
page_size = 1000
watermark_field = "contract_signing_date"
ignore_keys = ["as_of_date"]
fixture_dataset = "awards"
cadence = "daily"
license = "CC BY 4.0"
silver_transform = "awards"
stratum = "What"

[[sources.awards_copy.known_gaps]]
id = "copy_gap"
label = "Contract awards"
noun = "contract awards"
first_fiscal_year = 2017
last_fiscal_year = 2019
note = "No World Bank dataset publishes contract awards for these years."
"""


def test_a_source_is_one_entry_in_the_registry(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS_COPY)

    awards = config.load_sources(path)["awards_copy"]

    assert awards.dataset_id == "DS00005"
    assert awards.cadence == "daily"
    assert (awards.api, awards.page_size, awards.ignore_keys) == ("finances_one", 1000, ("as_of_date",))
    assert [(gap.first_fiscal_year, gap.last_fiscal_year) for gap in awards.known_gaps] == [(2017, 2019)]


# ── What the Data readiness page reads from the registry (ticket 16) ─────

def test_every_source_says_how_its_data_readiness_shows_and_the_documents_show_as_plans_and_reports():
    """The 16 brief, section 5.1: one row per source, in the registry's order, What before How
    before Why. The documents source holds two readers' measures, so it shows as two rows, and a third
    for the notices' text the passage reader reads (ticket 18), which arrives as text."""
    sources = config.load_sources()

    assert all(source.readiness for source in sources.values())
    awards = sources["awards"].readiness[0]
    assert (awards.label, awards.linked.measure, awards.fresh.measure) == (
        "Contract awards", "linked_step_reference", "fresh_fetched")
    assert awards.read_well is None  # STEP publishes awards as a table, so nothing needs reading
    assert [(row.id, row.stratum) for row in sources["documents"].readiness] == [
        ("plans", "How"), ("reports", "Why"), ("notice_text", "What")]
    assert sources["documents"].readiness[2].published_as == "text"
    ids = [row.id for source in sources.values() for row in source.readiness]
    assert len(ids) == len(set(ids))


def test_the_registry_declares_the_fiscal_2017_to_2019_awards_as_a_known_gap():
    """The ticket: no dataset publishes contract awards for fiscal 2017 to 2019 (PLAN.md section 3)."""
    gaps = config.load_sources()["awards"].known_gaps

    assert [(gap.first_fiscal_year, gap.last_fiscal_year) for gap in gaps] == [(2017, 2019)]
    assert gaps[0].note.startswith("No World Bank dataset publishes contract awards for these years.")


def test_each_dataset_names_its_data_source_and_the_day_its_name_was_checked_against_the_catalog():
    """PLAN.md section 18 asks for the exact dataset names on the attribution page."""
    sources = config.load_sources()

    datasets = {key: source.attribution for key, source in sources.items() if source.attribution}
    assert set(datasets) == set(sources) - {"documents"}
    assert datasets["awards"].data_source == "Systematic Tracking of Exchanges in Procurement (STEP)"
    assert all(isinstance(found.name_checked, dt.date) for found in datasets.values())
    assert all(found.catalog_url.startswith("https://") for found in datasets.values())
    assert [collection.name for collection in sources["documents"].collections][0] == "Procurement Plans"


def test_a_data_readiness_column_with_a_key_the_registry_does_not_know_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path, 'linked = { measure = "linked_step_reference"',
                'linked = { mesure = "linked_step_reference"')

    with pytest.raises(ConfigError, match=r"sources\.awards\.readiness\[1\]\.linked has keys I do not know: mesure"):
        config.load_sources(path)


def test_a_fix_names_the_measure_whose_numbers_fill_its_sentence(tmp_path):
    fixes = config.load_sources()["awards"].fixes

    assert {fix.measure for fix in fixes} >= {"linked_step_reference"}
    assert all("{" in fix.sentence for fix in fixes)


def test_a_fix_on_a_measure_no_column_shows_must_say_what_it_counts(tmp_path):
    """Its numbers' tooltips need a noun (design review B1), and no column gives one."""
    path = copy("sources.toml", tmp_path, 'noun = "contracts in local currency"\n', "")

    with pytest.raises(ConfigError, match=r"sources\.awards\.fixes\[2\]\.noun must say what its measure counts"):
        config.load_sources(path)


def test_a_fix_on_a_measure_no_column_shows_must_name_the_table_it_counts(tmp_path):
    """Review r7: every number's window names the table it was counted in, and no column gives one."""
    path = copy("sources.toml", tmp_path, 'noun = "contracts in local currency"\ncounted_in = "strata.gold.contract"\n',
                'noun = "contracts in local currency"\n')

    with pytest.raises(ConfigError, match=r"sources\.awards\.fixes\[2\]\.counted_in must name the table"):
        config.load_sources(path)


def test_a_fix_s_projects_measure_must_name_the_table_it_counts(tmp_path):
    path = copy("sources.toml", tmp_path, 'projects_counted_in = "strata.gold.contract"\nsentence = "Find', 'sentence = "Find')

    with pytest.raises(ConfigError, match=r"sources\.awards\.fixes\[1\]\.projects_counted_in must name the table"):
        config.load_sources(path)


def test_a_kind_s_ready_for_names_its_table_when_no_column_of_its_row_shows_the_measure():
    """Review r7 B1: the document search's Ready for counts passages, which no column of the reports
    row shows, so the tool registry names their table. The plan check's is the plans row's Read well
    measure, whose table the source registry already names once."""
    tools = config.load_tools()

    assert tools["search_passages"].readiness.ready_for_counted_in == "strata.gold.passage"
    assert tools["check_plan"].readiness.ready_for_counted_in is None


def _texts(value):
    """Every string in a loaded TOML value."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _texts(item)
    elif isinstance(value, list):
        for item in value:
            yield from _texts(item)


def _split_field_names(path):
    """The registry's words that write STEP's "Reference No." with a space a narrow cell may break."""
    return [text for text in _texts(tomllib.loads(path.read_text())) if "Reference No." in text]


def test_a_step_field_name_in_the_registry_keeps_its_no_break_space(tmp_path):
    """Review r5 P3: "Activity Reference No." keeps a no-break space, so the Sources table at 1024 px
    never leaves "No." alone on a line, as the registry's comment says."""
    assert _split_field_names(ROOT / "config" / "sources.toml") == []

    typed = copy("sources.toml", tmp_path, 'lack = "an Activity Reference\\u00A0No."', 'lack = "an Activity Reference No."')
    assert _split_field_names(typed), "the check finds a plain space"


def test_a_country_added_to_the_slice_joins_the_monthly_history_fetch(tmp_path):
    slice_file = copy("slice.toml", tmp_path)
    slice_file.write_text(slice_file.read_text() + '\n[[countries]]\nname = "Nepal"\niso2 = "NP"\niso3 = "NPL"\n')

    sources = config.load_sources(slice_path=slice_file)

    assert [country.iso2 for country in sources["ida_credit_history"].countries][-1] == "NP"
    assert sources["notices"].countries == ()


def test_a_source_fetched_for_the_slice_countries_needs_its_country_filter(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS_COPY.replace('scope = "every country"', 'scope = "slice countries"'))

    with pytest.raises(ConfigError, match=r"awards_copy\.country_filter"):
        config.load_sources(path)


def test_a_source_without_its_watermark_field_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS_COPY.replace('watermark_field = "contract_signing_date"\n', ""))

    with pytest.raises(ConfigError, match=r"sources\.toml.*awards_copy.*watermark_field"):
        config.load_sources(path)


def test_a_source_with_a_misspelled_key_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS_COPY.replace("cadence =", "cadance ="))

    with pytest.raises(ConfigError, match="cadance"):
        config.load_sources(path)


def test_a_source_that_names_some_of_the_paging_keys_but_not_all_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS_COPY.replace('records = "data"\n', ""))

    with pytest.raises(ConfigError, match=r"awards_copy.*records.*api, records, page_size, fixture_dataset, scope"):
        config.load_sources(path)


def test_a_source_that_pages_an_api_strata_does_not_know_is_refused(tmp_path):
    path = copy("sources.toml", tmp_path)
    path.write_text(path.read_text() + AWARDS_COPY.replace('api = "finances_one"', 'api = "socrata"'))

    with pytest.raises(ConfigError, match=r"awards_copy\.api.*finances_one, search, indicators"):
        config.load_sources(path)


# ── The model file ───────────────────────────────────────────────────────

def test_the_model_file_names_a_deployment_for_each_role():
    """The file's shape, not its names: swapping a model is one line and keeps the gate green.

    docs/PLAN.md section 2 gives the roles: the agent, drafting and hard questions, bulk extraction
    and embeddings. The caps probe checks the names themselves against Azure.
    """
    models = config.load_models()

    assert list(models) == list(config.ROLES) == ["agent", "draft", "batch", "embed"]
    assert all(model.deployment.strip() for model in models.values())
    assert isinstance(models["embed"].dimensions, int) and models["embed"].dimensions > 0


def test_swapping_a_model_is_one_line(tmp_path):
    current = config.load_models()["agent"].deployment
    path = copy("models.toml", tmp_path, old=f'deployment = "{current}"', new='deployment = "swapped-model"')

    assert config.load_models(path)["agent"].deployment == "swapped-model"


def test_the_model_file_names_the_layout_parser_and_strata_has_its_adapter():
    """The ticket's layout parser is ai_parse_document, or Content Understanding if day-one test 3
    failed, so a swap is one line in the model file."""
    from strata.reader import layout

    assert config.load_layout_parser() == "ai_parse_document"
    assert config.load_layout_parser() in layout.PARSERS


def test_swapping_the_layout_parser_is_one_line(tmp_path):
    path = copy("models.toml", tmp_path, old='parser = "ai_parse_document"', new='parser = "content_understanding"')

    assert config.load_layout_parser(path) == "content_understanding"
    assert list(config.load_models(path)) == list(config.ROLES)


def test_a_model_file_missing_a_role_is_refused(tmp_path):
    path = copy("models.toml", tmp_path, old="[roles.batch]", new="[roles.bulk]")

    with pytest.raises(ConfigError, match=r"models\.toml.*batch"):
        config.load_models(path)


def test_an_embedding_role_without_its_dimensions_is_refused(tmp_path):
    """The AI Search probe and the passage index need the size, so the loader names the gap."""
    size = config.load_models()["embed"].dimensions
    path = copy("models.toml", tmp_path, old=f"dimensions = {size}\n", new="")

    with pytest.raises(ConfigError, match=r"models\.toml.*roles\.embed\.dimensions is missing"):
        config.load_models(path)


def test_only_the_model_file_names_a_deployment_or_the_embedding_size():
    """Swapping a model is one line (spec, "Ten single places"), so no other file repeats what it holds.

    The wizard and the probes from ticket 03 read the names through load_models(), and dayone.toml
    keeps only each role's cap.
    """
    names = [model.deployment for model in config.load_models().values()]
    for path in (".env.example", "ops/dayone/dayone.toml", "ops/wizard/strata-setup.sh"):
        text = (ROOT / path).read_text()
        assert "STRATA_MODEL_" not in text, path
        assert [name for name in names if name in text] == [], path

    caps = tomllib.loads((ROOT / "ops" / "dayone" / "dayone.toml").read_text())["caps"]["deployments"]
    assert list(caps) == list(config.ROLES)
    assert [key for cap in caps.values() for key in cap if key in ("env_key", "deployment", "dimensions")] == []


# ── The thresholds file ──────────────────────────────────────────────────

def test_the_thresholds_file_loads_and_a_missing_threshold_says_where_to_add_it():
    thresholds = config.load_thresholds()

    # A name no ticket adds, so the test holds as the file grows.
    with pytest.raises(ConfigError, match=r"plan_check\.not_a_threshold.*config/thresholds\.toml"):
        thresholds.value("plan_check.not_a_threshold")


def test_a_threshold_added_to_the_file_is_read(tmp_path):
    path = copy("thresholds.toml", tmp_path, old="[signals]", new="[signals]\nexample_threshold = 30")

    assert config.load_thresholds(path).value("signals.example_threshold") == 30
