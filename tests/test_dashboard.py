"""The dashboard's Data readiness page (ticket 16; the 16 design brief, section 10), offline.

The dashboard is defined in code (src/strata/dashboard, the spec's tenth single place) and deployed
with the bundle by one command. Its numbers come from the same measures as the app: the measure run
writes the page data_readiness_for builds into strata.ops.readiness_snapshot, and the dashboard's
own queries read that table and strata.gold. Here each query runs on the fixture database on the
day the fixture was measured, and its rows are compared with the tool's answer for that day.
"""

import datetime as dt
from pathlib import Path

import pytest

from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine
from strata.tools import registry
from strata.tools.data_readiness_for import text_of

ROOT = Path(__file__).resolve().parents[1]
DAY = dt.date(2026, 10, 23)  # the day the fixture's sources were recorded and measured
ANA = Viewer(email="ana.example@worldbank.org", token="token-for-ana-only")


@pytest.fixture(scope="module")
def engine(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        yield engine


@pytest.fixture(scope="module")
def page(engine):
    return registry.call("data_readiness_for", {"as_of": DAY.isoformat()}, registry.Context(engine=engine, viewer=ANA))


def snapshot(engine, part):
    result = engine.run("SELECT * FROM strata.ops.readiness_snapshot WHERE part = :part AND measured_on = :day "
                        "QUALIFY written_at = max(written_at) OVER () ORDER BY position", {"part": part, "day": DAY})
    return [dict(zip(result.columns, row)) for row in result.rows]


def test_the_fixture_s_snapshot_holds_the_app_s_headline_for_the_same_day(engine, page):
    [headline] = snapshot(engine, "headline")

    assert headline["text"] == page["headline"]["text"]


def test_the_snapshot_ranks_the_fixes_in_the_app_s_order_with_the_same_counts(engine, page):
    fixes = snapshot(engine, "fix")

    assert [(row["position"], row["text"], row["projects"]) for row in fixes] == [
        (fix["rank"], text_of(fix["sentence"]), fix["projects"]) for fix in page["fixes"]]


def test_the_snapshot_gives_each_source_the_app_s_status_and_link_counts(engine, page):
    sources = {row["position"]: row for row in snapshot(engine, "source") + snapshot(engine, "gap")}

    for position, row in enumerate(page["sources"], 1):
        stored = sources[position]
        if row["type"] == "gap":
            assert stored["status"] == "Gap"
            continue
        statuses = {cell.get("status") for cell in row["cells"].values()}
        assert stored["status"] == ("Partial" if "partial" in statuses else None), row["id"]
        linked = row["cells"]["linked"]
        if linked.get("row") is not None:
            measure = page["rows"][linked["row"]]
            assert (stored["count"], stored["denominator"]) == (measure["count"], measure["denominator"]), row["id"]


# ── The definition, and one deploy ────────────────────────────────────────

import json  # noqa: E402
import re  # noqa: E402

from strata import dashboard  # noqa: E402
from strata.lakehouse import bundle  # noqa: E402

DESIGN = (ROOT / "DESIGN.md").read_text()
TENTH_PLACE_ORDER = ["introduction", "measure_date", "headline", "award_rows", "source_rows", "links", "routes",
                     "freshness", "fixes", "notes"]


def lvdash() -> dict:
    return json.loads(dashboard.FILE.read_text())


def dataset_rows(engine, name):
    result = engine.run(dashboard.query(name), {dashboard.PARAMETER: DAY})
    return [dict(zip(result.columns, row)) for row in result.rows]


def test_the_dashboard_file_says_what_its_definition_in_code_says():
    assert dashboard.FILE.read_text() == dashboard.written(), "run: uv run --frozen python -m strata.dashboard --write"


def test_the_bundle_deploys_the_dashboard_file_with_each_viewer_s_own_credentials():
    declared = bundle.load().resources("dashboards")["strata"]

    assert (ROOT / "bundle" / declared["file_path"]).resolve() == dashboard.FILE
    assert declared["warehouse_id"] == "${var.warehouse_id}"
    assert declared["embed_credentials"] is False


def test_the_data_readiness_page_holds_the_brief_s_ten_tiles_in_order_on_a_six_column_grid():
    [page] = lvdash()["pages"]

    assert page["displayName"] == "Data readiness"
    assert [tile["widget"]["name"] for tile in page["layout"]] == TENTH_PLACE_ORDER
    for tile in page["layout"]:
        position = tile["position"]
        assert position["x"] + position["width"] <= 6, tile["widget"]["name"]


def test_every_chart_and_table_has_a_title_that_states_no_number_and_a_description():
    for tile in lvdash()["pages"][0]["layout"]:
        spec = tile["widget"].get("spec")
        if spec is None:
            continue  # a text tile
        frame = spec["frame"]
        assert frame["title"] and frame["description"], tile["widget"]["name"]
        assert not re.search(r"\d", frame["title"]), frame["title"]


def test_one_date_filter_sets_every_dataset_and_starts_at_today():
    board = lvdash()
    [date] = [tile for tile in board["pages"][0]["layout"] if tile["widget"]["name"] == "measure_date"]

    assert {query["query"]["datasetName"] for query in date["widget"]["queries"]} == {
        dataset["name"] for dataset in board["datasets"]}
    for dataset in board["datasets"]:
        [parameter] = dataset["parameters"]
        assert (parameter["keyword"], parameter["dataType"]) == ("measure_date", "DATE")
        assert ":measure_date" in "".join(dataset["queryLines"])


def test_the_charts_use_design_md_s_categorical_colors_in_order_with_the_text_variants_for_essential_marks():
    """DESIGN.md section 6: cat1, cat2, cat4 and cat9 fall below 3:1 on white, so bars use their text variants."""
    def row(name):
        return re.findall(r"`(#[0-9a-f]{6})`", re.search(rf"\| {name} \|([^\n]+)", DESIGN).group(1))

    categorical, variants = row("Categorical, in order"), row("Categorical text variants")
    expected = [variants[i] if i in (0, 1, 3, 8) else categorical[i] for i in range(9)]

    assert list(dashboard.COLORS) == expected
    used = set(re.findall(r"#[0-9a-fA-F]{6}", dashboard.FILE.read_text()))
    assert used <= set(expected)
    [awards] = [tile for tile in lvdash()["pages"][0]["layout"] if tile["widget"]["name"] == "award_rows"]
    mappings = awards["widget"]["spec"]["encodings"]["color"]["scale"]["mappings"]
    assert [mapping["color"] for mapping in mappings] == expected[:len(mappings)]


def test_every_dataset_runs_on_the_fixture_on_the_day_it_was_measured(engine):
    for name, _ in dashboard.DATASETS:
        assert dataset_rows(engine, name), name


def test_the_dashboard_s_headline_fixes_and_link_shares_are_the_app_s_for_the_same_day(engine, page):
    [headline] = dataset_rows(engine, "readiness_headline")
    assert (headline["measured_on"], headline["headline"]) == (DAY, page["headline"]["text"])

    fixes = dataset_rows(engine, "readiness_fixes")
    assert [(row["rank"], row["fix"], row["projects"]) for row in fixes] == [
        (fix["rank"], text_of(fix["sentence"]), fix["projects"]) for fix in page["fixes"]]

    shares = {row["link"]: row["share_percent"] for row in dataset_rows(engine, "readiness_links")}
    assert shares["Contract awards: carry a STEP reference"] == 88  # 528 of 603, as the app shows


def test_the_award_rows_per_fiscal_year_add_up_to_kenya_s_contracts(engine):
    """values.toml counts Kenya's 603 contracts from the recorded award files; the fixture records
    awards since fiscal 2020 for Kenya only."""
    import tomllib

    kenya = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["counts"]["kenya"]
    rows = dataset_rows(engine, "award_rows_by_year")

    assert sum(row["award_rows"] for row in rows if row["dataset"] == "Awards since FY2020") == kenya["contracts"]
    assert {row["dataset"] for row in rows} <= set(dashboard.AWARD_DATASETS)
    assert all(re.fullmatch(r"FY\d\d", row["fiscal_year_label"]) for row in rows)


def test_a_date_before_the_first_snapshot_shows_no_headline(engine):
    result = engine.run(dashboard.query("readiness_headline"), {dashboard.PARAMETER: DAY - dt.timedelta(days=1)})

    assert result.rows == ()
