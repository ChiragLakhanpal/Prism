"""The dashboard's Data readiness page (ticket 16; the 16 design brief, section 10), offline.

The dashboard is defined in code (src/strata/dashboard, the spec's tenth single place) and deployed
with the bundle by one command. Its numbers come from the same measures as the app: the measure run
writes the page data_readiness_for builds into strata.ops.readiness_snapshot, with each charted
source's rows per fiscal year counted as its Coverage cell counts them, and the dashboard's own
queries read only that table. Here each query runs on the fixture database on the day the fixture
was measured, and its rows are compared with the tool's answer for that day.
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


@pytest.fixture
def empty_catalog_copy(tmp_path):
    """Every table and no rows, as a first deploy leaves the catalog."""
    from strata.lakehouse import catalog

    path = tmp_path / "strata.duckdb"
    with DuckDBEngine.open(path) as engine:
        catalog.build(engine)
    return path


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


def test_the_snapshot_s_pages_read_well_by_route_are_the_tool_s_route_rows(engine, page):
    """Review B3: the routes' shares come from data_readiness_for's rows, never a sum of the
    snapshot's own."""
    routes = snapshot(engine, "route")

    assert [(row["label"], row["count"], row["denominator"], row["share_percent"]) for row in routes] == [
        (route["label"], page["rows"][route["row"]]["count"], page["rows"][route["row"]]["denominator"],
         page["rows"][route["row"]]["share_percent"]) for route in page["routes"]]
    assert routes


# ── The definition, and one deploy ────────────────────────────────────────

import json  # noqa: E402
import re  # noqa: E402
import tomllib  # noqa: E402

from strata import dashboard  # noqa: E402
from strata.lakehouse import bundle  # noqa: E402

DESIGN = (ROOT / "DESIGN.md").read_text()
TENTH_PLACE_ORDER = ["introduction", "measure_date", "headline", "award_rows", "source_rows", "links", "routes",
                     "freshness", "fixes", "notes"]


KENYA = tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["counts"]["kenya"]


def lvdash() -> dict:
    return json.loads(dashboard.FILE.read_text())


def dataset_rows(engine, name, day=DAY):
    result = engine.run(dashboard.query(name), {dashboard.PARAMETER: day})
    return [dict(zip(result.columns, row)) for row in result.rows]


def test_the_dashboard_file_says_what_its_definition_in_code_says():
    assert dashboard.FILE.read_text() == dashboard.written(), "run: uv run --frozen python -m strata.dashboard --write"


def test_the_bundle_deploys_the_dashboard_file_with_each_viewer_s_own_credentials():
    declared = bundle.load().resources("dashboards")["strata_dashboard"]

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
        [date] = dataset["parameters"]
        assert (date["keyword"], date["dataType"]) == ("measure_date", "DATE")
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
    """The routes chart charts a route only from the thresholds file's fewest rows for a percentage
    (DESIGN.md section 7, rule 15): the fixture's plan routes read 24 and 27 pages, so they have no bar,
    and its report routes read hundreds (ticket 18), so they do."""
    for name in dashboard.DATASETS:
        assert dataset_rows(engine, name), name
    assert [row["route"] for row in dataset_rows(engine, "readiness_routes")] == [
        "Report pages, published text", "Report pages, layout parser"]


def test_a_route_or_a_link_is_charted_only_from_enough_rows_for_a_percentage(empty_catalog_copy):
    """Review P11: a share the tool leaves empty draws no empty bar."""
    from strata.dashboard import snapshot as written
    at = dt.datetime(2026, 10, 23, 9, tzinfo=dt.UTC)
    result = {"headline": None, "sources": [], "fixes": [],
              "rows": [{"count": 60, "denominator": 64, "share_percent": 94}, {"count": 15, "denominator": 15,
                                                                               "share_percent": None}],
              "routes": [{"label": "Plan pages, published text", "row": 0}, {"label": "Plan pages, layout parser", "row": 1}]}
    with DuckDBEngine.open(empty_catalog_copy) as engine:
        engine.insert_rows("strata.ops.readiness_snapshot", written.COLUMNS, written.rows(result, "run-1", DAY, at))
        assert [(row["route"], row["share_percent"]) for row in dataset_rows(engine, "readiness_routes")] == [
            ("Plan pages, published text", 94)]


def test_the_dashboard_s_headline_fixes_and_link_shares_are_the_app_s_for_the_same_day(engine, page):
    [headline] = dataset_rows(engine, "readiness_headline")
    assert (headline["measured_on"], headline["headline"]) == (DAY, page["headline"]["text"])

    fixes = dataset_rows(engine, "readiness_fixes")
    assert [(row["rank"], row["fix"], row["projects"]) for row in fixes] == [
        (fix["rank"], text_of(fix["sentence"]), fix["projects"]) for fix in page["fixes"]]

    shares = {row["link"]: row["share_percent"] for row in dataset_rows(engine, "readiness_links")}
    since_2020 = dashboard.year_labels()["awards"]
    assert shares[f"{since_2020}: contracts carry a STEP reference"] == 88  # 528 of 603, as the app shows


def test_the_award_rows_per_fiscal_year_add_up_to_kenya_s_award_rows(engine):
    """values.toml counts Kenya's 632 award rows from the recorded award files (one per joint-venture
    member, as the Coverage column counts them); the fixture records awards since fiscal 2020 for
    Kenya only. Review r3 B1: the tile once counted gold's 603 contracts."""
    kenya = KENYA
    rows = dataset_rows(engine, "award_rows_by_year")
    since_2020 = dashboard.year_labels()["awards"]

    assert sum(row["award_rows"] for row in rows if row["dataset"] == since_2020) == kenya["award_rows"]
    assert {row["dataset"] for row in rows} == set(dashboard.award_datasets())
    assert all(re.fullmatch(r"FY\d\d", row["fiscal_year_label"]) for row in rows)


def coverage_numbers(page) -> dict[str, int]:
    """Each source's Coverage number as the app shows it, by source key."""
    out = {}
    for row in page["sources"]:
        cell = row["cells"]["coverage"] if row["type"] == "measured" else {}
        if cell.get("row") is not None:
            out.setdefault(row["source_key"], page["rows"][cell["row"]]["count"])
    return out


def test_each_source_s_rows_per_fiscal_year_add_up_to_its_coverage_number_in_the_app(engine, page):
    """Review r3 B1: the dashboard says its tiles are the app's measures, so tiles 4 and 5 count each
    source's rows as its Coverage cell counts them, and a source's years add up to that number on the
    same date. The award notices for fiscal 2017 to 2019 are a Gap row in the app, with no count."""
    labels = dashboard.year_labels()
    totals: dict[str, int] = {}
    for row in dataset_rows(engine, "rows_by_year"):
        totals[row["source"]] = totals.get(row["source"], 0) + row["source_rows"]
    coverage = coverage_numbers(page)

    compared = {key: totals[label] for key, label in labels.items() if key in coverage}
    assert compared == {key: coverage[key] for key in compared}
    assert set(compared) == {"awards", "awards_fy2001_2016", "ieg_ratings", "notices", "projects"}
    assert compared["awards"] == KENYA["award_rows"]
    # Ticket 18: after the sources, the documents read of each type, by fiscal year of disclosure, add up
    # to the documents the reports' Coverage cell counts.
    documents = {label: total for label, total in totals.items() if label.endswith(", documents read")}
    assert set(totals) == set(labels.values()) | set(documents)
    assert "Project Appraisal Document, documents read" in documents
    [reports] = [row for row in page["sources"] if row["id"] == "reports"]
    assert sum(documents.values()) == page["rows"][reports["cells"]["coverage"]["row"]]["count"]


def test_a_date_before_the_first_snapshot_shows_no_headline(engine):
    assert dataset_rows(engine, "readiness_headline", DAY - dt.timedelta(days=1)) == []


def test_the_table_of_freshness_and_links_keeps_the_pages_each_route_read_well(engine):
    """Design r3 N9: tile 7 charts a route only from enough pages for a percentage, so tile 8, its
    table, lists every route's counts, as the app shows them."""
    rows = dataset_rows(engine, "readiness_sources")

    assert {row["source"]: row["read_well"] for row in rows if row["read_well"]} == {
        "Plan pages, published text": "24 of 24", "Plan pages, layout parser": "27 of 27",
        "Report pages, published text": "528 of 528", "Report pages, layout parser": "97 of 122"}


def test_the_table_of_freshness_and_links_names_each_awards_dataset_as_the_charts_do(engine):
    """Design r4 P7: tiles 6 and 8 name the two awards datasets with tiles 4 and 5's labels, and tile 8
    writes the fiscal 2017 to 2019 Gap's years as tables write years, so no row has two names on one page."""
    names = [row["source"] for row in dataset_rows(engine, "readiness_sources")]
    labels = dashboard.year_labels()

    assert labels["awards"] in names and labels["awards_fy2001_2016"] in names
    assert "Contract awards, FY2017–19" in names
    assert not [name for name in names if "fiscal" in name]
    # Review r5 P1: tile 6's bars name the two datasets the same way.
    links = [row["link"] for row in dataset_rows(engine, "readiness_links")]
    for key in ("awards", "awards_fy2001_2016"):
        assert [link for link in links if link.startswith(f"{labels[key]}: ")], (key, links)
