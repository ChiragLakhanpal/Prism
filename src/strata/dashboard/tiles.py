"""The kinds of tile the dashboard definition is written in (ticket 45; the 45 design brief, sections 3 and 4).

Each tile names its data (a KPI from config/kpis.toml, or a dataset whose query is sql/<name>.sql), its form, its
width and height on AI/BI's six-column grid, and the copy keys of its words. The renderer places tiles in reading
order, left to right and then down, so adding or removing a tile is one entry and moves no other
(strata.dashboard.render).

A copy key is a dotted path: dash.* and kpi.* are copy.dash and copy.kpi in web/src/copy.ts (src/strata/dashboard/
copy.json); readiness.* is the Data readiness page's words, copy.dataReadiness.server.dashboard (ticket 16).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# DESIGN.md section 6: the categorical colors in order, with the text variants for cat1, cat2, cat4 and cat9, because
# bars and lines are essential marks and those four fall below 3:1 on white (the 45 brief, section 8.1).
COLORS = ("#106ca1", "#b65f0c", "#664ab6", "#208383", "#f3578e", "#081079", "#0c7c68", "#aa0000", "#767712")
FIRST, SECOND = COLORS[0], COLORS[1]  # one series is #106ca1 alone; two are #106ca1 then #b65f0c (section 8.2)
REFERENCE = "#8a969f"  # DESIGN.md section 6's reference grey: a budget line or a target edge, never data
FAILED = "#c91c25"  # the one state color on the dashboard: a failed quality check (section 8.2)
PASSED = REFERENCE  # passes recede, so failures carry the color


@dataclass(frozen=True)
class Text:
    """A Markdown text tile. Each line is a copy key; a key after "## " or "### " is a heading of that level."""

    name: str
    lines: tuple[str, ...]
    width: int = 6
    height: int = 2
    fewest: str | None = None  # the thresholds value a {fewest} in the words is filled from


@dataclass(frozen=True)
class Filter:
    """A page filter: one date (date), a date range (dates), one value from a list (select) or typed text (text).
    It sets the parameter of every dataset on its page whose query reads it."""

    name: str
    kind: str
    parameter: str
    title: str
    about: str
    width: int = 2
    height: int = 1
    values: str | None = None  # select: the dataset that lists its values
    value_field: str | None = None  # select: the field that holds each value
    label_field: str | None = None  # select: the field that holds each value's words


@dataclass(frozen=True)
class Column:
    """A table column: the query's field, the copy key of its heading, and its type (string, integer, number, date
    or datetime). decimals sets a number's decimals; a date shows as "Oct 22, 2026"."""

    field: str
    title: str
    kind: str = "string"
    decimals: int | None = None


@dataclass(frozen=True)
class Table:
    name: str
    dataset: str
    columns: tuple[Column, ...]
    title: str
    about: str
    width: int = 6
    height: int = 6
    fewest: str | None = None


@dataclass(frozen=True)
class Counter:
    """A KPI tile: AI/BI's counter, showing the KPI query's display string, with no target, delta or arrow. Its title
    is kpi.<id>.name and its description kpi.<id>.definition."""

    name: str
    kpi: str
    width: int = 2
    height: int = 3


@dataclass(frozen=True)
class Findings:
    """What the measures say: the sentences the nightly job wrote for the page, one row per section."""

    name: str
    page: str  # governance or ai
    width: int = 6
    height: int = 4


@dataclass(frozen=True)
class Series:
    """A chart's series. By value: field holds each row's series, and each (value copy key, color) maps one value to
    its color, so a filter that removes a series never repaints the others. By field: each (field, copy key, color)
    is a series of its own, for a chart whose series are columns, such as a running total beside its budget."""

    field: str | None = None
    title: str | None = None
    values: tuple[tuple[str, str], ...] = ()
    fields: tuple[tuple[str, str, str], ...] = ()


@dataclass(frozen=True)
class Axis:
    field: str
    title: str
    scale: str = "categorical"  # categorical, temporal or quantitative
    domain: tuple[float, float] | None = None
    decimals: int = 0


@dataclass(frozen=True)
class Chart:
    """A bar, line or scatter chart. A horizontal bar puts its categories on y. labels shows each mark's value."""

    name: str
    mark: str  # bar, line or scatter
    dataset: str
    x: Axis
    y: Axis
    title: str
    about: str
    width: int = 6
    height: int = 6
    series: Series | None = None
    horizontal: bool = False
    stacked: bool = False
    labels: bool = False
    tooltip: tuple[str, ...] = ()
    fewest: str | None = None


@dataclass(frozen=True)
class Pivot:
    """Ticket 16's table of rows per fiscal year: rows by one field, columns by another, a count in each cell."""

    name: str
    dataset: str
    rows: tuple[str, str]
    columns: tuple[str, str]
    cell: tuple[str, str]
    title: str
    about: str
    width: int = 6
    height: int = 6


@dataclass(frozen=True)
class Definitions:
    """A text tile generated from the KPI registry: each loop indicator's name in bold and its definition."""

    name: str
    intro: str
    width: int = 6
    height: int = 5


@dataclass(frozen=True)
class QueryHistory:
    """Who queried what (the 45 brief, tile 21): the table of queries where the workspace lets Strata read its query
    history, or a dated text tile saying it doesn't (section 6.4)."""

    table: Table
    unreadable: str  # the copy key of the text tile, with {date} the day the dashboard was written

    @property
    def name(self) -> str:
        return self.table.name


@dataclass(frozen=True)
class Page:
    key: str
    name: str  # copy key
    tiles: tuple = field(default_factory=tuple)
    notes: str | None = None  # the copy key of its source sentence; the notes tile ends every page
