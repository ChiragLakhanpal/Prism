"""Strata's AI/BI dashboard, defined in code (the spec's tenth single place; docs/PLAN.md section 9).

This module is the one definition of the dashboard's pages and tiles. It writes them as an AI/BI
dashboard file, bundle/dashboards/strata.lvdash.json, which bundle/dashboard.yml declares, so the
bundle's one deploy command (ops/bundle/deploy.py) deploys it with the catalog and the job. The gate
checks that the file says what this module says, and runs every dataset's query on the fixture.

Ticket 16 builds the first page, Data readiness (the 16 design brief, section 10). Its queries read
only strata.ops and strata.gold: the day's headline, statuses and fixes come from
strata.ops.readiness_snapshot, which the measure run writes with the same function as the app's page
(strata.dashboard.snapshot), and the rows per fiscal year come from gold. Every dataset takes the
measure_date parameter, so one date filter sets the whole page. The words are copy.dataReadiness.server
.dashboard in web/src/copy.ts, which the copy lint checks.

Write the file again after changing this module or the words:

    uv run --frozen python -m strata.dashboard --write
"""

from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

from strata.config import load_thresholds
from strata.tools.data_readiness_for import words

FILE = Path(__file__).resolve().parents[3] / "bundle" / "dashboards" / "strata.lvdash.json"
PARAMETER = "measure_date"
# DESIGN.md section 6: the categorical colors in order, with the text variants for cat1, cat2, cat4
# and cat9, because bars are essential marks and those four fall below 3:1 on white.
COLORS = ("#106ca1", "#b65f0c", "#664ab6", "#208383", "#f3578e", "#081079", "#0c7c68", "#aa0000", "#767712")
SINGLE = COLORS[0]  # a single-series chart separates nothing by color
# The parameters that name tile 4's datasets, in the order their colors are given. Their values are
# copy.dataReadiness.server.dashboard.labels.
AWARD_LABELS = ("awards_label", "fy2001_label", "notices_awards_label")
LABEL = re.compile(r":(\w+_label)\b")
# Each dataset: its name, the file of its query in sql/, and what it is.
DATASETS = (
    ("readiness_headline", "The day's headline"),
    ("award_rows_by_year", "Contract-award rows per fiscal year"),
    ("rows_by_year", "Rows per fiscal year, by source"),
    ("readiness_links", "Shares of rows that link"),
    ("readiness_routes", "Shares of pages read well"),
    ("readiness_sources", "Freshness and link counts"),
    ("readiness_fixes", "Fixes"),
)


def _query(name: str) -> str:
    return (resources.files("strata.dashboard") / "sql" / f"{name}.sql").read_text()


def query(name: str) -> str:
    """A dataset's query as the dashboard runs it, without its comment lines."""
    return "\n".join(line for line in _query(name).splitlines() if not line.lstrip().startswith("--")).strip()


def labels(name: str) -> dict[str, str]:
    """The row names a dataset's query takes as parameters, from the copy file."""
    given = words()["dashboard"]["labels"]
    return {label: given[label] for label in dict.fromkeys(LABEL.findall(query(name)))}


def award_datasets() -> tuple[str, ...]:
    """Tile 4's datasets by name, in the order their colors are given."""
    return tuple(words()["dashboard"]["labels"][label] for label in AWARD_LABELS)


def _fewest(text: str) -> str:
    """A description with the fewest rows a share is charted from, as the thresholds file says."""
    return text.replace("{fewest}", str(load_thresholds().value("data_readiness.fewest_for_a_percentage")))


def _dataset(name: str, about: str) -> dict:
    return {
        "name": name,
        "displayName": about,
        "queryLines": [line + "\n" for line in query(name).splitlines()],
        # The page starts at today: AI/BI writes a dynamic date as "now", rounded to the day. Row
        # names are fixed text parameters, so the words stay in the copy file.
        "parameters": [{"displayName": PARAMETER, "keyword": PARAMETER, "dataType": "DATE",
                        "defaultSelection": {"values": {"dataType": "DATE", "values": [{"value": "now/d"}]}}},
                       *({"displayName": label, "keyword": label, "dataType": "STRING",
                          "defaultSelection": {"values": {"dataType": "STRING", "values": [{"value": value}]}}}
                         for label, value in labels(name).items())],
    }


def _frame(title: str, about: str) -> dict:
    return {"showTitle": True, "title": title, "showDescription": True, "description": about}


def _fields(*names: str) -> list[dict]:
    return [{"name": name, "expression": f"`{name}`"} for name in names]


def _main(dataset: str, *fields: str) -> list[dict]:
    return [{"name": "main_query", "query": {"datasetName": dataset, "fields": _fields(*fields), "disaggregated": True}}]


def _at(x: int, y: int, width: int, height: int) -> dict:
    return {"x": x, "y": y, "width": width, "height": height}


def _text(name: str, lines: list[str], position: dict) -> dict:
    return {"widget": {"name": name, "multilineTextboxSpec": {"lines": lines}}, "position": position}


def _table(name: str, dataset: str, columns: list[tuple[str, str, str]], title: str, about: str,
           position: dict) -> dict:
    """A table: each column as (field, title, type), type string, number, integer or date."""
    return {"widget": {"name": name, "queries": _main(dataset, *(field for field, _, _ in columns)), "spec": {
        "version": 1, "widgetType": "table",
        "encodings": {"columns": [{"fieldName": field, "title": heading, "type": kind,
                                   "displayAs": "datetime" if kind == "date" else kind, "order": order,
                                   **({"dateTimeFormat": "MMM D, YYYY"} if kind == "date" else {})}
                                  for order, (field, heading, kind) in enumerate(columns)]},
        "frame": _frame(title, about)}}, "position": position}


def _bars(name: str, dataset: str, category: tuple[str, str], value: tuple[str, str], title: str, about: str,
          position: dict, horizontal: bool = False, color: tuple[str, str] | None = None,
          domain: tuple[int, int] | None = None, tooltip: tuple[str, ...] = ()) -> dict:
    category_encoding = {"fieldName": category[0], "displayName": category[1],
                         "scale": {"type": "categorical", "sort": {"by": "natural-order"}}}
    value_encoding = {"fieldName": value[0], "displayName": value[1],
                      "scale": {"type": "quantitative", **({"domain": {"min": domain[0], "max": domain[1]}}
                                                           if domain else {})},
                      "format": {"type": "number-plain", "abbreviation": "none",
                                 "decimalPlaces": {"type": "max", "places": 0}, "hideGroupSeparator": False}}
    encodings = {"x": value_encoding, "y": category_encoding} if horizontal else {"x": category_encoding,
                                                                                   "y": value_encoding}
    if color:
        encodings["color"] = {"fieldName": color[0], "displayName": color[1], "scale": {
            "type": "categorical", "mappings": [{"value": value_name, "color": shade}
                                                for value_name, shade in zip(award_datasets(), COLORS)]}}
    else:
        encodings["label"] = {"show": True}
    if tooltip:
        encodings["extra"] = [{"fieldName": field} for field in tooltip]
    fields = [category[0], value[0], *([color[0]] if color else []), *tooltip]
    spec = {"version": 3, "widgetType": "bar", "encodings": encodings, "frame": _frame(title, about),
            "mark": {"colors": [SINGLE] if not color else list(COLORS[:len(AWARD_LABELS)])}}
    return {"widget": {"name": name, "queries": _main(dataset, *fields), "spec": spec}, "position": position}


def _date_filter(name: str, title: str, about: str, position: dict) -> dict:
    """One date for the whole page: the measure_date parameter of every dataset."""
    queries = [{"name": f"parameter_{dataset}", "query": {"datasetName": dataset, "parameters": [
        {"name": PARAMETER, "keyword": PARAMETER}], "disaggregated": False}} for dataset, _ in DATASETS]
    return {"widget": {"name": name, "queries": queries, "spec": {
        "version": 2, "widgetType": "filter-date-picker",
        "encodings": {"fields": [{"parameterName": PARAMETER, "queryName": entry["name"]} for entry in queries]},
        "frame": _frame(title, about)}}, "position": position}


def data_readiness_page() -> dict:
    """The page's ten tiles, in the brief's order, on AI/BI's six-column grid."""
    say = words()["dashboard"]
    return {"name": "data_readiness", "displayName": say["page"], "pageType": "PAGE_TYPE_CANVAS", "layout": [
        _text("introduction", [f"## {say['introHeading']}\n", say["intro"]], _at(0, 0, 6, 2)),
        _date_filter("measure_date", say["measureDate"], say["measureDateAbout"], _at(0, 2, 2, 1)),
        _table("headline", "readiness_headline", [("measured_on", say["measuredOn"], "date"),
                                                  ("headline", say["headlineColumn"], "string")],
               say["headline"], say["headlineAbout"], _at(0, 3, 6, 2)),
        _bars("award_rows", "award_rows_by_year", ("fiscal_year_label", say["fiscalYear"]),
              ("award_rows", say["rows"]), say["awardRows"], say["awardRowsAbout"], _at(0, 5, 6, 6),
              color=("dataset", say["dataset"])),
        {"widget": {"name": "source_rows", "queries": _main("rows_by_year", "source", "fiscal_year_label",
                                                             "source_rows"), "spec": {
            "version": 3, "widgetType": "pivot",
            "encodings": {"rows": [{"fieldName": "source", "displayName": say["source"]}],
                          "columns": [{"fieldName": "fiscal_year_label", "displayName": say["fiscalYear"]}],
                          "cell": {"type": "multi-cell", "fields": [
                              {"fieldName": "source_rows", "cellType": "text", "displayName": say["rows"]}]}},
            "frame": _frame(say["sourceRows"], say["sourceRowsAbout"])}}, "position": _at(0, 11, 6, 6)},
        _bars("links", "readiness_links", ("link", say["link"]), ("share_percent", say["share"]), say["links"],
              _fewest(say["linksAbout"]), _at(0, 17, 3, 6), horizontal=True, domain=(0, 100),
              tooltip=("count", "denominator")),
        _bars("routes", "readiness_routes", ("route", say["route"]), ("share_percent", say["share"]), say["routes"],
              _fewest(say["routesAbout"]), _at(3, 17, 3, 6), horizontal=True, domain=(0, 100),
              tooltip=("count", "denominator")),
        _table("freshness", "readiness_sources", [
            ("source", say["source"], "string"), ("latest_data", say["latestData"], "date"),
            ("updates", say["updates"], "string"), ("days_late", say["daysLate"], "integer"),
            ("linked", say["linked"], "string"), ("status", say["status"], "string")],
            say["freshness"], say["freshnessAbout"], _at(0, 23, 6, 7)),
        _table("fixes", "readiness_fixes", [("rank", say["rank"], "integer"), ("fix", say["fix"], "string"),
                                            ("projects", say["projects"], "integer")],
               say["fixes"], say["fixesAbout"], _at(0, 30, 6, 5)),
        _text("notes", [say["notes"] + "\n", words()["footer"]], _at(0, 35, 6, 2)),
    ]}


def dashboard() -> dict:
    """The whole dashboard, as an AI/BI dashboard file holds it."""
    return {"datasets": [_dataset(name, about) for name, about in DATASETS], "pages": [data_readiness_page()]}


def written() -> str:
    return json.dumps(dashboard(), indent=2, ensure_ascii=False) + "\n"
