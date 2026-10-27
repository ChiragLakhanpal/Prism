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
4. One rewrite round (ticket 109): the loop runs the verifier's checks 1 to 3 on the agent's answer, offline, and
   when they would remove a sentence it sends the agent one data-only message, {"rewrite": [{"sentence", "reasons"}]},
   and takes the next answer as final. A rewrite that is not an answer (tool calls, no claims as JSON, or an agent
   that failed on the message) leaves the earlier answer. agent.rewrite_rounds (config/thresholds.toml) sets how many such rounds run; 0 turns them off.
   Nothing goes to the stream before this ends.
5. The agent's claims go to the stream, which runs the verifier's six checks on them before anything is shown, with
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
import time
from collections.abc import AsyncIterator, Callable, Mapping
from typing import Any, Protocol

from strata.agent.claims import Answer, Claim, ClaimsError, parse_answer
from strata.agent.verifier import verify
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


def keep_nested(facts: Facts, record: Mapping, tool: str | None, kind: str | None = None) -> None:
    """Keep a record a tool returned, a row or one a row holds (such as one side of a disagreement), under its own
    evidence id. Two records under one id come from one source, such as two ratings in one passage, or a passage
    search_passages also returned: the record kept first keeps its fields, and the later ones are kept beside it
    under also, so every value that came back under that id backs a claim that cites it (ticket 20's review round 3,
    F7). kind is the kind of question of the search that found it (Facts.record)."""
    held = facts.get(record["evidence_id"])
    if held is None or _ranked_again(held, record):
        facts.record(record["evidence_id"], record, tool=tool, kind=kind)
    elif held != record and record not in held.get("also", ()):
        facts.record(record["evidence_id"], {**record, **held, "also": [*held.get("also", ()), record]},
                     tool=facts.tool(record["evidence_id"]), kind=kind)
    # Every tool that returned the id is kept, so check 5 asks each of them (ticket 61's review, F4).
    facts.returned(record["evidence_id"], tool)


RANKING = ("rank", "score")  # a search's own order, which says nothing about the record


def _ranked_again(held: Mapping, record: Mapping) -> bool:
    """Whether a record is the one held, found again by another search at another rank: the later one is kept, as a
    search's ranking is not a value."""
    def plain(row: Mapping) -> dict:
        return {key: value for key, value in row.items() if key not in RANKING}
    return plain(held) == plain(record)


def keep_result(facts: Facts, name: str, result: Mapping, tools: dict[str, Tool]) -> None:
    """Keep every row a tool returned in the turn's Facts, with the records inside its rows that the registry
    names (nested_rows, such as each side of a disagreement), its summary of derived figures when it has one and
    its abstention, so the verifier can check what a sentence cites against them. The answer loop, check 6's
    get_disagreements call (ticket 24) and the risk-table builder (ticket 30) keep results this way."""
    nested = tools[name].result.nested_rows if name in tools else ()
    # The kind of question of the search that found these rows, which a passage report on one of them takes (ticket 32).
    kind = (result.get("ranked_lower") or {}).get("query_kind")
    for row in result["rows"]:
        keep_nested(facts, row, name, kind)
        for record in (inner for field in nested for inner in row.get(field) or ()):
            keep_nested(facts, record, name)
    if result.get("summary"):  # the tool's derived figures, such as a past range, as one citable record
        facts.record(result["summary"]["evidence_id"], result["summary"], tool=name)
    if result.get("abstention"):  # what the tool could not answer, which a summary citing nothing may say
        facts.abstained(name, result["abstention"])


def tool_context(engine, viewer, view: str, as_of: dt.date, limits: Thresholds,
                 environ: Mapping[str, str] | None = None, reads: list[str] | None = None) -> registry.Context:
    """The Context every /api/ask tool call runs in. It carries no reader of uploads, so no agent answer reads an
    implementing agency team's upload, whoever asks (ticket 38; tests/test_uploads.py's must-refuse case). reads
    collects the tables the call read, for the run's lineage (ticket 45)."""
    return registry.Context(engine, viewer, view, as_of, limits, environ=environ, reads=reads)


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
    rewrites = int(limits.value("agent.rewrite_rounds"))
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
        # Lineage (ticket 45): the tables the call read, when it started and how long it took, for the run log.
        reads: list[str] = []
        note.update(reads=reads, called_at=dt.datetime.now(dt.UTC).isoformat())
        started = time.monotonic()
        try:
            with engine_for(turn.viewer) as engine:
                result = registry.call(name, arguments, tool_context(engine, turn.viewer, turn.scope.view, as_of, limits,
                                                                     environ, reads), tools_held)
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
        note.update(rows=len(result["rows"]), abstention=(result["abstention"] or {}).get("reason"),
                    took_ms=round((time.monotonic() - started) * 1000),
                    evidence_ids=[row["evidence_id"] for row in result["rows"]])
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
        previous, refusals, step, answer, rewritten = None, 0, 0, None, 0
        while True:
            try:
                response = await asyncio.to_thread(agent.respond, items, previous)
            except AgentError as error:
                if answer is None:
                    raise
                # The agent failed on the rewrite message, such as a content filter, so it wrote nothing new.
                log.warning("Run %s: the agent did not answer the rewrite (%s).", turn.run_id, error.code)
                response = None
            if response is not None:
                turn.notes.agent_version = agent.version or turn.notes.agent_version  # Foundry names it in a response
                previous = response.get("id")
                turn.notes.response_ids.append(previous)
            calls = function_calls(response) if response is not None else []
            if answer is not None or not calls:
                if answer is None:
                    yield Event("step", {"id": "write", "kind": "write", "status": "running"})
                    try:
                        answer = parse_answer(output_text(response))
                    except ClaimsError as error:
                        raise AgentError("agent_output", str(error)) from error
                else:  # the agent's rewrite, which replaces its answer only when it is one
                    again = None if response is None or calls else _answer_or_none(output_text(response))
                    if again is None:
                        log.info("Run %s: the agent's rewrite was not an answer, so its earlier answer stands.",
                                 turn.run_id)
                        rewritten = rewrites  # no further round: the earlier answer goes to the verifier as it is
                    else:
                        answer = again
                flagged = would_remove(answer.claims, turn.facts, turn.scope.language) if rewritten < rewrites else []
                if flagged:
                    rewritten += 1
                    log.info("Run %s: checks 1 to 3 would remove %d sentences, so the agent was asked to rewrite.",
                             turn.run_id, len(flagged))
                    items = [{"role": "user", "content": json.dumps({REWRITE: flagged}, ensure_ascii=False)}]
                    continue
                # Only now does the answer go to the stream, which runs the verifier's six checks on it.
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


REWRITE = "rewrite"  # the key of the one message the rewrite round sends


def rewrite_asked(items: list[dict]) -> list[dict] | None:
    """The sentences a request asks the agent to rewrite, when it is the rewrite round's message, or None."""
    for item in items:
        if item.get("role") == "user":
            try:
                message = json.loads(item.get("content") or "")
            except (TypeError, ValueError):
                continue
            if isinstance(message, dict) and REWRITE in message:
                return message[REWRITE]
    return None


def would_remove(claims: list[Claim], facts: Facts, language: str) -> list[dict]:
    """Each sentence the verifier's checks 1 to 3 would remove, with its reasons, as the rewrite message lists them:
    data only, the sentence and each reason's code with the number, date or evidence id it is about."""
    return [{"sentence": sentence.claim.sentence,
             "reasons": [{"code": reason.code, **({"text": reason.text} if reason.text is not None else {})}
                         for reason in sentence.reasons]}
            for sentence in verify(claims, facts, language).removed]


def _answer_or_none(text: str) -> Answer | None:
    try:
        return parse_answer(text)
    except ClaimsError:
        return None


def _arguments(call: Mapping) -> dict:
    try:
        arguments = json.loads(call.get("arguments") or "{}")
    except ValueError:
        return {}
    return arguments if isinstance(arguments, dict) else {}
