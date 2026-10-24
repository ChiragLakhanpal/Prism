"""The tool registry at work: every tool is called here, by name, as the viewer (spec, seam 2).

config/tools.toml defines each tool once (spec, "Ten single places", item 2) and
strata.config.load_tools() reads it. This module does three things with those definitions:

- agent_tools() is the agent's tool list: one function tool per entry, in the Responses API's
  shape, so adding a tool is one entry in the file. A value of the thresholds file named in braces
  in a description, such as {passages.results}, is filled in from that file.
- call() runs a tool by name. It checks the arguments against the tool's parameters, settles
  the as-of date (the earlier of the call's and the page's, else today), runs the adapter with
  the viewer's engine, and wraps the result in the envelope every tool shares.
- It then checks the result against seam 2's contract and the tool's declared shape: every row
  has an evidence id, a public date on or before the as-of date and a source line, and every
  reason code and abstention reason is one the file lists. A tool that breaks the contract raises
  ToolContractError, so a test catches it before a viewer does.
"""

from __future__ import annotations

import datetime as dt
import importlib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

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


@dataclass(frozen=True)
class Call:
    """What a tool's adapter receives: the context, with the as-of date settled."""

    engine: Engine
    viewer: Viewer
    view: str
    as_of: dt.date
    thresholds: Thresholds


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
    output = _adapter(tool)(Call(context.engine, context.viewer, context.view, as_of, context.thresholds), **bound)
    result = {"tool": name, "as_of": as_of.isoformat(), "view": context.view, **output}
    check_contract(tool, result)
    return result


# ── Seam 2's contract ────────────────────────────────────────────────────

def check_contract(tool: Tool, result: dict) -> None:
    """Every result has the shared envelope and the tool's own fields; every row is cited, dated on or
    before the as-of date, and has its source line. An abstention gives a reason and no rows, unless the
    registry lists it under abstentions_with_rows, such as too few comparables for a range. Each
    reason code, in a row's marks or in the coverage line, and each abstention reason is one the
    registry lists, so the screens' copy has a sentence for it."""
    def broken(what: str):
        raise ToolContractError(f"{tool.name} broke the tool contract: {what}.")

    expected = set(ENVELOPE) | set(tool.result.fields)
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
    for row in result["rows"]:
        if set(row) != set(tool.result.row_fields):
            broken(f"a row has {sorted(row)}, not the declared {sorted(tool.result.row_fields)}")
        if not isinstance(row["evidence_id"], str) or ":" not in row["evidence_id"]:
            broken(f"the row {row['evidence_id']!r} has no evidence id naming its table and key")
        if not row["public_from"] or row["public_from"] > result["as_of"]:
            broken(f"{row['evidence_id']} is public from {row['public_from']}, after the as-of date {result['as_of']}")
        if not isinstance(row["source"], dict) or set(row["source"]) != set(tool.result.source_fields):
            broken(f"{row['evidence_id']} has no source line with {', '.join(tool.result.source_fields)}")
        for mark in row.get("marks") or []:
            for reason in mark["reasons"]:
                if reason["code"] not in tool.result.reasons:
                    broken(f"{row['evidence_id']} gives the reason {reason['code']!r}, which its result's "
                           f"reasons do not list")
