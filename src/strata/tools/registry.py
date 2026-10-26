"""The tool registry at work: every tool is called here, by name, as the viewer (spec, seam 2).

config/tools.toml defines each tool once (spec, "Ten single places", item 2) and
strata.config.load_tools() reads it. This module does three things with those definitions:

- agent_tools() is the agent's tool list: one function tool per entry, in the Responses API's
  shape, so adding a tool is one entry in the file. A value of the thresholds file named in braces
  in a description, such as {passages.results}, is filled in from that file.
- call() runs a tool by name. It checks the arguments against the tool's parameters, settles
  the as-of date (the earlier of the call's and the page's, else today), runs the adapter with
  the viewer's engine, and wraps the result in the envelope every tool shares.
- A tool that declares summary_fields gets one more citable record, its summary: those fields,
  with an evidence id that names the tool, its arguments and the as-of date. The derived figures in
  them, such as a past range or a count, can then be cited and checked like a row's values
  (CLAUDE.md rule 1; spec, "a derived figure the agent needs is returned as a column").
- A tool that declares nested_rows returns records inside its rows, such as each side of a
  disagreement, and each of them is cited and dated like a row, so the answer loop can keep it.
- It then checks the result against seam 2's contract and the tool's declared shape: every row
  has an evidence id, a public date on or before the as-of date and a source line, and every
  reason code and abstention reason is one the file lists. A tool that breaks the contract raises
  ToolContractError, so a test catches it before a viewer does.
"""

from __future__ import annotations

import datetime as dt
import functools
import importlib
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

from strata.config import Thresholds, Tool, ToolParameter, load_thresholds, load_tools
from strata.dbx import Viewer
from strata.lakehouse.engine import Engine

JSON_TYPES = {
    "string": {"type": "string"},
    "date": {"type": "string", "format": "date"},
    "integer": {"type": "integer"},
    "number": {"type": "number"},
    "boolean": {"type": "boolean"},
}
VIEWS = ("staff", "piu", "public")  # World Bank staff, an implementing agency officer, the public
ENVELOPE = ("tool", "as_of", "view", "rows", "coverage", "abstention")
COVERAGE = ("matched", "used", "not_used")


class ToolError(ValueError):
    """A call the registry refuses: an unknown tool or view, or arguments its parameters do not take."""


class ToolContractError(RuntimeError):
    """A tool returned something that breaks seam 2's contract or its declared shape: a bug in the tool."""


@dataclass(frozen=True)
class Context:
    """Who is calling: the engine that runs as the viewer, the viewer, the view and the page's as-of date."""

    engine: Engine
    viewer: Viewer
    view: str = "staff"
    as_of: dt.date | None = None
    thresholds: Thresholds = field(default_factory=load_thresholds)
    # The hindsight test's replays only (ticket 34): the lesson library as decided by this date, each lesson
    # counted from the day the passages it rests on became public, not from its decision. None everywhere else,
    # where a lesson counts from the day two people decided it (ADR 0002).
    decided_by: dt.date | None = None
    # An implementing agency's private uploads (ticket 38): the upload with this id as the viewer may read it, through
    # the one access rule (src/strata/server/access.py), or None for one they may not read or that does not exist. Only
    # the server gives it, per request; without it, a tool reads no upload, so no other caller can reach one.
    uploads: Callable[[str], Mapping[str, Any] | None] | None = None
    # Lineage (ticket 45): a list the call adds each table it read to, in three parts and in the order it first read
    # them, so the run log can trace an answer to the tables its tool calls read. None records nothing.
    reads: list[str] | None = None


TABLE_READ = re.compile(r"\bstrata\.[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*\b")
SQL_COMMENT = re.compile(r"--[^\n]*|/\*.*?\*/", re.S)


@functools.cache
def _catalog_names() -> frozenset[str]:
    """The tables and views the catalog defines, read once, on the first call that records lineage."""
    from strata.lakehouse import catalog

    return catalog.defined_names()


class _Reading:
    """The viewer's engine, noting each table a query names before it runs it (ticket 45). Every query names its
    tables in three parts (gates/sql_lint.py), so the names in its text are the tables it read. A name in a comment,
    such as the module strata.knowledge.retrieval, is not read, and only names the catalog defines are kept."""

    def __init__(self, engine: Engine, reads: list[str]):
        self._engine, self._reads = engine, reads

    def run(self, sql: str, params=None):
        known = _catalog_names()
        for name in TABLE_READ.findall(SQL_COMMENT.sub("", sql)):
            if name in known and name not in self._reads:
                self._reads.append(name)
        return self._engine.run(sql, params)

    def __getattr__(self, name: str):
        return getattr(self._engine, name)


@dataclass(frozen=True)
class Call:
    """What a tool's adapter receives: the context, with the as-of date settled."""

    engine: Engine
    viewer: Viewer
    view: str
    as_of: dt.date
    thresholds: Thresholds
    decided_by: dt.date | None = None  # Context.decided_by
    uploads: Callable[[str], Mapping[str, Any] | None] | None = None  # Context.uploads


# ── The agent's tool list ────────────────────────────────────────────────

THRESHOLD = re.compile(r"\{([a-z_]+(?:\.[a-z_]+)+)\}")  # a value of the thresholds file: {passages.results}


def _filled(text: str, thresholds: Thresholds) -> str:
    """A description with each threshold it names in braces filled in from the thresholds file."""
    return THRESHOLD.sub(lambda match: str(thresholds.value(match.group(1))), text)


def _schema(parameter: ToolParameter, thresholds: Thresholds) -> dict:
    return {**JSON_TYPES[parameter.type], "description": _filled(parameter.description, thresholds)}


def agent_tool(tool: Tool, thresholds: Thresholds | None = None) -> dict:
    """One tool as the agent is offered it: a function with a JSON Schema for its arguments."""
    limits = thresholds or load_thresholds()
    return {
        "type": "function",
        "name": tool.name,
        "description": _filled(tool.description, limits),
        "parameters": {
            "type": "object",
            "properties": {parameter.name: _schema(parameter, limits) for parameter in tool.parameters},
            "required": [parameter.name for parameter in tool.parameters if parameter.required],
            "additionalProperties": False,
        },
    }


def agent_tools(tools: dict[str, Tool] | None = None, thresholds: Thresholds | None = None) -> list[dict]:
    """The agent's tool list: exactly the registry's tools, in the registry's order."""
    limits = thresholds or load_thresholds()
    return [agent_tool(tool, limits) for tool in (tools if tools is not None else load_tools()).values()]


# ── Calling a tool ───────────────────────────────────────────────────────

def today() -> dt.date:
    return dt.datetime.now(dt.UTC).date()


def _argument(tool: Tool, parameter: ToolParameter, value: Any) -> Any:
    def refuse(need: str):
        raise ToolError(f"{tool.name} takes {parameter.name} as {need}, not {value!r}.")

    if parameter.type == "date":
        if isinstance(value, dt.date) and not isinstance(value, dt.datetime):
            return value
        try:
            return dt.date.fromisoformat(value)
        except (TypeError, ValueError):
            refuse("a date such as 2026-10-22")
    if parameter.type == "string":
        return value if isinstance(value, str) and value.strip() else refuse("text")
    if parameter.type == "integer":
        return value if isinstance(value, int) and not isinstance(value, bool) else refuse("a whole number")
    if parameter.type == "number":
        return value if isinstance(value, int | float) and not isinstance(value, bool) else refuse("a number")
    return value if isinstance(value, bool) else refuse("true or false")


def _bind(tool: Tool, arguments: Mapping[str, Any]) -> dict[str, Any]:
    names = {parameter.name for parameter in tool.parameters}
    unknown = sorted(set(arguments) - names)
    if unknown:
        raise ToolError(f"{tool.name} has no parameter {', '.join(unknown)}. It takes {', '.join(sorted(names))}.")
    bound = {}
    for parameter in tool.parameters:
        value = arguments.get(parameter.name)
        if value is None:
            if parameter.required:
                raise ToolError(f"{tool.name} needs {parameter.name}: {parameter.description}")
            continue
        bound[parameter.name] = _argument(tool, parameter, value)
    return bound


def _adapter(tool: Tool):
    module, function = tool.adapter.split(":")
    return getattr(importlib.import_module(module), function)


def call(name: str, arguments: Mapping[str, Any], context: Context, tools: dict[str, Tool] | None = None) -> dict:
    """Run one tool by name with the agent's or the page's arguments, as the context's viewer."""
    tools = tools if tools is not None else load_tools()
    if name not in tools:
        raise ToolError(f"There is no tool {name}. The registry has {', '.join(tools)}.")
    if context.view not in VIEWS:
        raise ToolError(f"{context.view!r} is not a view. The views are {', '.join(VIEWS)}.")
    tool = tools[name]
    bound = _bind(tool, arguments)
    asked = [date for date in (bound.pop("as_of", None), context.as_of) if date is not None]
    as_of = min(asked) if asked else today()
    engine = context.engine if context.reads is None else _Reading(context.engine, context.reads)
    output = _adapter(tool)(Call(engine, context.viewer, context.view, as_of, context.thresholds,
                                 context.decided_by, context.uploads), **bound)
    result = {"tool": name, "as_of": as_of.isoformat(), "view": context.view, **output}
    if tool.result.summary_fields:
        result["summary"] = summary(tool, bound, result)
    check_contract(tool, result)
    return result


def summary_id(tool: Tool, bound: Mapping[str, Any], as_of: str) -> str:
    """The summary's evidence id: the tool, its required arguments and those that name the record it is about
    (key = true), the as-of date, then any other argument the call set, so two calls with different criteria
    in one turn are two records. strata.tools.find_comparables:KE-NWWDA-541055-CW-RFB@2026-10-22?review_type=Prior,
    or, for a package with no STEP row, strata.tools.find_comparables:@2026-10-22?method=Request%20for%20Bids&..."""
    def text(value: Any) -> str:
        return quote(value.isoformat() if isinstance(value, dt.date) else str(value), safe="-_.~")

    keyed = [parameter for parameter in tool.parameters if parameter.required or parameter.key]
    key = "/".join(text(bound[parameter.name]) for parameter in keyed if parameter.name in bound)
    others = "&".join(f"{parameter.name}={text(bound[parameter.name])}" for parameter in tool.parameters
                      if parameter not in keyed and parameter.name in bound)
    return f"strata.tools.{tool.name}:{key}@{as_of}" + (f"?{others}" if others else "")


def summary(tool: Tool, bound: Mapping[str, Any], result: Mapping[str, Any]) -> dict:
    """The tool's derived figures as one record: public on the as-of date, with a source line that names
    the tool and the sources it read."""
    return {"evidence_id": summary_id(tool, bound, result["as_of"]), "public_from": result["as_of"],
            "source": {"tool": tool.name, "sources": list(tool.sources)},
            # A field the tool left out is the contract check's to name, so a broken tool raises ToolContractError.
            **{field: result.get(field) for field in tool.result.summary_fields}}


# ── Seam 2's contract ────────────────────────────────────────────────────

def check_contract(tool: Tool, result: dict) -> None:
    """Every result has the shared envelope and the tool's own fields; every row, and the summary when
    the tool declares one, is cited, dated on or before the as-of date, and has its source line. An abstention gives a reason and no rows, unless the
    registry lists it under abstentions_with_rows, such as too few comparables for a range. Each
    reason code, in a row's marks or in the coverage line, and each abstention reason is one the
    registry lists, so the screens' copy has a sentence for it."""
    def broken(what: str):
        raise ToolContractError(f"{tool.name} broke the tool contract: {what}.")

    expected = set(ENVELOPE) | set(tool.result.fields) | ({"summary"} if tool.result.summary_fields else set())
    if set(result) != expected:
        broken(f"its result has {sorted(result)}, not {sorted(expected)}")
    coverage = result["coverage"]
    if not isinstance(coverage, dict) or set(coverage) != set(COVERAGE):
        broken(f"its coverage must have {', '.join(COVERAGE)}")
    for left_out in coverage["not_used"]:
        if left_out.get("reason") not in tool.result.reasons:
            broken(f"its coverage line leaves rows out for {left_out.get('reason')!r}, which its result's reasons "
                   f"do not list")
    abstention = result["abstention"]
    if abstention is not None and (not isinstance(abstention, dict) or not abstention.get("reason")):
        broken("an abstention must give its reason")
    if abstention is not None and abstention["reason"] not in tool.result.abstentions:
        broken(f"it abstained for {abstention['reason']!r}, which its result's abstentions do not list")
    if abstention is not None and result["rows"] and abstention["reason"] not in tool.result.abstentions_with_rows:
        broken("it abstained and still returned rows")
    if tool.result.summary_fields:
        record = result["summary"]
        if set(record) != {"evidence_id", "public_from", "source", *tool.result.summary_fields}:
            broken(f"its summary has {sorted(record)}, not the declared {sorted(tool.result.summary_fields)}")
        if not str(record["evidence_id"]).startswith(f"strata.tools.{tool.name}:"):
            broken(f"its summary's evidence id {record['evidence_id']!r} does not name the tool")
        if not record["public_from"] or record["public_from"] > result["as_of"]:
            broken(f"its summary is public from {record['public_from']}, after the as-of date {result['as_of']}")
        if not isinstance(record["source"], dict) or not record["source"].get("tool"):
            broken("its summary has no source line naming the tool")
    for row in result["rows"]:
        if set(row) != set(tool.result.row_fields):
            broken(f"a row has {sorted(row)}, not the declared {sorted(tool.result.row_fields)}")
        if not isinstance(row["evidence_id"], str) or ":" not in row["evidence_id"]:
            broken(f"the row {row['evidence_id']!r} has no evidence id naming its table and key")
        if not row["public_from"] or row["public_from"] > result["as_of"]:
            broken(f"{row['evidence_id']} is public from {row['public_from']}, after the as-of date {result['as_of']}")
        for field_name in tool.result.nested_rows:
            for record in row[field_name] or ():
                cited = record.get("evidence_id") if isinstance(record, dict) else None
                if not isinstance(cited, str) or ":" not in cited:
                    broken(f"an item of {row['evidence_id']}'s {field_name} has no evidence id naming its table and key")
                if not record.get("public_from") or record["public_from"] > result["as_of"]:
                    broken(f"{cited} in {row['evidence_id']}'s {field_name} is public from {record.get('public_from')}, "
                           f"after the as-of date {result['as_of']}")
        if not isinstance(row["source"], dict) or set(row["source"]) != set(tool.result.source_fields):
            broken(f"{row['evidence_id']} has no source line with {', '.join(tool.result.source_fields)}")
        for mark in row.get("marks") or []:
            for reason in mark["reasons"]:
                if reason["code"] not in tool.result.reasons:
                    broken(f"{row['evidence_id']} gives the reason {reason['code']!r}, which its result's "
                           f"reasons do not list")
