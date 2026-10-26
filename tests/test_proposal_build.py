"""The proposal's build (ticket 46; the 46 brief, sections 4, 7, 9, 10, 12, 13 and 15), on a snapshot pulled from the
fixture and the dashboard's made-up month (tests/proposal_seed.py). The real proposal is built from the workspace's
snapshot, so nothing here is a finding.

Expected words and structure come from the brief, docs/assessment.md and DESIGN.md, never from the build.
"""

import datetime as dt
import html
import re
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from proposal_seed import merged
from strata import config
from strata.proposal import build, figures, numbers, register
from strata.proposal.__main__ import proposal_problems, source_problems

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "docs" / "proposal" / "source.md").read_text()
URLS = config.Urls("https://strata-1.aws.databricksapps.com", "https://dbc-1.cloud.databricks.com/dashboards/1",
                   "https://github.com/someone/strata")


@pytest.fixture(scope="module")
def snap(fixture_db):
    return merged(fixture_db)


def inputs(snap, **changes):
    return build.Inputs(**{"snapshot": snap, "commit": "0123456789abcdef", "urls": URLS, **changes})


@pytest.fixture(scope="module")
def built(snap):
    return build.build(SOURCE, inputs(snap))


def lint(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["node", str(ROOT / "web" / "lint" / "proposal.ts"), str(path)], capture_output=True,
                          text=True)


def paragraph(markdown: str, number: int) -> str:
    return next(line for line in markdown.splitlines() if line.startswith(f'<a id="p{number}"></a>'))


# ── The number check, on the proposal and on a planted copy ──────────────

def test_the_number_check_passes_on_the_built_proposal_and_its_links_all_land(built):
    assert numbers.unsourced(built.markdown) == []
    assert proposal_problems(built.markdown) == []


def test_the_number_check_fails_when_an_unlinked_number_is_planted_in_a_copy(built):
    planted = built.markdown.replace(paragraph(built.markdown, 3), paragraph(built.markdown, 3)
                                     + " Strata read 4,812 pages in a day.", 1)
    found = numbers.unsourced(planted)
    assert [(problem.where, problem.number) for problem in found] == [("Paragraph 3", "4,812")]
    assert proposal_problems(planted)[0].startswith("The number check failed. Paragraph 3 has a number with no source")


def test_a_number_typed_into_the_source_stops_the_build_and_the_gate(snap):
    planted = SOURCE.replace("{#summary-how} Strata keeps its data", "{#summary-how} In 14 months, Strata keeps its data")
    with pytest.raises(build.BuildError, match=r"Paragraph 3 has a number with no source: \"In 14 months"):
        build.build(planted, inputs(snap))
    assert any('has a number with no source: "In 14 months' in problem for problem in source_problems(planted))
    assert source_problems(SOURCE) == []


# ── Every state the build stops on ───────────────────────────────────────

def test_a_result_with_no_measured_value_stops_the_build_and_names_its_query_and_paragraph(snap):
    results = {**snap["results"], "passages": {"measured": False}}
    with pytest.raises(build.BuildError) as stopped:
        build.build(SOURCE, inputs({**snap, "results": results}))
    assert re.fullmatch(r"The proposal did not build\. Result passages has no measured value\. Measure it with "
                        r"src/strata/proposal/sql/passages\.sql, or remove the sentence that cites it in Paragraph "
                        r"\d+\.", str(stopped.value))


def test_a_missing_url_stops_the_build(snap):
    with pytest.raises(build.BuildError, match=r"^The data sheet can't link to app, because its URL isn't set in "
                                               r"config/urls.toml.$"):
        build.build(SOURCE, inputs(snap, urls=replace(URLS, app=None)))


def test_the_data_sheet_gives_the_decks_address_as_the_apps_with_present_and_the_repo(built):
    # The 46 brief, section 5: full addresses as link text, so a reader of a printed copy can type them in.
    sheet = built.markdown.split("## Summary")[0]
    deck = URLS.app + "/present"
    assert f'<tr><th scope="row">The deck</th><td><a href="{deck}">{deck}</a></td></tr>' in sheet
    assert f'<a href="{URLS.repo}">{URLS.repo}</a>' in sheet


def test_a_reference_to_a_paragraph_that_is_not_there_stops_the_build(snap):
    planted = SOURCE.replace("{fig:pipeline} shows the parts.", "{p:nowhere} shows the parts.")
    with pytest.raises(build.BuildError, match=r"^Paragraph 3 links to nowhere, which is not in the proposal.$"):
        build.build(planted, inputs(snap))


def test_a_figure_with_no_drawing_stops_the_build(snap):
    planted = SOURCE.replace("## Designed, not built", "{figure:ladder-drawing}\n**Figure. The ladder.**\n\n"
                                                         "## Designed, not built")
    with pytest.raises(build.BuildError, match=r"^Figure 10 is missing: proposal/figures/10-ladder-drawing.svg."):
        build.build(planted, inputs(snap))


# ── Structure: the modules and the rubric map ────────────────────────────

def test_the_sections_follow_the_assessments_four_modules_in_order(built):
    headings = re.findall(r"^## (.+)$", built.markdown, re.M)
    assert headings == [
        "Summary", "Where Strata earns each point", "Module 1: Ingestion and knowledge representation",
        "Module 2: Estimates and agentic retrieval", "Module 3: Guardrails, faithfulness and attribution",
        "Module 4: Learning loops and implementation", "Designed, not built", "Annex 1: Results register",
        "Annex 2: Settings and counts", "Annex 3: Data sources and licenses", "Annex 4: Words and abbreviations"]


def test_paragraphs_are_numbered_from_the_summary_without_gaps_and_the_annexes_have_none(built):
    body, annexes = built.markdown.split("## Annex 1: Results register")
    numbered = [int(n) for n in re.findall(r'<a id="p(\d+)"></a>\*\*(?:\d+)\.\*\*', body)]
    assert numbered == list(range(1, len(numbered) + 1)) and len(numbered) > 40
    assert '<a id="p' not in annexes
    assert '<a id="p1"></a>' not in body.split("## Summary")[0]


def test_the_rubric_map_lists_each_dimension_with_its_points_and_the_sections_that_earn_them(built):
    rubric_map = built.markdown.split("## Where Strata earns each point")[1].split("## Module 1")[0]
    # docs/assessment.md, section 5: the four dimensions and their points, linked to the rubric.
    for name, points in (("System and knowledge architecture", 30), ("Analytical and AI methodology", 30),
                         ("Domain alignment and data use", 25), ("Operationalization and scalability", 15)):
        assert re.search(rf"<strong>{name}</strong>, <a href=\"assessment.md#5-evaluation--assessment-rubric\">"
                         rf"{points}</a> points", rubric_map), name
    assert rubric_map.count('<td data-quote="assessment">') == 13
    rows = re.findall(r'<td data-quote="assessment">[^<]+</td><td>(.*?)</td>', rubric_map)
    assert all(re.search(r'href="#(p\d+|figure-\d|sec-annex-sources)"', row) for row in rows)
    assert 'All four dimensions, <a href="assessment.md#5-evaluation--assessment-rubric">100</a> points' in rubric_map


def test_each_module_opens_with_its_scored_under_line_and_an_in_short_paragraph(built):
    for module in re.split(r"^## Module \d: ", built.markdown, flags=re.M)[1:]:
        lines = [line for line in module.splitlines() if line.strip()]
        assert lines[1].startswith("Scored under [")
        assert "**In short.**" in lines[2]


def test_the_showcase_trail_names_only_the_records_its_contract_trail_holds(built):
    # tests/fixtures/api/activity-in-rrsmp-7431.json, the package's trail: no plan read for P130164 and no invitation
    # found, so the trail holds the award notice OP00044090 with its bids, the contract, and the report paragraphs
    # that appeared together with it.
    import json

    trail = json.loads((ROOT / "tests" / "fixtures" / "api" / "activity-in-rrsmp-7431.json").read_text())
    found = {stage["stage"]: stage["found"] for stage in trail["stages"]}
    assert found == {"plan": False, "notice": False, "bids": True, "contract": True, "paragraphs": True}
    sentences = next(line for line in built.markdown.splitlines() if "IN-RRSMP-7431-CW-RFB" in line
                     and line.startswith('<a id="p'))
    assert "plan row" not in sentences and "invitation" not in sentences
    assert "Award notice OP00044090" in sentences and "bids" in sentences and "appeared together" in sentences


def test_the_module_3_disagreement_quotes_the_icr_and_isr_7_as_the_ground_truth_holds_them_and_links_both(built):
    # tests/ground_truth/values.toml: ICR paragraph 78 on PDF page 27 against ISR 7 of August 26, 2016, rated
    # Satisfactory, each from its own page of the recorded documents.
    import tomllib

    with open(ROOT / "tests" / "ground_truth" / "values.toml", "rb") as handle:
        facts = {entry["id"]: entry for entry in tomllib.load(handle)["value"]}
    icr, day, rating = facts["icr-para-78"], facts["isr-7-date"], facts["isr-7-rating"]
    showcase = next(line for line in built.markdown.splitlines() if "The assessment's own case is in" in line)
    assert f"{day['value']:%B} {day['value'].day}, {day['value'].year}" in showcase
    assert f'"{rating["value"]}"' in showcase
    assert f'"{icr["quote"]}"' in showcase
    assert f"paragraph {icr['paragraph']}, on page {icr['pdf_page']}" in showcase
    for fact, part in ((icr, f"?page={icr['pdf_page']}&para={icr['paragraph']}"), (day, f"?page={day['pdf_page']}")):
        project, key = fact["document"].split("/")[1:]
        assert f"(https://strata-1.aws.databricksapps.com/projects/{project}/documents/{key}{part})" in showcase


def test_model_names_come_from_the_model_file_so_swapping_a_model_changes_the_next_build(snap):
    # docs/PLAN.md section 15's drill "Swap the model" changes config/models.toml alone (CLAUDE.md rule 9).
    for model in config.load_models().values():
        assert model.deployment not in SOURCE, model.deployment
    models = {**config.load_models()}
    models["embed"] = replace(models["embed"], deployment="text-embedding-swapped")
    swapped = build.build(SOURCE, inputs(snap, models=models)).markdown
    assert "`text-embedding-swapped`" in swapped
    assert config.load_models()["embed"].deployment not in swapped


# ── The change drill's times (ticket 49; the 46 brief, sections 11.4 and 15) ──

PACIFIC = dt.timezone(dt.timedelta(hours=-7))


def rehearsed(minutes: dict[str, int]) -> dict[str, register.Rehearsal]:
    """Made-up rehearsals that took the minutes given, each finished on October 26, 2026, 30 seconds short of a
    whole minute."""
    start = dt.datetime(2026, 10, 26, 10, 0, tzinfo=PACIFIC)
    return {change: register.Rehearsal(change, "An example.", f"drill-49/{number:02d}-example", f"{number:040d}",
                                       start, start + dt.timedelta(minutes=taken, seconds=-30), 130.5)
            for number, (change, taken) in enumerate(minutes.items(), 1)}


def drill_section(markdown: str) -> str:
    return markdown.split("### Changing Strata in round 2")[1].split("## Designed, not built")[0]


CHANGES = [drill.change for drill in config.load_change_drills()]


def test_until_a_drill_is_rehearsed_its_time_reads_not_rehearsed_yet_and_a_note_says_why(snap):
    section = drill_section(build.build(SOURCE, inputs(snap, rehearsals={})).markdown)

    assert "| Change | The one place it lives | Time, minutes | Proved by |" in section
    assert "| Add a data source | [`config/sources.toml`](../config/sources.toml) | Not rehearsed yet |" in section
    assert section.count("Not rehearsed yet") == len(CHANGES) == 10
    assert ("**Note:** The rehearsal times come from the change drill run in phase P4. This version was built before "
            "it.") in section
    assert "Their rehearsal has not run yet, so the table gives no times." in section
    assert "The table gives the minutes each one took" not in section


def test_a_rehearsed_drill_shows_its_minutes_linked_to_its_row_in_annex_1_and_the_note_goes(snap):
    markdown = build.build(SOURCE, inputs(snap, rehearsals=rehearsed({change: 6 for change in CHANGES}))).markdown
    section = drill_section(markdown)

    assert ('| Swap the model | [`config/models.toml`](../config/models.toml) | '
            '[6](#r-drill-swap-the-model "6 minutes. Rehearsal, measured Oct 26, 2026.") |') in section
    assert "Not rehearsed yet" not in section and "**Note:**" not in section
    assert "**Source:** Annex 1." in section
    [row] = [line for line in markdown.splitlines() if line.startswith('| <a id="r-drill-swap-the-model"></a>')]
    assert "| 6 | Oct 26, 2026 | Rehearsal; branch `drill-49/05-example`, commit `0000000`" in row
    assert "the gate passed in 130.5 seconds" in row
    assert '[The section "Changing Strata in round 2"](#sec-m4-drill)' in row  # as every Cited in cell
    # The P3 phase gate's finding: the ten-minute claim links to its target in Annex 2, and the times are cited.
    assert re.search(r"so it can land in under \[10\]\(#s-drill-target [^)]*\) minutes with the gate green\.", section)
    assert "The table gives the minutes each one took when it was rehearsed" in section
    assert "Their rehearsal has not run yet" not in section
    assert numbers.unsourced(markdown) == []


def test_a_drill_over_ten_minutes_says_its_target_was_not_met_and_is_never_left_out(snap):
    times = {change: 6 for change in CHANGES} | {"Add a data source": 12}
    markdown = build.build(SOURCE, inputs(snap, rehearsals=rehearsed(times))).markdown
    section = drill_section(markdown)

    [line] = [line for line in section.splitlines() if line.startswith("| Add a data source |")]
    assert '[12](#r-drill-add-a-data-source "12 minutes. Rehearsal, measured Oct 26, 2026.")' in line
    assert re.search(r"<br>Target: \[10\]\(#s-drill-target [^)]*\)\. Not met\. \|", line)
    [row] = [line for line in markdown.splitlines() if line.startswith('| <a id="r-drill-add-a-data-source"></a>')]
    assert re.search(r"\| 12<br>Target: \[10\]\(#s-drill-target [^)]*\)\. Not met\. \|", row)
    assert '<a id="s-drill-target"></a>' in markdown.split("## Annex 2")[1]


def test_while_any_drill_is_not_rehearsed_the_note_stays(snap):
    section = drill_section(build.build(SOURCE, inputs(snap, rehearsals=rehearsed({CHANGES[0]: 4}))).markdown)

    assert section.count("Not rehearsed yet") == len(CHANGES) - 1
    assert "**Note:** The rehearsal times come from the change drill run in phase P4." in section


def test_the_retrieval_scores_name_the_query_set_they_were_measured_on(built):
    # docs/proposal/results.toml pins precision, recall and nDCG to the ICR Review citation set; the live run scores
    # four other sets too (src/strata/knowledge/retrieval/labels.py).
    measured = next(line for line in built.markdown.splitlines() if "precision at 10 was" in line)
    shown = re.sub(r' "[^"]*"\)', ")", measured)  # the words a reader sees, without each number's link title
    assert "on the ICR Review citation set" in shown
    register = built.markdown.split("## Annex 1")[1].split("## Annex 2")[0]
    assert "Precision at 10 on the ICR Review citation set, the newest run" in register


def test_the_retrieval_label_line_says_code_builds_the_labels_and_counts_the_queries_from_the_run(built):
    # src/strata/knowledge/retrieval/labels.py: icr_review_citations are silver labels that code takes from each
    # "ICR para N" citation, and no step has a person check them (STATUS.md decision 5 asks the proposal to say how).
    # tests/dashboard_seed.py: the October 10 run asked 250 queries of the set.
    # Recall and nDCG rest on the same labels, so their rows say so too.
    for key in ("retrieval-precision", "retrieval-recall", "retrieval-ndcg"):
        row = next(line for line in built.markdown.splitlines() if line.startswith(f'| <a id="r-{key}">'))
        assert ('Labels: 250 queries that code built from ICR Reviews. Each "ICR para N" citation in an ICR Review '
                "is a query, and the paragraphs it names answer it. No person checks them.") in row, key
    assert "checked by one person" not in built.markdown


def shown_words(line: str) -> str:
    """A built line as a reader sees it: each link's text, without its target or title."""
    return re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", line)


def test_the_spend_sentence_writes_money_as_the_dashboards_sentence_does(built):
    # tests/test_dashboard_findings.py: the dashboard says "had cost US$7.80 of the US$197.00 budget for the free
    # credit" from the same made-up cost pull. The 46 brief, section 11.3: the proposal and the dashboard agree.
    spend = shown_words(next(line for line in built.markdown.splitlines() if "the latest day with cost data" in line))
    assert "Strata's Azure resources had cost US$7.80 of the US$197.00 budget for the free credit" in spend


def test_spend_past_the_budget_says_how_far_past_as_the_dashboards_over_sentence_does(snap):
    # tests/test_dashboard_kpis.py: US$7.80 against a US$5.00 budget is US$2.80 over, in the dashboard's words.
    over = {**snap["results"]["azure-spend"], "n": 7.8, "d": 5, "budget": 5, "over": 2.8}
    markdown = build.build(SOURCE, inputs({**snap, "results": {**snap["results"], "azure-spend": over}})).markdown
    spend = shown_words(next(line for line in markdown.splitlines() if "the latest day with cost data" in line))
    assert "had cost US$7.80. That is US$2.80 more than the US$5.00 budget for the free credit" in spend
    assert "of the US$5.00 budget" not in markdown


def test_with_no_cost_data_yet_the_spend_paragraph_and_its_summary_row_say_so_instead_of_stopping_the_build(snap):
    # The 46 brief, section 15, "No cost data yet": brief 45's words, with the dashboard's "I" made "Strata".
    none = {**snap, "results": {**snap["results"], "azure-spend": {"measured": False}}}
    markdown = build.build(SOURCE, inputs(none)).markdown
    said = ("Strata has no Azure cost data yet. The daily cost pull adds each day's charges once Azure reports them.")
    spend = next(line for line in markdown.splitlines() if line.startswith('<a id="p') and "Azure cost data" in line)
    assert said in spend
    summary = markdown.split("### What the build measured")[1].split("**Source:**")[0]
    assert f"| Operationalization and scalability | {said} | Not measured yet |" in summary
    assert "the latest day with cost data" not in markdown
    assert proposal_problems(markdown) == []
    # With cost data, the no-cost words are left out.
    assert "Strata has no Azure cost data yet" not in build.build(SOURCE, inputs(snap)).markdown


def test_the_gate_names_a_measured_condition_whose_result_is_not_in_the_register():
    planted = SOURCE.replace("{when:unmeasured:azure-spend}", "{when:unmeasured:azure-spent}", 1)
    assert source_problems(planted) == ["docs/proposal/source.md keeps a line on the result azure-spent, which is not "
                                        "in docs/proposal/results.toml."]


# ── Designed, not built ──────────────────────────────────────────────────

def test_with_nothing_designed_but_unbuilt_the_list_says_so_and_the_summary_leaves_it_out(built):
    section = built.markdown.split("## Designed, not built")[1].split("## Annex 1")[0]
    assert 'Everything this proposal describes is built. Strata shows no "Designed, not built" labels.' in section
    assert "These parts of Strata are designed" not in section
    assert 'Anything marked "Designed, not built"' not in built.markdown.split("## Summary")[0]
    assert "designed but not built" not in built.markdown.split("## Where Strata earns")[0]


def test_each_item_designed_but_not_built_gets_its_row_and_the_summary_names_the_list(snap):
    item = config.DesignedNotBuilt("hazard_model", "The early-warning model", "/projects/P156634",
                                   "m2-signals", "Strata shows fixed signals.")
    markdown = build.build(SOURCE, inputs(snap, designed=(item,))).markdown
    section = markdown.split("## Designed, not built")[1].split("## Annex 1")[0]
    assert ('| <a id="dnb-hazard_model"></a>The early-warning model | Strata shows fixed signals. | '
            "[/projects/P156634](https://strata-1.aws.databricksapps.com/projects/P156634) |") in section
    assert "Some parts of Strata are designed but not built" in markdown.split("## Where Strata earns")[0]
    assert "These parts of Strata are designed, and this proposal describes them, but they are not in the app yet." \
        in section
    assert 'Anything marked "Designed, not built"' in markdown.split("## Summary")[0]


# ── Annexes: attributions word for word ──────────────────────────────────

def design_section_8() -> str:
    text = (ROOT / "DESIGN.md").read_text()
    return text.split("## 8. Attribution and disclaimers")[1].split("## 9.")[0]


def test_annex_3_credits_every_dataset_and_the_fixed_lines_word_for_word_from_design_md(built):
    from strata.tools.data_readiness_for import registry_page

    annex = built.markdown.split("## Annex 3: Data sources and licenses")[1].split("## Annex 4")[0]
    section = design_section_8()
    # DESIGN.md section 8's example line, with the source registry's names in its slots.
    example = re.search(r'For example: "(The World Bank: [^"]+)"', section).group(1)
    template = example.replace("Contract Awards in Investment Project Financing (Since FY 2020)", "{dataset}").replace(
        "Systematic Tracking of Exchanges in Procurement (STEP)", "{source}").replace("CC BY 4.0", "{license}")
    for row in registry_page()["datasets"]:
        assert template.format(dataset=row["dataset_name"], source=row["data_source"], license=row["license"]) in annex
    for fixed in ("Terms of use: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets",
                  "Strata joined these records, read the documents, and summarized them. These changes are Strata's own.",
                  "The World Bank does not guarantee the accuracy of the data.",
                  "The World Bank Group authorizes the use of this material subject to the terms and conditions on its "
                  "website, Legal."):
        assert fixed in section and fixed in annex
    footer = re.search(r'\| Footer, every screen, slide and dashboard page \| "([^"]+)" \|', section).group(1)
    assert built.markdown.count(footer) == 2


# ── Figures: the strata-wb profile and DESIGN.md section 6 ───────────────

def design_colors() -> set[str]:
    text = (ROOT / "DESIGN.md").read_text()
    profile = text.split("## 11. Diagram-design profile")[1]
    charts = text.split("## 6. Data visualization")[1].split("## 7. Writing")[0]
    light = {row.split("|")[2].strip().strip("`").lower() for row in profile.splitlines()
             if re.match(r"^\| `[a-z0-9-]+` \| `#", row)}
    return light | {color.lower() for color in re.findall(r"#[0-9a-fA-F]{6}", charts)} | {"#ffffff"}


def test_the_nine_figures_use_the_strata_wb_colors_and_type_on_the_paper_background(built):
    assert len(built.figures) == 9
    allowed = design_colors()
    for file, svg in built.figures.items():
        colors = {color.lower() for color in re.findall(r"#[0-9a-fA-F]{6}\b", svg)}
        assert colors <= allowed, (file, colors - allowed)
        assert re.search(r'<rect width="720" height="\d+" fill="#f5f7f9"/>', svg), file
        assert set(re.findall(r"font-family=\"'([^']+)'", svg)) <= {"Open Sans", "Roboto Mono"}, file
        assert min(int(size) for size in re.findall(r'font-size="(\d+)"', svg)) >= 12, file
        assert "logo" not in svg.lower(), file


def test_a_data_chart_has_a_table_twin_whose_numbers_link_to_the_register(built):
    figure = built.markdown.split('<a id="figure-5"></a>')[1].split("</details>")[0]
    assert "<details><summary>Show the table</summary>" in figure
    assert re.search(r"\| 2021 \| \[31 of 40\]\(#r-backtest-years ", figure)  # tests/proposal_seed.py, BACKTEST
    assert "| 2023 | [9 of 12](#r-backtest-years" in figure
    # 2021 has 40 packages: enough for "about N in 10" (20) but not for a percentage (50), DESIGN.md section 7, rule 15
    # and config/thresholds.toml's data_readiness.fewest_for_a_percentage. The chart draws percentages.
    assert re.search(r"\| 2021 \| \[31 of 40\][^|]*\| Too few for a percentage \|", figure)
    assert "Too few for a share" not in built.markdown


def test_diagrams_carry_no_numbers(built):
    for slug in ("pipeline", "knowledge-model", "reading", "retrieval", "checks", "loops"):
        svg = next(text for file, text in built.figures.items() if file.endswith(f"-{slug}.svg"))
        words = html.unescape(" ".join(re.findall(r">([^<>]+)</text>", svg)))
        for model in config.load_models().values():  # a model's name holds digits, and is a name
            words = words.replace(model.deployment, " ")
        assert not re.search(r"\d|\b(two|three|four|five|six|seven|eight|nine)\b", words, re.I), slug
    assert figures.DATA_CHARTS == ("award-gap", "backtest", "hindsight")


# ── The copy lint ────────────────────────────────────────────────────────

def test_the_copy_lint_passes_on_the_built_proposal_and_catches_a_planted_word(built, tmp_path):
    good = tmp_path / "proposal.md"
    good.write_text(built.markdown)
    assert lint(good).returncode == 0, lint(good).stdout
    bad = tmp_path / "planted.md"
    bad.write_text(built.markdown.replace(paragraph(built.markdown, 3),
                                          paragraph(built.markdown, 3) + " The Bank must validate the PP — quickly."))
    found = lint(bad)
    assert found.returncode == 1
    assert all(word in found.stdout for word in ('"The Bank"', '"validate"', '"PP"', "em dash"))
