"""The answer loop: the agent decides, the app runs its tools as the viewer (ADR 0003).

answer_runner() makes the runner the server's /api/ask stream runs. For each question:

1. It sends the agent one message that carries data only (Prompt Shields refuses data that holds
   rules, so the rules live in the agent's instructions): the question, the page's scope chip, the
   as-of date, the view and the language. The as-of date is the page's, and never later than today,
   so the agent never sees or states an event that has not happened.
2. The agent answers through the Responses API with tool calls or with its claims. Each tool call runs
   through the tool registry with the viewer's own engine, and every row it returns, with its summary
   of derived figures when it has one and the records inside its rows that the registry names
   (nested_rows, such as each side of a disagreement), is kept in the turn's Facts, so the verifier
   can check the answer against it. The results go back to the agent.
3. This repeats for at most agent.tool_rounds rounds (config/thresholds.toml). A call the agent asks
   for after that is not run: the agent gets a result that says so, and must answer from what it has.
4. The agent's claims go to the stream, which runs the verifier on them before anything is shown, with
   the refusal key when the agent turned the request down (ticket 24).

Each tool call is a step, announced as it starts and when it is done. A tool the agent called with
arguments the registry refuses gets the refusal back, so the agent can try again in its next round. A
viewer whose grants do not let a tool read gets "permission" back, never someone else's rows.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any, Protocol

from strata.agent.claims import ClaimsError, parse_answer
from strata.config import Thresholds, Tool, load_thresholds, load_tools
from strata.harness.facts import Facts
from strata.harness.turn import Event, RunError, Runner, Turn
from strata.lakehouse.engine import EngineError, PermissionDenied
from strata.server.engines import EngineFor
from strata.tools import registry

log = logging.getLogger("strata.agent")
ISO_DAY = 10  # the length of an ISO date, 2026-10-23


class Agent(Protocol):
    """The agent as the loop sees it: the Foundry agent live, the scripted agent offline."""

    name: str
    version: str | None

    def respond(self, items: list[dict], previous_response_id: str | None) -> dict:
        """One answer through the Responses API: a response with its output items."""


class AgentError(RunError):
    """The agent did not answer: unavailable, refused by a content filter, no claims, or the data service
    failed during a tool call."""


def output_text(response: Mapping) -> str:
    """The text of a response's message items, joined."""
    return "".join(part.get("text", "") for item in response.get("output") or [] if item.get("type") == "message"
                   for part in item.get("content") or [] if part.get("type") == "output_text")


def function_calls(response: Mapping) -> list[dict]:
    return [item for item in response.get("output") or [] if item.get("type") == "function_call"]


def call_output(call: Mapping, output: Mapping) -> dict:
    return {"type": "function_call_output", "call_id": call["call_id"],
            "output": json.dumps(output, ensure_ascii=False, default=str)}


def for_agent(value: Any, as_of: dt.date) -> Any:
    """A tool's result as the agent gets it: the same, but with no date later than the as-of date in an
    abstention, such as the day a plan version that was not yet public became public (ticket 09)."""
    def strip(item):
        if isinstance(item, Mapping):
            return {key: strip(inner) for key, inner in item.items() if not _later(inner, as_of)}
        if isinstance(item, list):
            return [strip(inner) for inner in item]
        return item

    if isinstance(value, Mapping) and value.get("abstention"):
        shown = {**value, "abstention": strip(value["abstention"])}
        if "summary" in value and not value.get("rows"):
            # A tool that abstained with no rows has no figure to cite, and its summary's id repeats the call's
            # arguments, such as the date of a plan version not yet public (ticket 36, check_plan's summary).
            shown["summary"] = None
        return shown
    return value


def _later(value: Any, as_of: dt.date) -> bool:
    if isinstance(value, dt.date):
        return (value.date() if isinstance(value, dt.datetime) else value) > as_of
    if isinstance(value, str) and len(value) >= ISO_DAY:
        try:
            return dt.date.fromisoformat(value[:ISO_DAY]) > as_of
        except ValueError:
            return False
    return False


def keep_nested(facts: Facts, record: Mapping, tool: str | None) -> None:
    """Keep a record a row holds, such as one side of a disagreement, under its own evidence id. Two records
    under one id come from one source, such as two ratings in one passage, or a passage search_passages also
    returned: the record kept first keeps its fields, and the later ones are kept beside it under also, so
    every value that came back under that id backs a claim that cites it."""
    held = facts.get(record["evidence_id"])
    if held is None:
        facts.record(record["evidence_id"], record, tool=tool)
    elif held != record and record not in held.get("also", ()):
        facts.record(record["evidence_id"], {**record, **held, "also": [*held.get("also", ()), record]},
                     tool=facts.tool(record["evidence_id"]))


def keep_result(facts: Facts, name: str, result: Mapping, tools: dict[str, Tool]) -> None:
    """Keep every row a tool returned in the turn's Facts, with the records inside its rows that the registry
    names (nested_rows, such as each side of a disagreement), its summary of derived figures when it has one and
    its abstention, so the verifier can check what a sentence cites against them. The answer loop, check 6's
    get_disagreements call (ticket 24) and the risk-table builder (ticket 30) keep results this way."""
    nested = tools[name].result.nested_rows if name in tools else ()
    # The kind of question of the search that found these rows, which a passage report on one of them takes (ticket 32).
    kind = (result.get("ranked_lower") or {}).get("query_kind")
    for row in result["rows"]:
        facts.record(row["evidence_id"], row, tool=name, kind=kind)
        for record in (inner for field in nested for inner in row.get(field) or ()):
            keep_nested(facts, record, name)
    if result.get("summary"):  # the tool's derived figures, such as a past range, as one citable record
        facts.record(result["summary"]["evidence_id"], result["summary"], tool=name)
    if result.get("abstention"):  # what the tool could not answer, which a summary citing nothing may say
        facts.abstained(name, result["abstention"])


def tool_context(engine, viewer, view: str, as_of: dt.date, limits: Thresholds,
                 environ: Mapping[str, str] | None = None) -> registry.Context:
    """The Context every /api/ask tool call runs in. It carries no reader of uploads, so no agent answer reads an
    implementing agency team's upload, whoever asks (ticket 38; tests/test_uploads.py's must-refuse case)."""
    return registry.Context(engine, viewer, view, as_of, limits, environ=environ)


def answer_runner(agent_for: Callable[[Turn], Agent], engine_for: EngineFor, tools: dict[str, Tool] | None = None,
                  thresholds: Thresholds | None = None,
                  today: Callable[[], dt.date] = registry.today,
                  on_result: Callable[[Turn, str, dict, dict], None] | None = None,
                  environ: Mapping[str, str] | None = None) -> Runner:
    """The runner for /api/ask: agent_for gives each turn its own agent, and engine_for opens the
    viewer's engine for each tool call. on_result, when given, gets each tool call's whole result with the turn,
    the tool's name and its arguments: the full gate's benchmark reads the answer each tool gave this way
    (strata.evals.answer_benchmark). The app passes none. environ is the settings every tool call reads its
    services' addresses and keys from (registry.Context.environ): the env file a live script loaded, or the app's
    environment; without it, the process's environment (ticket 66)."""
    limits = thresholds or load_thresholds()
    rounds = int(limits.value("agent.tool_rounds"))
    tools_held = tools if tools is not None else load_tools()

    def run_tool(turn: Turn, as_of: dt.date, call: Mapping) -> tuple[dict, dict]:
        """One tool call as the viewer: what goes back to the agent, and its line in the run's notes."""
        name, note = call.get("name"), {"tool": call.get("name"), "ran": True, "rows": 0, "abstention": None}
        try:
            arguments = json.loads(call.get("arguments") or "{}")
            if not isinstance(arguments, dict):
                raise ValueError("the arguments are not an object")
        except ValueError as error:
            note.update(arguments=call.get("arguments"), error="bad_arguments")
            return {"error": "bad_arguments", "detail": f"The arguments are not a JSON object: {error}."}, note
        note["arguments"] = arguments
        # The page's as-of date and view go with every call, from the request; the agent never chooses what was public
        # (ticket 40; ADR 0002). A date the agent wrote is replaced, and the run's record keeps what it wrote.
        note.update(as_of=as_of.isoformat(), view=turn.scope.view)
        written = arguments.get("as_of")
        if written is not None:
            arguments = {key: value for key, value in arguments.items() if key != "as_of"}
            if str(written) != as_of.isoformat():
                note["as_of_replaced"] = written
                log.info("Run %s: the agent asked %s as of %s; it ran as of the page's %s.", turn.run_id, name, written,
                         as_of.isoformat())
        try:
            with engine_for(turn.viewer) as engine:
                result = registry.call(name, arguments, tool_context(engine, turn.viewer, turn.scope.view, as_of, limits,
                                                                     environ), tools_held)
        except registry.ToolError as error:
            note["error"] = "bad_arguments"
            return {"error": "bad_arguments", "detail": str(error)}, note
        except PermissionDenied:
            note["error"] = "permission"
            return {"error": "permission"}, note
        except EngineError as error:  # the warehouse timed out or is down: not the agent's doing, nor a bug
            raise AgentError("data_service", str(error)) from error
        shown = for_agent(result, as_of)
        # The turn keeps what the agent got: the same rows, and an abstention with no date after the as-of date, so
        # the judge reads a summary that cites nothing against what the agent read (src/strata/agent/verifier.py).
        keep_result(turn.facts, name, shown, tools_held)
        if on_result is not None:
            on_result(turn, name, arguments, result)
        note.update(rows=len(result["rows"]), abstention=(result["abstention"] or {}).get("reason"))
        if shown.get("summary"):  # which call a cited summary came from, such as the past range an exposure logs
            note["summary_id"] = shown["summary"]["evidence_id"]
        return shown, note

    async def run(turn: Turn) -> AsyncIterator[Event]:
        agent = agent_for(turn)
        turn.notes.agent, turn.notes.agent_version = agent.name, agent.version
        as_of = turn.notes.as_of = min(turn.scope.as_of or today(), today())
        message = {"question": turn.question, "scope": turn.scope.chip, "as_of": as_of.isoformat(),
                   "view": turn.scope.view, "language": turn.scope.language}
        items = [{"role": "user", "content": json.dumps(message, ensure_ascii=False)}]
        previous, refusals, step = None, 0, 0
        while True:
            response = await asyncio.to_thread(agent.respond, items, previous)
            turn.notes.agent_version = agent.version or turn.notes.agent_version  # Foundry names it in a response
            previous = response.get("id")
            turn.notes.response_ids.append(previous)
            calls = function_calls(response)
            if not calls:
                yield Event("step", {"id": "write", "kind": "write", "status": "running"})
                try:
                    answer = parse_answer(output_text(response))
                except ClaimsError as error:
                    raise AgentError("agent_output", str(error)) from error
                yield Event("step", {"id": "write", "kind": "write", "status": "done", "count": len(answer.claims)})
                yield Event("claims", {"claims": answer.claims, "refusal": answer.refusal})
                return
            if turn.notes.tool_rounds >= rounds:
                refusals += 1
                if refusals > 1:
                    raise AgentError("agent_output", "The agent kept asking for tools after its last round.")
                turn.notes.tool_calls += [{"tool": call.get("name"), "ran": False, "reason": "round_limit",
                                           "round": rounds + 1} for call in calls]
                items = [call_output(call, {"not_run": "round_limit", "tool_rounds": rounds}) for call in calls]
                continue
            turn.notes.tool_rounds += 1
            items = []
            for call in calls:
                step += 1
                arguments = _arguments(call)
                shown = {"id": f"tool-{step}", "kind": "tool", "tool": call.get("name"),
                         "project_id": arguments.get("project_id")}
                yield Event("step", {**shown, "status": "running"})
                output, note = await asyncio.to_thread(run_tool, turn, as_of, call)
                turn.notes.tool_calls.append({**note, "round": turn.notes.tool_rounds})
                yield Event("step", {**shown, "status": "done", "count": note["rows"],
                                     "abstention": note["abstention"], "error": note.get("error")})
                items.append(call_output(call, output))

    return run


def _arguments(call: Mapping) -> dict:
    try:
        arguments = json.loads(call.get("arguments") or "{}")
    except ValueError:
        return {}
    return arguments if isinstance(arguments, dict) else {}
