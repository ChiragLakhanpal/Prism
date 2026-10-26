"""Every widget the dashboard writer produces has a shape AI/BI's own dashboards carry (ticket 68).

The deployed "Strata operations" showed "Invalid widget definition is imported." on some tiles on October 25, 2026.
tests/fixtures/dashboard/widget_shapes.json holds known-good widgets by kind, each copied from a dashboard file that
Databricks publishes or that a workspace's dashboard editor exported, with its repository, commit and path named.
Here every widget strata.dashboard writes, on every page of "Strata operations" and its test copy, with and without
the query history, is checked against its kind: the version for its widget type, the fields every known-good widget
of its kind carries, and no field or value that no known-good widget of its kind carries.
"""

import datetime as dt
import json
import re
from collections import Counter
from functools import cache
from pathlib import Path

import pytest

from strata import dashboard
from strata.lakehouse.engine import DuckDBEngine

ROOT = Path(__file__).resolve().parents[1]
SHAPES = json.loads((ROOT / "tests" / "fixtures" / "dashboard" / "widget_shapes.json").read_text())
KINDS = SHAPES["kinds"]
SHARED = tuple(SHAPES["sharedObjects"])  # format, frame and scale: one shape wherever they sit
ENUM_KEYS = tuple(SHAPES["enumKeys"])
DAY = dt.date(2026, 10, 23)  # the day the fixture's sources were measured (tests/test_dashboard.py)


def kind_of(widget: dict) -> str | None:
    if "multilineTextboxSpec" in widget:
        return "text"
    widget_type = widget.get("spec", {}).get("widgetType")
    return next((name for name, kind in KINDS.items() if widget_type in kind["widgetTypes"]), None)


def fields(value, path: str = "") -> set[str]:
    """A widget's key paths, a list's items written [], each format, frame or scale starting a path of its own, and
    path=value for each word at an enum key, such as spec.widgetType=table or format.type=number-plain."""
    found = set()
    if isinstance(value, dict):
        for key, item in value.items():
            here = key if key in SHARED else (f"{path}.{key}" if path else key)
            found.add(here)
            if key in ENUM_KEYS and isinstance(item, str):
                found.add(f"{here}={item}")
            found |= fields(item, here)
    elif isinstance(value, list):
        for item in value:
            found |= fields(item, path + "[]")
    return found


def holds(value, path: str, expected=...) -> bool:
    """Whether the widget has the field at path, in every item of each list on the way, equal to expected if given."""
    if not path:
        return expected is ... or value == expected
    head, _, rest = path.partition(".")
    key = head.removesuffix("[]")
    if not isinstance(value, dict) or key not in value:
        return False
    if head.endswith("[]"):
        return isinstance(value[key], list) and bool(value[key]) and all(holds(item, rest, expected)
                                                                       for item in value[key])
    return holds(value[key], rest, expected)


def is_shared(name: str) -> bool:
    return re.split(r"[.=\[]", name)[0] in SHARED


@cache
def known_good() -> dict[str, set[str]]:
    """Each kind's fields, from its examples, and under "shared" every example's format, frame and scale fields."""
    found = {"shared": set()}
    for name, kind in KINDS.items():
        found[name] = set()
        for example in kind["examples"]:
            own = fields(example["widget"])
            found[name] |= own
            found["shared"] |= {field for field in own if is_shared(field)}
    return found


def problems(widget: dict, kind: str) -> list[str]:
    """What keeps a widget from its kind's known-good shape, in words."""
    shape, found = KINDS[kind], []
    widget_type = widget.get("spec", {}).get("widgetType")
    if widget_type and widget["spec"].get("version") != shape["widgetTypes"][widget_type]:
        found.append(f"{widget_type} is version {widget['spec'].get('version')}, but known-good {widget_type} "
                     f"widgets are version {shape['widgetTypes'][widget_type]}")
    found += [f"lacks {path}" for path in shape["required"] if not holds(widget, path)]
    found += [f"{path} is not {expected}" for path, expected in shape["equals"].items()
              if not holds(widget, path, expected)]
    allowed = known_good()[kind] | known_good()["shared"]
    found += [f"carries {field}, which no known-good {kind} widget carries"
              for field in sorted(fields(widget) - allowed)]
    return found


@cache
def written() -> tuple[tuple[str, dict], ...]:
    """Every widget the writer produces: the dashboard and its test copy, with the query history and without it."""
    return tuple((f"{'test copy, ' if test else ''}{page['name']}", tile["widget"])
                 for test in (False, True) for history in (True, False)
                 for page in dashboard.dashboard(test, history)["pages"] for tile in page["layout"])


def test_every_widget_the_writer_produces_is_a_kind_the_known_good_widgets_show():
    unknown = [(page, widget["name"], widget.get("spec", {}).get("widgetType")) for page, widget in written()
               if kind_of(widget) is None]

    assert unknown == []


@pytest.mark.parametrize("kind", sorted(KINDS))
def test_each_widget_has_its_kind_s_version_and_required_fields_and_no_field_known_good_widgets_lack(kind):
    found = {f"{page}: {widget['name']}": problems(widget, kind) for page, widget in written()
             if kind_of(widget) == kind}

    assert found, f"the writer produces no {kind} widget, so the fixture's {kind} entry can go"
    assert {name: issues for name, issues in found.items() if issues} == {}


def test_every_known_good_widget_names_its_source_and_carries_its_kind_s_required_fields():
    """The required fields are the ones every example of a kind carries, so the test above asks for nothing that
    AI/BI's own dashboards leave out."""
    for name, kind in KINDS.items():
        assert kind["examples"], name
        for example in kind["examples"]:
            source = SHAPES["sources"][example["source"]]
            assert source["repository"] and re.fullmatch(r"[0-9a-f]{40}", source["commit"]) and source["path"]
            assert problems(example["widget"], name) == [], (name, example["source"], example["widget"]["name"])


def test_the_pivot_of_rows_per_fiscal_year_sums_one_row_per_cell_so_each_cell_is_the_snapshot_s_count(fixture_db):
    """AI/BI's pivot aggregates its cells, as every known-good pivot does. Each source and fiscal year is one row of
    the snapshot, so the sum in a cell is that row's count, a number the measure run wrote (CLAUDE.md rule 1)."""
    [pivot] = [tile["widget"] for tile in dashboard.dashboard()["pages"][0]["layout"]
               if tile["widget"]["name"] == "source_rows"]
    query = pivot["queries"][0]["query"]
    rows, columns = (encoding["fieldName"] for encoding in (pivot["spec"]["encodings"]["rows"][0],
                                                            pivot["spec"]["encodings"]["columns"][0]))
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        result = engine.run(dashboard.query(query["datasetName"]), {dashboard.PARAMETER: DAY})
    cells = Counter((row[result.columns.index(rows)], row[result.columns.index(columns)]) for row in result.rows)

    assert [field["expression"] for field in query["fields"]] == [f"`{rows}`", f"`{columns}`", "SUM(`source_rows`)"]
    assert cells and set(cells.values()) == {1}
