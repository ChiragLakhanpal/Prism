"""The dashboard definition as an AI/BI dashboard file (ticket 45; the 45 design brief, sections 2 to 4 and 8).

render() turns the pages of strata.dashboard.definition into the JSON an AI/BI dashboard file holds: its datasets,
each with its query and the parameters it reads, its pages with each tile placed on the six-column grid in reading
order, and the theme every page shares. Nothing on the dashboard computes a number (CLAUDE.md rule 1): every number
is a column of a dataset's query, and every counter shows its KPI query's display string as it is.

A dataset's query is the SQL file of its name in sql/ (or, for kpi_<id>, the KPI's query in sql/kpi/, from
config/kpis.toml). Before a query is written into the file, or run in a test, these placeholders in it are filled:

- :copy__<path>             words from the copy file (copy.dash and copy.kpi), as SQL text, such as
                            :copy__kpi__display__share for "{n} of {d}"
- :threshold__<section>__<key>   a value of config/thresholds.toml, such as the fewest cases for a percentage
- :<label>__<column>        a column's code in words, by a map of the copy file (LABELS), such as
                            :task_label__task_key for "Fetch what changed"
- :task_order__<column>     a nightly task's place in the job, and :nightly_tasks how many tasks it has
- :share__<n>__<d>          the counts "{n} of {d}"; :ratio__<n>__<d> the counts with their share as DESIGN.md section
                            7 writes them; :percent__<n>__<d> the whole percent, empty below the fewest cases for one

so the words have one home and the copy lint checks them, and the queries the gate runs on DuckDB are the ones the
dashboard runs. The parameters a viewer sets stay bound: :measure_date, :budget_period, :run_id, and :date_from and
:date_to, which the file writes as AI/BI's date range parameter, :dates.min and :dates.max.
"""

from __future__ import annotations

import datetime as dt
import re
from functools import cache
from importlib import resources

from strata.config import load_kpis, load_thresholds
from strata.dashboard import tiles as kinds
from strata.dashboard import wording
from strata.dashboard.tiles import COLORS, Page

PLACEHOLDER = re.compile(r"(?<![:\w]):([a-z][A-Za-z0-9_]*)")
PARAMETERS = ("measure_date", "date_from", "date_to", "budget_period", "run_id")
GRID = 6
# Each map of codes to words a query may use, by the name of its placeholder.
LABELS = {
    "task_label": "dash.gov.task",
    "check_label": "dash.gov.checkName",
    "kind_label": "dash.gov.kinds",
    "through_label": "dash.gov.through",
    "view_label": "dash.gov.views",
    "removed_label": "dash.ai.removed",
    "held_label": "dash.ai.held",
    "benchmark_kind_label": "dash.ai.kinds",
    "evaluator_label": "dash.ai.evaluators",
    "query_set_label": "dash.ai.querySets",
}
# The theme every page shares (the 45 brief, section 8.1): DESIGN.md's page, surface, line and chart text, the
# selection color, and the categories in order with their text variants.
THEME = {
    "canvasBackgroundColor": {"light": "#f5f7f9"},
    "widgetBackgroundColor": {"light": "#ffffff"},
    "widgetBorderColor": {"light": "#dae3eb"},
    "fontColor": {"light": "#111111"},
    "selectionColor": {"light": "#0071bc"},
    "visualizationColors": list(COLORS),
    "widgetHeaderAlignment": "LEFT",
}


# ── Words ────────────────────────────────────────────────────────────────

def words(key: str, fewest: str | None = None) -> str:
    """The words at a copy key, with {fewest} filled from the thresholds file when the tile names its value."""
    if key.startswith("readiness."):
        from strata.tools.data_readiness_for import words as readiness_words

        value = readiness_words()["dashboard"]
        for part in key.split(".")[1:]:
            value = value[part]
    else:
        value = wording.at(key)
    if not isinstance(value, str):
        raise KeyError(f"The copy at {key} is not one string.")
    if "{fewest}" in value:
        if fewest is None:
            raise KeyError(f"The copy at {key} names {{fewest}}, so its tile must say which threshold fills it.")
        value = value.replace("{fewest}", str(load_thresholds().value(fewest)))
    return value


def _literal(text: str) -> str:
    """Words as SQL text. Spark SQL reads 'don''t' as two strings run together, and mangles backslashes, so words
    with an apostrophe go in double quotes, which Databricks SQL reads as text and the transpile step rewrites for
    DuckDB; words with both kinds of quote are joined from parts."""
    if "'" not in text:
        return f"'{text}'"
    if '"' not in text:
        return f'"{text}"'
    return "concat(" + ", ".join(_literal(part) if part else "''" for part in
                                 re.split(r"(')", text) if part) + ")"


def _label_case(name: str, column: str) -> str:
    mapping = wording.at(LABELS[name])
    whens = " ".join(f"WHEN {_literal(code)} THEN {_literal(text)}" for code, text in mapping.items())
    return f"CASE {column} {whens} ELSE {column} END"


def _task_order(column: str) -> str:
    from strata.lakehouse import nightly

    whens = " ".join(f"WHEN {_literal(task.key)} THEN {number}" for number, task in enumerate(nightly.job_tasks(), 1))
    return f"CASE {column} {whens} END"


def _count(n: str, d: str) -> str:
    return (f"replace(replace({_literal(wording.at('kpi.display.share'))}, '{{n}}', format_number({n}, 0)), '{{d}}', "
            f"format_number({d}, 0))")


def _whole(expression: str) -> str:
    return f"CAST(CAST(round({expression}) AS BIGINT) AS STRING)"


def _ratio(n: str, d: str) -> str:
    """DESIGN.md section 7, rules 6 and 15, as web/src/lib/format.ts's formatRatio writes a table cell."""
    value = load_thresholds().value
    fewest, percent_from = int(value("data_readiness.fewest_for_a_share")), int(value("data_readiness.fewest_for_a_percentage"))
    say = wording.at("dash.ratio")
    count = _count(n, d)
    part = f"{n} > 0 AND {n} < {d}"
    pct, tenths = f"(100.0 * {n} / {d})", f"(10.0 * {n} / {d})"

    def fill(template: str, slot: str | None = None, number: str | None = None) -> str:
        text = f"replace({_literal(say[template])}, '{{count}}', {count})"
        return f"replace({text}, '{{{slot}}}', {number})" if slot else text

    return (f"CASE WHEN {d} >= {percent_from} THEN CASE "
            f"WHEN {part} AND round({pct}) = 0 THEN {fill('underPercent')} "
            f"WHEN {part} AND round({pct}) = 100 THEN {fill('overPercent')} "
            f"ELSE {fill('percent', 'pct', _whole(pct))} END "
            f"WHEN {d} >= {fewest} AND {part} THEN CASE "
            f"WHEN round({tenths}) = 0 THEN {fill('fewerThanOne')} "
            f"WHEN round({tenths}) = 10 THEN {fill('moreThanNine')} "
            f"WHEN (10 * {n}) % {d} = 0 THEN {fill('inTenExact', 'in10', _whole(tenths))} "
            f"ELSE {fill('inTen', 'in10', _whole(tenths))} END "
            f"ELSE {count} END")


def _percent(n: str, d: str) -> str:
    percent_from = int(load_thresholds().value("data_readiness.fewest_for_a_percentage"))
    return f"CASE WHEN {d} >= {percent_from} THEN CAST(round(100.0 * {n} / {d}) AS BIGINT) END"


def _expand(name: str) -> str | None:
    """A placeholder's SQL, or None for a parameter the viewer sets."""
    if name in PARAMETERS:
        return None
    head, _, rest = name.partition("__")
    if head == "copy":
        text = wording.at(rest.replace("__", "."))
        if not isinstance(text, str):
            raise KeyError(f"The copy at {rest.replace('__', '.')} is not one string, so a query can't use it as text.")
        return _literal(text)
    if head == "threshold":
        return repr(load_thresholds().value(rest.replace("__", ".")))
    if head == "nightly_tasks":
        from strata.lakehouse import nightly

        return str(len(nightly.job_tasks()))
    if head in LABELS:
        return _label_case(head, rest)
    if head == "task_order":
        return _task_order(rest)
    if head in ("share", "ratio", "percent"):
        n, _, d = rest.partition("__")
        return {"share": _count, "ratio": _ratio, "percent": _percent}[head](n, d)
    raise KeyError(f"A dashboard query names :{name}, which is neither a parameter ({', '.join(PARAMETERS)}) nor a "
                   "placeholder strata.dashboard.render knows.")


def expand(sql: str) -> str:
    """A query with its placeholders filled and its comment lines left out: what the dashboard and the gate run."""
    body = "\n".join(line for line in sql.splitlines() if not line.lstrip().startswith("--")).strip()
    return PLACEHOLDER.sub(lambda match: _expand(match.group(1)) or match.group(0), body)


# ── Datasets ─────────────────────────────────────────────────────────────

def source(name: str) -> str:
    """A dataset's query as written in its SQL file: kpi_<id> is the KPI's defining query (config/kpis.toml)."""
    folder = resources.files("strata.dashboard") / "sql"
    if name.startswith("kpi_"):
        kpi = load_kpis()[name[len("kpi_"):]]
        return (folder / "kpi" / f"{kpi.query}.sql").read_text()
    return (folder / f"{name}.sql").read_text()


@cache
def query(name: str) -> str:
    """A dataset's query as the gate runs it on DuckDB, with :date_from and :date_to for the date range."""
    return expand(source(name))


def deployed(sql: str) -> str:
    """A query as the dashboard file holds it: the date range is AI/BI's one parameter, dates."""
    return sql.replace(":date_from", ":dates.min").replace(":date_to", ":dates.max")


def parameters(sql: str) -> list[str]:
    """The parameters a query reads, in PARAMETERS' order, with date_from and date_to as one range, dates."""
    found = set(PLACEHOLDER.findall(sql))
    names = [name for name in PARAMETERS if name in found]
    if "date_from" in names or "date_to" in names:
        names = [name for name in names if name not in ("date_from", "date_to")] + ["dates"]
    return names


def _parameter(name: str, today: dt.date) -> dict:
    if name == "measure_date":  # the page starts at today: AI/BI writes a dynamic date as "now", rounded to the day
        return {"displayName": name, "keyword": name, "dataType": "DATE",
                "defaultSelection": {"values": {"dataType": "DATE", "values": [{"value": "now/d"}]}}}
    if name == "dates":  # the last 90 days (the 45 brief, decision 11)
        return {"displayName": name, "keyword": name, "dataType": "DATE", "complexType": "RANGE",
                "defaultSelection": {"range": {"dataType": "DATE", "min": {"value": "now-90d/d"},
                                               "max": {"value": "now/d"}}}}
    # budget_period: empty means the current period, the newest the latest cost pull wrote; run_id: empty means the
    # latest answer run. So the file never names a day, and a deploy on any day shows today's period.
    return {"displayName": name, "keyword": name, "dataType": "STRING",
            "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": ""}]}}}


# ── Tiles ────────────────────────────────────────────────────────────────

def _frame(title: str, about: str) -> dict:
    return {"showTitle": True, "title": title, "showDescription": True, "description": about}


def _fields(*names: str) -> list[dict]:
    return [{"name": name, "expression": f"`{name}`"} for name in names]


def _main(dataset: str, *fields: str) -> list[dict]:
    return [{"name": "main_query", "query": {"datasetName": dataset, "fields": _fields(*fields), "disaggregated": True}}]


def _number(decimals: int) -> dict:
    return {"type": "number-plain", "abbreviation": "none", "decimalPlaces": {"type": "exact" if decimals else "max",
                                                                               "places": decimals},
            "hideGroupSeparator": False}


def _text(name: str, lines: list[str]) -> dict:
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": lines}}}


def _table(tile: kinds.Table) -> dict:
    columns = []
    for order, column in enumerate(tile.columns):
        entry = {"fieldName": column.field, "title": words(column.title, tile.fewest), "type": column.kind,
                 "displayAs": "datetime" if column.kind in ("date", "datetime") else column.kind, "order": order}
        if column.kind == "date":
            entry["dateTimeFormat"] = "MMM D, YYYY"
        if column.kind == "datetime":
            entry["dateTimeFormat"] = "MMM D, YYYY HH:mm"
        if column.decimals is not None:
            entry["numberFormat"] = _number(column.decimals)
        columns.append(entry)
    return {"widget": {"name": tile.name, "queries": _main(tile.dataset, *(column.field for column in tile.columns)),
                       "spec": {"version": 1, "widgetType": "table", "encodings": {"columns": columns},
                                "frame": _frame(words(tile.title, tile.fewest), words(tile.about, tile.fewest))}}}


def _axis(axis: kinds.Axis) -> dict:
    encoding = {"fieldName": axis.field, "displayName": words(axis.title),
                "scale": {"type": axis.scale}}
    if axis.scale == "categorical":
        encoding["scale"]["sort"] = {"by": "natural-order"}
    if axis.scale == "quantitative":
        if axis.domain:
            encoding["scale"]["domain"] = {"min": axis.domain[0], "max": axis.domain[1]}
        encoding["format"] = _number(axis.decimals)
    return encoding


def _chart(tile: kinds.Chart) -> dict:
    x, y = _axis(tile.x), _axis(tile.y)
    fields = [tile.x.field, tile.y.field]
    encodings: dict = {"x": x, "y": y}
    series = tile.series
    colors = [COLORS[0]]
    if series and series.fields:  # each series is a column of its own
        value_axis = "x" if tile.horizontal else "y"
        encodings[value_axis] = {**encodings[value_axis], "fields": [
            {"fieldName": field, "displayName": words(title)} for field, title, _ in series.fields]}
        encodings[value_axis].pop("fieldName", None)
        encodings[value_axis].pop("displayName", None)
        encodings["color"] = {"scale": {"type": "categorical", "mappings": [
            {"value": words(title), "color": color} for _, title, color in series.fields]}}
        fields = [tile.x.field if tile.horizontal is False else tile.y.field,
                  *(field for field, _, _ in series.fields)]
        colors = [color for _, _, color in series.fields]
    elif series:  # each series is a value of one column
        encodings["color"] = {"fieldName": series.field, "displayName": words(series.title), "scale": {
            "type": "categorical", "mappings": [{"value": words(value), "color": color}
                                                for value, color in series.values]}}
        fields.append(series.field)
        colors = [color for _, color in series.values]
    if tile.labels:
        encodings["label"] = {"show": True}
    if tile.tooltip:
        encodings["extra"] = [{"fieldName": field} for field in tile.tooltip]
        fields += list(tile.tooltip)
    spec = {"version": 3, "widgetType": tile.mark, "encodings": encodings,
            "frame": _frame(words(tile.title, tile.fewest), words(tile.about, tile.fewest)),
            "mark": {"colors": colors}}
    if tile.stacked:
        spec["mark"]["layout"] = "stack"
    elif series and series.fields and tile.mark == "bar":
        spec["mark"]["layout"] = "group"
    return {"widget": {"name": tile.name, "queries": _main(tile.dataset, *dict.fromkeys(fields)), "spec": spec}}


def _pivot(tile: kinds.Pivot) -> dict:
    return {"widget": {"name": tile.name, "queries": _main(tile.dataset, tile.rows[0], tile.columns[0], tile.cell[0]),
                       "spec": {"version": 3, "widgetType": "pivot", "encodings": {
                           "rows": [{"fieldName": tile.rows[0], "displayName": words(tile.rows[1])}],
                           "columns": [{"fieldName": tile.columns[0], "displayName": words(tile.columns[1])}],
                           "cell": {"type": "multi-cell", "fields": [
                               {"fieldName": tile.cell[0], "cellType": "text", "displayName": words(tile.cell[1])}]}},
                           "frame": _frame(words(tile.title), words(tile.about))}}}


def _counter(tile: kinds.Counter) -> dict:
    """A KPI as AI/BI's counter: the display string as it is, and no target, delta or arrow (the 45 brief, 4.1)."""
    name, definition, _ = load_kpis()[tile.kpi].copy_keys
    dataset = f"kpi_{tile.kpi}"
    return {"widget": {"name": tile.name, "queries": _main(dataset, "display"), "spec": {
        "version": 2, "widgetType": "counter",
        "encodings": {"value": {"fieldName": "display", "displayName": words(name)}},
        "frame": _frame(words(name), words(definition))}}}


def _findings(tile: kinds.Findings) -> dict:
    return _table(kinds.Table(tile.name, f"findings_{tile.page}", (
        kinds.Column("about", "dash.findings.aboutColumn"), kinds.Column("finding", "dash.findings.finding"),
        kinds.Column("measured", "dash.findings.measured")), "dash.findings.title", "dash.findings.about"))


def _definitions(tile: kinds.Definitions) -> dict:
    """What each indicator measures, generated from the KPI registry in loop order (the 45 brief, tile 20)."""
    lines = [words(tile.intro) + "\n"]
    for kpi in load_kpis().values():
        if kpi.loop:
            name, definition, _ = kpi.copy_keys
            lines.append(f"- **{words(name)}.** {words(definition)}\n")
    return _text(tile.name, lines)


def _filter(tile: kinds.Filter, datasets: list[str]) -> dict:
    """A filter sets its parameter on every dataset of its page whose query reads it."""
    parameter = tile.parameter
    queries = [{"name": f"parameter_{dataset}", "query": {"datasetName": dataset, "parameters": [
        {"name": parameter, "keyword": parameter}], "disaggregated": False}} for dataset in datasets]
    fields = [{"parameterName": parameter, "queryName": entry["name"]} for entry in queries]
    widget = {"date": "filter-date-picker", "dates": "filter-date-range-picker", "select": "filter-single-select",
              "text": "filter-text-entry"}[tile.kind]
    if tile.kind == "select":
        queries.append({"name": "values", "query": {"datasetName": tile.values, "fields": _fields(
            tile.value_field, tile.label_field), "disaggregated": False}})
        fields.append({"fieldName": tile.value_field, "displayName": words(tile.title), "queryName": "values"})
    return {"widget": {"name": tile.name, "queries": queries, "spec": {
        "version": 2, "widgetType": widget, "encodings": {"fields": fields},
        "frame": _frame(words(tile.title), words(tile.about))}}}


def notes_lines(page: Page) -> list[str]:
    """The notes that end every page (the 45 brief, section 3.3): the source, the 20-case note and the footer."""
    return [f"**{words('dash.sourceLabel')}** {words(page.notes)}\n",
            f"**{words('dash.noteLabel')}** {words('dash.note', 'data_readiness.fewest_for_a_share')}\n",
            wording.words()["footer"]]


# ── Pages ────────────────────────────────────────────────────────────────

def dataset_of(tile) -> list[str]:
    """The datasets a tile reads."""
    if isinstance(tile, kinds.QueryHistory):
        return []
    if isinstance(tile, (kinds.Table, kinds.Chart, kinds.Pivot)):
        return [tile.dataset]
    if isinstance(tile, kinds.Counter):
        return [f"kpi_{tile.kpi}"]
    if isinstance(tile, kinds.Findings):
        return [f"findings_{tile.page}"]
    if isinstance(tile, kinds.Filter) and tile.values:
        return [tile.values]
    return []


def _tiles(page: Page, query_history: bool) -> list:
    """The page's tiles with the query history settled: its table where it can be read."""
    found = []
    for tile in page.tiles:
        if isinstance(tile, kinds.QueryHistory):
            found.append(tile.table if query_history else tile)
        else:
            found.append(tile)
    return found


def page_datasets(page: Page, query_history: bool = True) -> list[str]:
    """Every dataset a page reads, in the order its tiles first read them."""
    return list(dict.fromkeys(name for tile in _tiles(page, query_history) for name in dataset_of(tile)))


def place(sizes: list[tuple[int, int]]) -> list[dict]:
    """Each tile's position on the grid, in reading order: left to right, then down, a new row when the next tile
    doesn't fit, never moving a tile up to fill a gap (the 45 brief, sections 3.2 and 10)."""
    found, x, y, row = [], 0, 0, 0
    for width, height in sizes:
        if x + width > GRID:
            x, y, row = 0, y + row, 0
        found.append({"x": x, "y": y, "width": width, "height": height})
        x, row = x + width, max(row, height)
    return found


def _widget(tile, page: Page, test: bool, today: dt.date, query_history: bool) -> dict:
    if isinstance(tile, kinds.Text):
        lines = []
        for key in tile.lines:
            level, _, key = key.rpartition(" ")
            lines.append(f"{level} {words(key, tile.fewest)}\n" if level else words(key, tile.fewest) + "\n")
        if test and lines and lines[0].startswith("## "):  # the test copy says so first (the 45 brief, section 9.6)
            lines.insert(1, words("dash.testLine") + "\n")
        lines[-1] = lines[-1].rstrip("\n")
        return _text(tile.name, lines)
    if isinstance(tile, kinds.QueryHistory):
        return _text(tile.table.name, [wording.fill(words(tile.unreadable), date=wording.long_day(today))])
    if isinstance(tile, kinds.Filter):
        reading = [name for name in page_datasets(page, query_history)
                   if tile.parameter in parameters(query(name))]
        return _filter(tile, reading)
    return {kinds.Table: _table, kinds.Chart: _chart, kinds.Pivot: _pivot, kinds.Counter: _counter,
            kinds.Findings: _findings, kinds.Definitions: _definitions}[type(tile)](tile)


def render_page(page: Page, test: bool = False, today: dt.date | None = None, query_history: bool = True) -> dict:
    today = today or dt.date.today()
    found = [_widget(tile, page, test, today, query_history) for tile in _tiles(page, query_history)]
    found.append(_text("notes" if page.key == "data_readiness" else f"{page.key}_notes", notes_lines(page)))
    sizes = [(tile.table.width, 2) if isinstance(tile, kinds.QueryHistory) else (tile.width, tile.height)
             for tile in _tiles(page, query_history)] + [(GRID, 2)]
    for widget, position in zip(found, place(sizes)):
        widget["position"] = position
    return {"name": page.key, "displayName": words(page.name), "pageType": "PAGE_TYPE_CANVAS", "layout": found}


def _display_name(name: str, pages: tuple[Page, ...]) -> str:
    """What AI/BI's data panel calls a dataset: the title of the first tile that reads it."""
    for page in pages:
        for tile in page.tiles:
            if name in dataset_of(tile):
                if isinstance(tile, kinds.Counter):
                    return words(load_kpis()[tile.kpi].copy_keys[0])
                if isinstance(tile, kinds.Findings):
                    return words("dash.findings.title")
                if isinstance(tile, kinds.Filter):
                    return words(tile.title)
                return words(tile.title, getattr(tile, "fewest", None))
    if name.startswith("readiness_") or name in ("award_rows_by_year", "rows_by_year"):
        return words(f"readiness.datasets.{name}")
    return name


def render(pages: tuple[Page, ...], test: bool = False, today: dt.date | None = None,
           query_history: bool = True) -> dict:
    """The whole dashboard as an AI/BI dashboard file holds it. test writes the test copy, whose introductions say
    so; query_history says whether the workspace lets Strata read its query history (the 45 brief, section 6.4)."""
    today = today or dt.date.today()
    names = list(dict.fromkeys(name for page in pages for name in page_datasets(page, query_history)))
    datasets = []
    for name in names:
        sql = deployed(query(name))
        datasets.append({"name": name, "displayName": _display_name(name, pages),
                         "queryLines": [line + "\n" for line in sql.splitlines()],
                         **({"parameters": [_parameter(parameter, today) for parameter in parameters(query(name))]}
                            if parameters(query(name)) else {})})
    return {"datasets": datasets,
            "pages": [render_page(page, test, today, query_history) for page in pages],
            "uiSettings": {"theme": THEME}}
