"""The dashboard "Prism operations" as code (ticket 45; the 45 design brief): three pages deployed by the bundle,
each tile's number from its defining query, one entry to add or remove a tile, and DESIGN.md section 6's rules.

The deploy itself is a workspace step (docs/workspace-catchup.md). Here the dashboard files the bundle deploys are
checked against the definition (strata.dashboard.definition), the KPI registry (config/kpis.toml) and the copy
file, line by line where AI/BI's behaviour can't be seen offline.
"""

import json
import re
import tomllib
from dataclasses import replace
from pathlib import Path

import pytest

from strata import dashboard
from strata.config import load_kpis
from strata.dashboard import definition, render, tiles, wording
from strata.lakehouse import bundle

ROOT = Path(__file__).resolve().parents[1]


def board(path=dashboard.FILE) -> dict:
    return json.loads(path.read_text())


def widgets(page) -> dict:
    return {tile["widget"]["name"]: tile for tile in page["layout"]}


def frame(tile) -> dict:
    return tile["widget"].get("spec", {}).get("frame", {})


# ── Three pages, from code, by the bundle's one deploy ───────────────────

def test_the_bundle_deploys_strata_operations_and_its_test_copy_from_the_files_the_definition_writes():
    declared = bundle.load().resources("dashboards")

    assert declared["strata_dashboard"]["display_name"] == wording.at("dash.name") == "Prism operations"
    assert declared["strata_dashboard_test"]["display_name"] == wording.at("dash.testName")
    assert (ROOT / "bundle" / declared["strata_dashboard_test"]["file_path"]).resolve() == dashboard.TEST_FILE
    assert dashboard.FILE.read_text() == dashboard.written()
    assert dashboard.TEST_FILE.read_text() == dashboard.written(test=True), (
        "run: uv run --frozen python -m strata.dashboard --write")


def test_the_dashboard_has_three_pages_in_the_brief_s_order():
    assert [page["displayName"] for page in board()["pages"]] == [
        "Data readiness", "Governance", "AI quality and adoption"]


def test_every_tile_reads_a_dataset_whose_query_in_the_file_is_its_defining_query():
    """A counter's dataset is its KPI's one defining query, and every table and chart reads the query the
    definition names for it, as the gate runs it on DuckDB (tests/test_dashboard_kpis.py)."""
    deployed = {dataset["name"]: "".join(dataset["queryLines"]) for dataset in board()["datasets"]}
    for page in definition.PAGES:
        for tile in page.tiles:
            for name in render.dataset_of(tile):
                assert deployed[name].strip() == render.deployed(render.query(name)), name
                if isinstance(tile, tiles.Counter):
                    kpi = load_kpis()[tile.kpi]
                    assert name == f"kpi_{kpi.id}"
                    assert render.source(name) == (ROOT / "src/strata/dashboard/sql/kpi" / f"{kpi.query}.sql").read_text()


def test_every_dashboard_query_reads_only_strata_ops_and_strata_gold():
    """The Data readiness page reads strata.ops' snapshot; who queried what reads the workspace's own lineage table;
    lineage and one KPI name a silver table only as text they show, never one they read."""
    for dataset in board()["datasets"]:
        sql = "".join(dataset["queryLines"])
        read = set(re.findall(r"\b(?:FROM|JOIN)\s+([a-z_]+\.[a-z_]+\.[a-z_]+)", sql))
        assert read, dataset["name"]
        assert {name.split(".")[1] for name in read if name.startswith("strata.")} <= {"ops", "gold"}, dataset["name"]
        assert {name for name in read if not name.startswith("strata.")} <= {"system.access.table_lineage"}


def test_each_counter_shows_its_kpi_s_display_string_with_no_target_delta_or_arrow():
    for page in board()["pages"]:
        for tile in page["layout"]:
            spec = tile["widget"].get("spec", {})
            if spec.get("widgetType") != "counter":
                continue
            assert set(spec["encodings"]) == {"value"}, tile["widget"]["name"]
            assert spec["encodings"]["value"]["fieldName"] == "display"
            kpi = load_kpis()[tile["widget"]["name"]]
            assert frame(tile)["title"] == wording.at(kpi.copy_keys[0])
            assert frame(tile)["description"] == wording.at(kpi.copy_keys[1])


def test_governance_and_ai_quality_hold_the_brief_s_counters_in_order():
    pages = board()["pages"]
    counters = [[tile["widget"]["name"] for tile in page["layout"]
                 if tile["widget"].get("spec", {}).get("widgetType") == "counter"] for page in pages]

    assert counters == [[], ["checks_failed", "azure_spend", "contacts_left"],
                        ["benchmark_passed", "sentences_removed", "answers_held_back", "weekly_users",
                         "drafts_exported", "plan_rows_offered"]]


def test_governance_ends_on_lineage_with_its_run_id_filter_before_its_tables():
    names = [tile["widget"]["name"] for tile in board()["pages"][1]["layout"]]

    assert names[-7:] == ["lineage_section", "run_id", "answer_run", "tool_calls", "tables_read", "recent_runs",
                          "governance_notes"]
    [run_id] = [tile for tile in board()["pages"][1]["layout"] if tile["widget"]["name"] == "run_id"]
    assert {query["query"]["datasetName"] for query in run_id["widget"]["queries"]} == {
        "lineage_run", "lineage_calls", "lineage_reads"}


def test_each_page_s_date_filter_reaches_every_dataset_that_reads_the_dates_and_starts_at_the_last_90_days():
    data = board()
    datasets = {dataset["name"]: dataset for dataset in data["datasets"]}
    for page, name in ((data["pages"][1], "gov_dates"), (data["pages"][2], "ai_dates")):
        [dates] = [tile for tile in page["layout"] if tile["widget"]["name"] == name]
        bound = {query["query"]["datasetName"] for query in dates["widget"]["queries"]}
        reading = {dataset for dataset in bound if ":dates.min" in "".join(datasets[dataset]["queryLines"])}
        assert bound == reading and bound
        for dataset in bound:
            [parameter] = [entry for entry in datasets[dataset]["parameters"] if entry["keyword"] == "dates"]
            assert parameter["defaultSelection"]["range"]["min"]["value"] == "now-90d/d"


# ── One entry to add a tile, and one to remove it ────────────────────────

def test_adding_a_tile_for_a_kpi_that_exists_is_one_entry_and_removing_it_is_deleting_that_entry():
    """The test copy is where a tile is tried first: one entry adds a counter for weekly users to Governance, and no
    other tile moves or changes; deleting that entry gives back the dashboard as it was."""
    before = render.render(definition.PAGES, test=True)
    governance = definition.GOVERNANCE
    added = replace(governance, tiles=(*governance.tiles, tiles.Counter("weekly_users_again", "weekly_users")))
    after = render.render((definition.DATA_READINESS, added, definition.AI_QUALITY), test=True)

    old, new = widgets(before["pages"][1]), widgets(after["pages"][1])
    assert set(new) - set(old) == {"weekly_users_again"}
    # The notes move down a row, and the page's date filter now also sets the new counter's query; nothing else changes.
    assert [name for name in old if new[name] != old[name]] == ["gov_dates", "governance_notes"]
    added_queries = [query for query in new["gov_dates"]["widget"]["queries"]
                     if query not in old["gov_dates"]["widget"]["queries"]]
    assert [query["query"]["datasetName"] for query in added_queries] == ["kpi_weekly_users"]
    assert new["weekly_users_again"]["widget"]["spec"]["widgetType"] == "counter"
    assert {dataset["name"] for dataset in after["datasets"]} - {dataset["name"] for dataset in before["datasets"]} == set()

    removed = replace(added, tiles=tuple(tile for tile in added.tiles if tile.name != "weekly_users_again"))
    assert render.render((definition.DATA_READINESS, removed, definition.AI_QUALITY), test=True) == before


def test_a_tile_can_be_tried_on_the_test_copy_before_the_dashboard_people_use_gets_it(tmp_path, monkeypatch):
    from strata.dashboard import __main__ as command

    monkeypatch.setattr(command, "FILE", tmp_path / "strata.lvdash.json")
    monkeypatch.setattr(command, "TEST_FILE", tmp_path / "strata_test.lvdash.json")

    assert command.main(["--write", "--test-only"]) == 0
    assert [path.name for path in tmp_path.iterdir()] == ["strata_test.lvdash.json"]
    assert command.main(["--write"]) == 0 and command.main([]) == 0


def test_the_test_copy_says_so_first_on_every_page():
    for page in board(dashboard.TEST_FILE)["pages"]:
        lines = page["layout"][0]["widget"]["multilineTextboxSpec"]["lines"]
        assert lines[0].startswith("## ") and lines[1].strip() == wording.at("dash.testLine")


# ── DESIGN.md section 6, and the brief's lists ───────────────────────────

def charts(data=None):
    for page in (data or board())["pages"]:
        for tile in page["layout"]:
            spec = tile["widget"].get("spec", {})
            if spec.get("widgetType") in ("bar", "line", "scatter"):
                yield page, tile, spec


def test_every_chart_and_table_names_its_measure_without_a_number_and_says_what_it_shows():
    for page in board()["pages"]:
        titles = []
        for tile in page["layout"]:
            spec = tile["widget"].get("spec")
            if not spec or spec["widgetType"].startswith("filter"):
                continue
            title, about = frame(tile)["title"], frame(tile)["description"]
            assert title and about, tile["widget"]["name"]
            if spec["widgetType"] != "counter":  # a KPI's name may hold its own window, as "within 14 days" does
                # The measures' own names keep their units and windows: "per 100", "8-in-10", "precision at 10",
                # "recall at 20", "rolling 12 months".
                named = re.sub(r"8-in-10|per 100|at 10|at 20|12 months", "", title)
                assert not re.search(r"\d", named), title
            titles.append(title)
        assert len(titles) == len(set(titles)), page["displayName"]


def test_colors_follow_the_entity_one_series_is_the_first_and_two_series_the_first_two_in_order():
    for _, tile, spec in charts():
        colors = spec["mark"]["colors"]
        data = [color for color in colors if color not in (tiles.REFERENCE, tiles.FAILED)]
        assert data == list(tiles.COLORS[:len(data)]), tile["widget"]["name"]
        mappings = spec["encodings"].get("color", {}).get("scale", {}).get("mappings", [])
        assert [mapping["color"] for mapping in mappings] == colors or not mappings, tile["widget"]["name"]


def test_only_a_failed_quality_check_uses_a_state_color_against_a_grey_passed():
    used = [(tile["widget"]["name"], spec["mark"]["colors"]) for _, tile, spec in charts()
            if tiles.FAILED in spec["mark"]["colors"]]

    assert used == [("nightly_checks", [tiles.FAILED, tiles.PASSED])]
    [checks] = [spec for _, tile, spec in charts() if tile["widget"]["name"] == "nightly_checks"]
    assert [mapping["value"] for mapping in checks["encodings"]["color"]["scale"]["mappings"]] == ["Failed", "Passed"]
    assert checks["mark"]["layout"] == "stack"


def test_a_budget_and_a_target_edge_are_drawn_in_the_reference_grey():
    for name, references in (("spend_chart", ["Budget"]), ("coverage_chart", ["75% target edge", "85% target edge"])):
        [spec] = [spec for _, tile, spec in charts() if tile["widget"]["name"] == name]
        grey = [mapping["value"] for mapping in spec["encodings"]["color"]["scale"]["mappings"]
                if mapping["color"] == tiles.REFERENCE]
        assert grey == references, name


def test_every_chart_has_its_table_twin_directly_under_it_in_the_same_columns():
    """The brief puts the retrieval chart's twin beside it (tiles 28 and 29), so that pair is not here."""
    twins = {"nightly_checks": "nightly_runs", "spend_chart": "spend_days", "service_chart": "spend_resources",
             "benchmark_chart": "benchmark_results", "foundry_chart": "foundry_results", "removed_chart": "reasons",
             "held_chart": "reasons", "decisions_chart": "decisions", "wrong_chart": "opened",
             "coverage_chart": "coverage", "users_chart": "use_by_week", "drafts_chart": "use_by_week",
             "award_rows": "source_rows", "links": "freshness", "routes": "freshness"}
    for page in board()["pages"]:
        placed = {tile["widget"]["name"]: tile["position"] for tile in page["layout"]}
        for chart, twin in twins.items():
            if chart not in placed:
                continue
            above, below = placed[chart], placed[twin]
            assert below["y"] >= above["y"] + above["height"], chart
            assert below["x"] <= above["x"] < below["x"] + below["width"], chart


def test_tiles_fill_the_six_column_grid_in_reading_order_and_tiles_in_a_row_share_a_height():
    for page in board()["pages"]:
        positions = [tile["position"] for tile in page["layout"]]
        assert positions == sorted(positions, key=lambda at: (at["y"], at["x"])), page["displayName"]
        rows: dict[int, set[int]] = {}
        for at in positions:
            assert at["x"] + at["width"] <= 6
            rows.setdefault(at["y"], set()).add(at["height"])
        assert all(len(heights) == 1 for heights in rows.values()), page["displayName"]


def test_every_page_ends_with_its_source_the_note_on_too_few_cases_and_the_footer():
    footer = wording.words()["footer"]
    for page, source in zip(board()["pages"], ("dash.readiness.source", "dash.gov.source", "dash.ai.source")):
        lines = page["layout"][-1]["widget"]["multilineTextboxSpec"]["lines"]
        assert lines == [f"**Source:** {wording.at(source)}\n",
                         "**Note:** I give no percentage, median, rate per 100 or range from fewer than 20 cases. "
                         "Where a tile has fewer, it shows the count instead.\n", footer]


def test_the_theme_sets_design_md_s_surfaces_and_the_categories_in_order():
    theme = board()["uiSettings"]["theme"]

    assert theme["visualizationColors"] == list(tiles.COLORS)
    assert theme["widgetBackgroundColor"]["light"] == "#ffffff"
    assert theme["canvasBackgroundColor"]["light"] == "#f5f7f9"


def test_counters_and_tables_write_numbers_in_full_and_axes_never_shorten_below_ten_thousand():
    for page in board()["pages"]:
        for tile in page["layout"]:
            for encoding in json.dumps(tile).split('"abbreviation": ')[1:]:
                assert encoding.startswith('"none"'), tile["widget"]["name"]


def test_the_definitions_tile_lists_each_loop_indicator_s_name_and_definition_in_loop_order():
    [tile] = [tile for tile in board()["pages"][2]["layout"] if tile["widget"]["name"] == "indicator_definitions"]
    lines = tile["widget"]["multilineTextboxSpec"]["lines"]
    loops = [kpi for kpi in load_kpis().values() if kpi.loop]

    assert [kpi.loop for kpi in loops] == ["knowledge"] * 2 + ["retrieval"] * 2 + ["estimates"] * 2
    assert [kpi.role for kpi in loops] == ["leading", "lagging"] * 3
    assert lines[1:] == [f"- **{wording.at(kpi.copy_keys[0])}.** {wording.at(kpi.copy_keys[1])}\n" for kpi in loops]
    assert "Implementation Completion and Results Report (ICR)" in lines[0]


def test_each_loop_s_leading_indicator_has_a_chart_with_its_twin_and_each_lagging_one_a_table():
    names = {tile["widget"]["name"]: tile for tile in board()["pages"][2]["layout"]}
    leading = {"decisions_chart": "kpi_days_to_decision", "wrong_chart": "kpi_wrong_passage_rate",
               "coverage_chart": "kpi_rolling_coverage"}
    lagging = {"hindsight": "kpi_blamed_covered", "retrieval": "kpi_precision_recall",
               "plan_accuracy": "kpi_plan_accuracy"}
    for name, dataset in {**leading, **lagging}.items():
        assert names[name]["widget"]["queries"][0]["query"]["datasetName"] == dataset, name
    assert [names[name]["position"]["width"] for name in leading] == [2, 2, 2]


# ── The query history ────────────────────────────────────────────────────

def test_where_the_query_history_can_t_be_read_tile_21_is_a_dated_text_tile_saying_so():
    import datetime as dt

    page = render.render_page(definition.GOVERNANCE, today=dt.date(2026, 10, 24), query_history=False)
    [tile] = [tile for tile in page["layout"] if tile["widget"]["name"] == "queries"]

    assert tile["widget"]["multilineTextboxSpec"]["lines"] == [
        "I can't show who queried what, because this workspace doesn't let me read its query history. I checked when "
        "this dashboard was deployed on October 24, 2026. If Free Edition adds it later, deploying the dashboard again "
        "adds the table here."]
    assert "queries" not in render.page_datasets(definition.GOVERNANCE, query_history=False)


def test_where_it_can_who_queried_what_counts_statements_per_person_way_in_and_table_never_their_text():
    import datetime as dt

    from strata.lakehouse.engine import DuckDBEngine

    # DuckDB reserves the catalog name system, so the workspace's lineage table stands in under another name here.
    with DuckDBEngine.open() as engine:
        engine.connection.execute("ATTACH ':memory:' AS workspace_system")
        engine.connection.execute("CREATE SCHEMA workspace_system.access")
        engine.connection.execute(
            "CREATE TABLE workspace_system.access.table_lineage (event_date DATE, created_by VARCHAR, "
            "entity_type VARCHAR, source_table_catalog VARCHAR, source_table_full_name VARCHAR, statement_id VARCHAR)")
        engine.connection.execute(
            "INSERT INTO workspace_system.access.table_lineage VALUES "
            "('2026-10-22', 'ana.example@worldbank.org', NULL, 'strata', 'strata.gold.package', 's1'), "
            "('2026-10-22', 'ana.example@worldbank.org', NULL, 'strata', 'strata.gold.package', 's2'), "
            "('2026-10-22', 'ana.example@worldbank.org', 'NOTEBOOK', 'strata', 'strata.gold.package', 's3'), "
            "('2026-10-22', 'ana.example@worldbank.org', NULL, 'workspace', 'workspace.default.trips', 's4')")
        sql = render.query("queries").replace("system.access.", "workspace_system.access.")
        result = engine.run(sql, {"date_from": dt.date(2026, 10, 1), "date_to": dt.date(2026, 10, 23)})

    assert result.columns == ("day", "person", "through", "table_read", "queries")
    assert list(result.rows) == [
        (dt.date(2026, 10, 22), "ana.example@worldbank.org", "Notebook", "strata.gold.package", 1),
        (dt.date(2026, 10, 22), "ana.example@worldbank.org", "Prism app", "strata.gold.package", 2)]


# ── Words ────────────────────────────────────────────────────────────────

def test_every_reason_code_the_dashboard_counts_has_a_label_so_none_reaches_it_as_raw_text():
    from strata.agent.verifier import REASONS
    from strata.knowledge.retrieval.labels import EVALUATION_SETS
    from strata.lakehouse import nightly

    held_codes = set(re.findall(r"'([a-z_]+)'", re.search(r"abstention IN \(([^)]*)\)",
                                                         render.source("kpi_answers_held_back")).group(1)))
    assert set(REASONS) <= set(wording.at("dash.ai.removed"))
    assert held_codes == set(wording.at("dash.ai.held"))
    for name in ("held_reasons", "reasons"):
        assert held_codes == set(re.findall(r"'([a-z_]+)'", re.search(r"abstention IN \(([^)]*)\)",
                                                                      render.source(name)).group(1))), name
    assert set(EVALUATION_SETS) <= set(wording.at("dash.ai.querySets"))
    assert [task.key for task in nightly.job_tasks()] == list(wording.at("dash.gov.task"))
    with open(ROOT / "config" / "evaluations.toml", "rb") as handle:
        assert {item["key"] for item in tomllib.load(handle)["evaluators"]} == set(wording.at("dash.ai.evaluators"))


def test_the_personal_data_tile_claims_only_what_the_contacts_counter_checks():
    """Counter 7 reads ticket 43's contacts_left check, which looks for what the removal's last pass takes out
    (contacts.LEFTOVERS): email addresses, labelled phone numbers and names after "Attention" and a title (ticket
    121). The text tile beside it says what the counter counts, so a leftover of another kind changes both."""
    from strata.lakehouse import contacts

    assert {(leftover.kind, leftover.rule) for leftover in contacts.LEFTOVERS} == {
        ("emails", contacts.EMAIL), ("phones", contacts.LABELLED), ("phones", contacts.SHORT_LABELLED),
        ("names", contacts.ATTENTION)}
    [tile] = [tile for tile in board()["pages"][1]["layout"] if tile["widget"]["name"] == "remove_why"]
    text = "".join(tile["widget"]["multilineTextboxSpec"]["lines"])
    assert text.rstrip().endswith(
        "The counter above counts any email addresses, phone numbers and names after \"Attention\" that got through.")


def test_every_kpi_has_its_name_definition_and_fallback_sentence_in_the_copy_file():
    for kpi in load_kpis().values():
        for key in kpi.copy_keys:
            assert isinstance(wording.at(key), str), key
        assert (ROOT / "src/strata/dashboard/sql/kpi" / f"{kpi.query}.sql").exists(), kpi.id


@pytest.mark.parametrize("text", ["don't", 'a "b" c', "it's \"so\""])
def test_words_with_quotes_reach_a_query_as_the_copy_file_writes_them(text):
    from strata.lakehouse.engine import DuckDBEngine

    with DuckDBEngine.open() as engine:
        assert engine.run(f"SELECT {render._literal(text)} AS words").rows == ((text,),)  # sql-lint: names only
