"""The dashboard definition: the pages of "Strata operations" and their tiles, as code (the spec's tenth single place;
ticket 45; the 45 design brief, sections 5 to 7).

Each page is a list of tile entries in reading order. strata.dashboard.render places them on AI/BI's six-column grid,
left to right and then down, and ends each page with its notes, so adding a tile is one entry here and removing it is
deleting that entry. A tile for a KPI that exists names it (config/kpis.toml); a new KPI also needs its query and its
copy keys. The words are copy keys (strata.dashboard.tiles explains them).

Write the dashboard files again after a change here, to the KPI registry or to the words:

    uv run --frozen python -m strata.dashboard --write
"""

from __future__ import annotations

from strata.dashboard.tiles import (FAILED, FIRST, PASSED, REFERENCE, SECOND, Axis, Chart, Column, Counter,
                                    Definitions, Filter, Findings, Page, Pivot, QueryHistory, Series, Table, Text)

PERCENT_FROM = "data_readiness.fewest_for_a_percentage"  # DESIGN.md section 7, rule 15: a percentage from 50 cases
COUNT_FROM = "data_readiness.fewest_for_a_share"  # and no median, rate or "in 10" from fewer than 20

RD = "readiness"
GOV = "dash.gov.tiles"
AI = "dash.ai.tiles"

# ── Page 1: Data readiness (ticket 16, with ticket 45's shared shape) ────

DATA_READINESS = Page("data_readiness", f"{RD}.page", notes="dash.readiness.source", tiles=(
    Text("introduction", (f"## {RD}.introHeading", f"{RD}.intro", "dash.warehouse")),
    Filter("measure_date", "date", "measure_date", f"{RD}.measureDate", f"{RD}.measureDateAbout"),
    Table("headline", "readiness_headline", (Column("measured_on", f"{RD}.measuredOn", "date"),
                                              Column("headline", f"{RD}.headlineColumn")),
          f"{RD}.headline", f"{RD}.headlineAbout", height=2),
    Chart("award_rows", "bar", "award_rows_by_year", Axis("fiscal_year_label", f"{RD}.fiscalYear"),
          Axis("award_rows", f"{RD}.rows", "quantitative"), f"{RD}.awardRows", f"{RD}.awardRowsAbout",
          series=Series("dataset", f"{RD}.dataset", values=(
              (f"{RD}.years.awards", "#106ca1"), (f"{RD}.years.awards_fy2001_2016", "#b65f0c"),
              (f"{RD}.years.fy2017_2019", "#664ab6")))),
    Pivot("source_rows", "rows_by_year", ("source", f"{RD}.source"), ("fiscal_year_label", f"{RD}.fiscalYear"),
          ("source_rows", f"{RD}.rows"), f"{RD}.sourceRows", f"{RD}.sourceRowsAbout"),
    Chart("links", "bar", "readiness_links", Axis("share_percent", f"{RD}.share", "quantitative", (0, 100)),
          Axis("link", f"{RD}.link"), f"{RD}.links", f"{RD}.linksAbout", width=3, horizontal=True, labels=True,
          tooltip=("count", "denominator"), fewest=PERCENT_FROM),
    Chart("routes", "bar", "readiness_routes", Axis("share_percent", f"{RD}.share", "quantitative", (0, 100)),
          Axis("route", f"{RD}.route"), f"{RD}.routes", f"{RD}.routesAbout", width=3, horizontal=True, labels=True,
          tooltip=("count", "denominator"), fewest=PERCENT_FROM),
    Table("freshness", "readiness_sources", (
        Column("source", f"{RD}.source"), Column("latest_data", f"{RD}.latestData", "date"),
        Column("updates", f"{RD}.updates"), Column("days_late", f"{RD}.daysLate", "integer"),
        Column("linked", f"{RD}.linked"), Column("read_well", f"{RD}.readWell"), Column("status", f"{RD}.status")),
        f"{RD}.freshness", f"{RD}.freshnessAbout", height=7),
    Table("fixes", "readiness_fixes", (Column("rank", f"{RD}.rank", "integer"), Column("fix", f"{RD}.fix"),
                                        Column("projects", f"{RD}.projects", "integer")),
          f"{RD}.fixes", f"{RD}.fixesAbout", height=5),
))

# ── Page 2: Governance (the 45 brief, section 6) ─────────────────────────

GOVERNANCE = Page("governance", "dash.gov.page", notes="dash.gov.source", tiles=(
    Text("gov_introduction", ("## dash.gov.page", "dash.gov.intro", "dash.warehouse")),
    Filter("gov_dates", "dates", "dates", "dash.dates.title", "dash.dates.about"),
    Filter("budget_period", "select", "budget_period", "dash.gov.budgetPeriod.title", "dash.gov.budgetPeriod.about",
           values="budget_periods", value_field="period_key", label_field="label"),
    Findings("gov_findings", "governance"),
    Counter("checks_failed", "checks_failed"),
    Counter("azure_spend", "azure_spend"),
    Counter("contacts_left", "contacts_left"),
    Text("runs_section", ("### dash.gov.sections.runs", "dash.gov.sections.runsText")),
    Chart("nightly_checks", "bar", "nightly_checks", Axis("night", f"{GOV}.checksChart.night", "temporal"),
          Axis("checks", f"{GOV}.checksChart.checks", "quantitative"), f"{GOV}.checksChart.title",
          f"{GOV}.checksChart.about", stacked=True,
          series=Series("result", f"{GOV}.checksChart.result", values=(
              ("dash.gov.result.failed", FAILED), ("dash.gov.result.passed", PASSED)))),
    Table("nightly_runs", "nightly_runs", (
        Column("night", f"{GOV}.runs.night", "date"), Column("outcome", f"{GOV}.runs.outcome"),
        Column("tasks_finished", f"{GOV}.runs.tasks"), Column("minutes", f"{GOV}.runs.minutes", "integer"),
        Column("rows_changed", f"{GOV}.runs.rows", "integer"), Column("checks_passed", f"{GOV}.runs.passed", "integer"),
        Column("checks_failed", f"{GOV}.runs.failed", "integer")), f"{GOV}.runs.title", f"{GOV}.runs.about"),
    Table("failed_checks", "failed_checks", (
        Column("night", f"{GOV}.failed.night", "date"), Column("task", f"{GOV}.failed.task"),
        Column("check_name", f"{GOV}.failed.check"), Column("table_name", f"{GOV}.failed.table"),
        Column("found", f"{GOV}.failed.found")), f"{GOV}.failed.title", f"{GOV}.failed.about"),
    Text("spend_section", ("### dash.gov.sections.spend", "dash.gov.sections.spendText")),
    Chart("spend_chart", "line", "spend_by_day", Axis("charged_on", f"{GOV}.spendChart.day", "temporal"),
          Axis("spent_so_far", f"{GOV}.spendChart.amount", "quantitative", decimals=2), f"{GOV}.spendChart.title",
          f"{GOV}.spendChart.about", width=3,
          series=Series(fields=(("spent_so_far", f"{GOV}.spendChart.spent", FIRST),
                                ("budget_usd", f"{GOV}.spendChart.budget", REFERENCE)))),
    Chart("service_chart", "bar", "spend_by_service", Axis("spent", f"{GOV}.serviceChart.spent", "quantitative",
                                                           decimals=2),
          Axis("service", f"{GOV}.serviceChart.service"), f"{GOV}.serviceChart.title", f"{GOV}.serviceChart.about",
          width=3, horizontal=True, labels=True),
    Table("spend_days", "spend_by_day", (
        Column("charged_on", f"{GOV}.spendDays.day", "date"),
        Column("spent_that_day", f"{GOV}.spendDays.thatDay", "number", 2),
        Column("spent_so_far", f"{GOV}.spendDays.soFar", "number", 2)),
        f"{GOV}.spendDays.title", f"{GOV}.spendDays.about", width=3),
    Table("spend_resources", "spend_by_resource", (
        Column("service", f"{GOV}.spendResources.service"), Column("resource", f"{GOV}.spendResources.resource"),
        Column("spent", f"{GOV}.spendResources.spent", "number", 2)),
        f"{GOV}.spendResources.title", f"{GOV}.spendResources.about", width=3),
    Text("personal_section", ("### dash.gov.sections.personal",), height=1),
    Table("contacts_removed", "contact_removals", (
        Column("kind", f"{GOV}.contacts.kind"), Column("removed", f"{GOV}.contacts.removed", "integer"),
        Column("notices", f"{GOV}.contacts.notices", "integer"), Column("last_removed", f"{GOV}.contacts.last", "date")),
        f"{GOV}.contacts.title", f"{GOV}.contacts.about", width=3, height=4),
    Text("remove_why", ("dash.gov.removeWhy",), width=3, height=4),
    Text("queries_section", ("### dash.gov.sections.queries", "dash.gov.sections.queriesText")),
    QueryHistory(Table("queries", "queries", (
        Column("day", f"{GOV}.queries.day", "date"), Column("person", f"{GOV}.queries.person"),
        Column("through", f"{GOV}.queries.through"), Column("table_read", f"{GOV}.queries.table"),
        Column("queries", f"{GOV}.queries.queries", "integer")), f"{GOV}.queries.title", f"{GOV}.queries.about"),
        "dash.gov.noHistory"),
    Text("lineage_section", ("### dash.gov.sections.lineage", "dash.gov.sections.lineageText"), width=4),
    Filter("run_id", "text", "run_id", "dash.gov.runId.title", "dash.gov.runId.about", height=2),
    Table("answer_run", "lineage_run", (
        Column("run_id", f"{GOV}.run.runId"), Column("asked", f"{GOV}.run.asked", "datetime"),
        Column("view", f"{GOV}.run.view"), Column("question", f"{GOV}.run.question"),
        Column("tool_calls", f"{GOV}.run.calls", "integer"), Column("sentences_kept", f"{GOV}.run.kept", "integer"),
        Column("sentences_removed", f"{GOV}.run.removed", "integer")), f"{GOV}.run.title", f"{GOV}.run.about",
        height=3),
    Table("tool_calls", "lineage_calls", (
        Column("call_order", f"{GOV}.calls.order", "integer"), Column("tool", f"{GOV}.calls.tool"),
        Column("inputs", f"{GOV}.calls.inputs"), Column("rows_returned", f"{GOV}.calls.rows", "integer"),
        Column("took_ms", f"{GOV}.calls.took", "integer"), Column("evidence_ids", f"{GOV}.calls.evidence")),
        f"{GOV}.calls.title", f"{GOV}.calls.about"),
    Table("tables_read", "lineage_reads", (
        Column("call", f"{GOV}.reads.call"), Column("table_name", f"{GOV}.reads.table"),
        Column("version_read", f"{GOV}.reads.version", "integer"), Column("written_by", f"{GOV}.reads.writtenBy", "date"),
        Column("sources", f"{GOV}.reads.source")), f"{GOV}.reads.title", f"{GOV}.reads.about"),
    Table("recent_runs", "recent_runs", (
        Column("asked", f"{GOV}.recent.asked", "datetime"), Column("run_id", f"{GOV}.recent.runId"),
        Column("view", f"{GOV}.recent.view"), Column("tool_calls", f"{GOV}.recent.calls", "integer"),
        Column("sentences_removed", f"{GOV}.recent.removed", "integer")), f"{GOV}.recent.title", f"{GOV}.recent.about"),
))

# ── Page 3: AI quality and adoption (the 45 brief, section 7) ────────────

AI_QUALITY = Page("ai_quality", "dash.ai.page", notes="dash.ai.source", tiles=(
    Text("ai_introduction", ("## dash.ai.page", "dash.ai.intro", "dash.warehouse")),
    Filter("ai_dates", "dates", "dates", "dash.dates.title", "dash.dates.about"),
    Findings("ai_findings", "ai", height=5),
    Counter("benchmark_passed", "benchmark_passed"),
    Counter("sentences_removed", "sentences_removed"),
    Counter("answers_held_back", "answers_held_back"),
    Counter("weekly_users", "weekly_users"),
    Counter("drafts_exported", "drafts_exported"),
    Counter("plan_rows_offered", "plan_rows_offered"),
    Text("answers_section", ("### dash.ai.sections.answers", "dash.ai.sections.answersText")),
    Chart("benchmark_chart", "line", "benchmark_shares", Axis("run_on", f"{AI}.benchmarkChart.run", "temporal"),
          Axis("share_percent", f"{AI}.benchmarkChart.share", "quantitative", (0, 100)), f"{AI}.benchmarkChart.title",
          f"{AI}.benchmarkChart.about", width=3, tooltip=("passed", "questions"), fewest=PERCENT_FROM),
    Chart("foundry_chart", "bar", "foundry_latest", Axis("share_percent", f"{AI}.foundryChart.share", "quantitative",
                                                         (0, 100)),
          Axis("evaluator", f"{AI}.foundryChart.evaluator"), f"{AI}.foundryChart.title", f"{AI}.foundryChart.about",
          width=3, horizontal=True, labels=True, tooltip=("met", "scored"), fewest=PERCENT_FROM),
    Table("benchmark_results", "benchmark_results", (
        Column("run_on", f"{AI}.benchmark.run", "date"), Column("kind", f"{AI}.benchmark.kind"),
        Column("passed", f"{AI}.benchmark.passed", "integer"), Column("questions", f"{AI}.benchmark.questions", "integer"),
        Column("target", f"{AI}.benchmark.target"), Column("against", f"{AI}.benchmark.against")),
        f"{AI}.benchmark.title", f"{AI}.benchmark.about", width=3),
    Table("foundry_results", "foundry_results", (
        Column("run_on", f"{AI}.foundry.run", "date"), Column("evaluator", f"{AI}.foundry.evaluator"),
        Column("met", f"{AI}.foundry.met", "integer"), Column("scored", f"{AI}.foundry.scored", "integer"),
        Column("mean_score", f"{AI}.foundry.mean", "number", 1)), f"{AI}.foundry.title", f"{AI}.foundry.about", width=3),
    Chart("removed_chart", "bar", "removed_reasons", Axis("sentences", f"{AI}.removedChart.count", "quantitative"),
          Axis("reason", f"{AI}.removedChart.reason"), f"{AI}.removedChart.title", f"{AI}.removedChart.about",
          width=3, horizontal=True, labels=True),
    Chart("held_chart", "bar", "held_reasons", Axis("answers", f"{AI}.heldChart.count", "quantitative"),
          Axis("reason", f"{AI}.heldChart.reason"), f"{AI}.heldChart.title", f"{AI}.heldChart.about",
          width=3, horizontal=True, labels=True),
    Table("reasons", "reasons", (
        Column("what", f"{AI}.reasons.what"), Column("reason", f"{AI}.reasons.reason"),
        Column("count", f"{AI}.reasons.count", "integer"), Column("out_of", f"{AI}.reasons.outOf")),
        f"{AI}.reasons.title", f"{AI}.reasons.about"),
    Text("loops_section", ("### dash.ai.sections.loops", "dash.ai.sections.loopsText")),
    Table("loop_indicators", "loop_indicators", (
        Column("loop", f"{AI}.indicators.loop"), Column("indicator", f"{AI}.indicators.indicator"),
        Column("kind", f"{AI}.indicators.kind"), Column("latest", f"{AI}.indicators.latest"),
        Column("target", f"{AI}.indicators.target"), Column("against", f"{AI}.indicators.against"),
        Column("measured", f"{AI}.indicators.measured")), f"{AI}.indicators.title", f"{AI}.indicators.about"),
    Definitions("indicator_definitions", "dash.ai.abbreviations", height=6),
    Chart("decisions_chart", "scatter", "kpi_days_to_decision",
          Axis("decided_on", f"{AI}.decisionsChart.decided", "temporal"),
          Axis("days_from_publication", f"{AI}.decisionsChart.days", "quantitative"), f"{AI}.decisionsChart.title",
          f"{AI}.decisionsChart.about", width=2),
    Chart("wrong_chart", "line", "kpi_wrong_passage_rate", Axis("week_start", f"{AI}.wrongChart.week", "temporal"),
          Axis("wrong_per_100", f"{AI}.wrongChart.rate", "quantitative", decimals=1), f"{AI}.wrongChart.title",
          f"{AI}.wrongChart.about", width=2, fewest="retrieval.min_opened",
          series=Series(fields=(("wrong_per_100", f"{AI}.opened.wrong", FIRST),
                                ("not_useful_per_100", f"{AI}.opened.notUseful", SECOND)))),
    Chart("coverage_chart", "line", "kpi_rolling_coverage", Axis("month", f"{AI}.coverageChart.month", "temporal"),
          Axis("coverage_percent", f"{AI}.coverageChart.share", "quantitative", (50, 100)),
          f"{AI}.coverageChart.title", f"{AI}.coverageChart.about", width=2, fewest=PERCENT_FROM,
          series=Series(fields=(("coverage_percent", f"{AI}.coverageChart.coverage", FIRST),
                                ("target_low", f"{AI}.coverageChart.low", REFERENCE),
                                ("target_high", f"{AI}.coverageChart.high", REFERENCE)))),
    Table("decisions", "kpi_days_to_decision", (
        Column("decided_on", f"{AI}.decisions.decided", "date"), Column("report", f"{AI}.decisions.report"),
        Column("days_from_publication", f"{AI}.decisions.days", "integer")),
        f"{AI}.decisions.title", f"{AI}.decisions.about", width=2),
    Table("opened", "kpi_wrong_passage_rate", (
        Column("week_start", f"{AI}.opened.week", "date"), Column("opened", f"{AI}.opened.opened", "integer"),
        Column("wrong_passage", f"{AI}.opened.wrong", "integer"),
        Column("not_useful", f"{AI}.opened.notUseful", "integer"),
        Column("wrong_per_100_cell", f"{AI}.opened.per100")), f"{AI}.opened.title", f"{AI}.opened.about", width=2),
    Table("coverage", "kpi_rolling_coverage", (
        Column("month", f"{AI}.coverage.month", "date"), Column("finished", f"{AI}.coverage.finished", "integer"),
        Column("inside", f"{AI}.coverage.inside", "integer"), Column("coverage_cell", f"{AI}.coverage.coverage")),
        f"{AI}.coverage.title", f"{AI}.coverage.about", width=2),
    Table("hindsight", "kpi_blamed_covered", (
        Column("release_name", f"{AI}.hindsight.release"), Column("projects", f"{AI}.hindsight.projects", "integer"),
        Column("blamed", f"{AI}.hindsight.blamed", "integer"), Column("covered", f"{AI}.hindsight.covered", "integer"),
        Column("shown_when_covered", f"{AI}.hindsight.shown"), Column("hindsight_recall", f"{AI}.hindsight.recall"),
        Column("checklist_caught", f"{AI}.hindsight.checklist", "integer")),
        f"{AI}.hindsight.title", f"{AI}.hindsight.about"),
    Chart("retrieval_chart", "line", "kpi_precision_recall", Axis("run_on", f"{AI}.retrievalChart.run", "temporal"),
          Axis("held_out_precision", f"{AI}.retrievalChart.score", "quantitative", (0, 1), decimals=2),
          f"{AI}.retrievalChart.title", f"{AI}.retrievalChart.about", width=3, fewest="retrieval.min_opened",
          series=Series(fields=(("held_out_precision", f"{AI}.retrievalChart.precision", FIRST),
                                ("held_out_recall", f"{AI}.retrievalChart.recall", SECOND)))),
    Table("retrieval", "kpi_precision_recall", (
        Column("run_on", f"{AI}.retrieval.run", "date"), Column("query_set", f"{AI}.retrieval.set"),
        Column("queries", f"{AI}.retrieval.queries", "integer"),
        Column("precision_at_10", f"{AI}.retrieval.precision", "number", 2),
        Column("recall_at_20", f"{AI}.retrieval.recall", "number", 2),
        Column("ndcg_at_10", f"{AI}.retrieval.ndcg", "number", 2)), f"{AI}.retrieval.title", f"{AI}.retrieval.about",
        width=3),
    Table("plan_accuracy", "kpi_plan_accuracy", (
        Column("plan_rows", f"{AI}.accuracy.rows"), Column("countries", f"{AI}.accuracy.countries"),
        Column("with_actual", f"{AI}.accuracy.actual", "integer"), Column("median_days_cell", f"{AI}.accuracy.days"),
        Column("median_months_cell", f"{AI}.accuracy.months")), f"{AI}.accuracy.title", f"{AI}.accuracy.about",
        height=4),
    Text("adoption_section", ("### dash.ai.sections.adoption", "dash.ai.sections.adoptionText")),
    Chart("users_chart", "bar", "use_by_week", Axis("week_start", f"{AI}.usersChart.week", "temporal"),
          Axis("people", f"{AI}.usersChart.people", "quantitative"), f"{AI}.usersChart.title",
          f"{AI}.usersChart.about", width=3),
    Chart("drafts_chart", "bar", "use_by_week", Axis("week_start", f"{AI}.draftsChart.week", "temporal"),
          Axis("checked", f"{AI}.draftsChart.drafts", "quantitative"), f"{AI}.draftsChart.title",
          f"{AI}.draftsChart.about", width=3,
          series=Series(fields=(("checked", f"{AI}.draftsChart.checked", FIRST),
                                ("exported", f"{AI}.draftsChart.exported", SECOND)))),
    Table("use_by_week", "use_by_week", (
        Column("week_start", f"{AI}.use.week", "date"), Column("people", f"{AI}.use.people", "integer"),
        Column("answers", f"{AI}.use.answers", "integer"), Column("started", f"{AI}.use.started", "integer"),
        Column("checked", f"{AI}.use.checked", "integer"), Column("exported", f"{AI}.use.exported", "integer")),
        f"{AI}.use.title", f"{AI}.use.about"),
    Table("plan_rows", "plan_rows_by_month", (
        Column("month", f"{AI}.planRows.month", "date"), Column("plan_rows", f"{AI}.planRows.rows", "integer"),
        Column("anchored", f"{AI}.planRows.offered", "integer"), Column("share", f"{AI}.planRows.share")),
        f"{AI}.planRows.title", f"{AI}.planRows.about"),
))

PAGES = (DATA_READINESS, GOVERNANCE, AI_QUALITY)
