"""The deep research run (ticket 148): read every enabled source for a project, keep what they gave, write the brief
and check every sentence of it, as one stream of /api/ask's events.

The stream's steps, in order:

  facts            the project's record: its name, status and closing date
  source-<key>     one step per source, done with how many items it gave, or not_reached with its note. A source
                   that refuses or fails is a step that says so, never a failed run.
  writing          the writer writes the brief from the run's items (src/strata/research/writer.py)
  checking         the six checks on every sentence, with check 4's judge step inside it

then the kept sentences (sentence, with the section each sits in), the evidence they cite (evidence), the check counts
(checks), each removed sentence with its reasons (removed), and done with the run's id and the brief, which is saved
before done so GET /api/projects/{project_id}/research returns it without calling a model.

With reuse, the run writes the brief from the latest run already kept, without reading the sources again: each source
step then says what that run read, in the registry's order, done with its items and the note "read on <day>" (or
not_reached with that run's note), and stored_on, the day it read them. With stored_only (research.live_sources false,
ticket 152) the steps come one by one, research.stored_step_seconds apart, so the tab shows them as a live run's; and
when the writer or the judge fails, the run keeps the stored brief: a writing step done with kept_from, then done with
the stored brief, never an error. The demo's brief is written that way from the run ticket 147's seed keeps
(ops/research/seed.py, seed:P156634:2026-11-05).

The readers, the project facts they read and the fetch are ticket 147's (src/strata/research/sources). The Kit holds
them, so a test gives its own; default_kit() gives the live fetch, each source's calls paced by its pace_seconds in
config/research.toml. The run and its items are kept through ticket 147's store (src/strata/research/store.py).
"""

from __future__ import annotations

import asyncio
import dataclasses
import datetime as dt
import logging
from collections.abc import AsyncIterator, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from strata.agent.answer_check import Asker, SixChecks
from strata.agent.verifier import Verdict, answer_events, check
from strata.dbx import Viewer
from strata.harness.facts import Facts
from strata.harness.turn import Event
from strata.research import brief as briefs
from strata.research.sources import long_date
from strata.research.store import ResearchStore
from strata.research.store import Run as KeptRun
from strata.research.writer import Writer, WriterError
from strata.tools import project_signals as signals
from strata.tools import registry

log = logging.getLogger(__name__)
TOOL = briefs.TOOL
# The codes an error event may carry; web/src/copy.ts has a sentence for each (ticket 149).
ERRORS = ("unknown_project", "not_fetched", "no_sources", "writer_unavailable", "writer_shape", "internal")


class ResearchError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Kit:
    """What a run reads the sources with: the project's facts as ticket 147's readers take them, the enabled sources,
    the reader and the fetch. read(source, project, fetch, engine, now) gives a SourceResult (source, items, reached,
    status, note)."""
    facts: Callable[[Any, str, dt.date], Any]
    sources: Callable[[], list]
    read: Callable[..., Any]
    fetch: Any


def default_kit() -> Kit:
    """Ticket 147's readers on the live fetch, each source's calls paced by the registry's pace_seconds."""
    from strata.config import load_research
    from strata.research import fetching, project, sources

    fetch, pacer = fetching.live(), fetching.Pacer()

    def read(source, facts, fetch, engine, now):
        return sources.read(source, facts, fetching.for_source(source, fetch, pacer=pacer), engine, now)

    return Kit(facts=lambda engine, project_id, as_of: project.project_facts(project_id, fetch=fetch, engine=engine),
               sources=lambda: [source for source in load_research().values() if source.enabled], read=read,
               fetch=fetch)


@dataclass(frozen=True)
class Request:
    viewer: Viewer
    view: str
    project_id: str
    as_of: dt.date
    run_id: str
    reuse: bool = False
    stored_only: bool = False  # research.live_sources false: no source is read, and a failed writer keeps the brief
    # The viewer's team, and the reader of the field photos it kept (ticket 150; src/strata/server/field_photos.py),
    # through the one access rule. A brief written from a run that read a team's photos is kept for that team only.
    team_key: str | None = None
    field_photos: Callable[[str, dt.date], list] | None = None


class KeepStored(RuntimeError):
    """A stored-only run's writer or judge failed, so the run keeps the stored brief."""


def _key(source) -> str:
    return source if isinstance(source, str) else getattr(source, "key", None) or source["key"]


def _label(source) -> str:
    return getattr(source, "label", None) or (source.get("label") if isinstance(source, Mapping) else None) or _key(source)


def _plain(result, source) -> dict:
    """A SourceResult, or a mapping in its shape, as plain data with its source's key and label."""
    def value(name, default=None):
        return result.get(name, default) if isinstance(result, Mapping) else getattr(result, name, default)

    items = [dataclasses.asdict(item) if dataclasses.is_dataclass(item) else dict(item) for item in value("items", [])]
    return {"key": _key(source), "label": _label(source), "items": items, "reached": bool(value("reached")),
            "status": value("status"), "note": value("note"), "counts": dict(value("counts") or {})}


def _step(step_id: str, kind: str, status: str, **more) -> Event:
    return Event("step", {"id": step_id, "kind": kind, "status": status, **more})


class Run:
    """One run's dependencies: the viewer's engine, ticket 147's kit, the store, the writer, the six checks, the
    thresholds, the clock and the environment the tools read their services' settings from."""

    def __init__(self, engine_for, kit: Kit | None, store: ResearchStore, writer: Writer | None, six_checks: SixChecks,
                 now: Callable[[], dt.datetime], environ: Mapping[str, str] | None = None):
        self.engine_for, self.kit, self.store, self.writer = engine_for, kit, store, writer
        self.six_checks, self.now, self.environ = six_checks, now, environ

    def _context(self, engine, request: Request) -> registry.Context:
        return registry.Context(engine=engine, viewer=request.viewer, view=request.view, as_of=request.as_of,
                                thresholds=self.six_checks.thresholds, environ=self.environ,
                                field_photos=request.field_photos)

    def project(self, request: Request) -> dict | None:
        """The project as of the day, from its record (project_signals' one reading of status and closing date)."""
        with self.engine_for(request.viewer) as engine:
            call = registry.Call(engine, request.viewer, request.view, request.as_of, self.six_checks.thresholds,
                                 environ=self.environ)
            return signals._project(call, request.project_id,
                                    signals._rows(call, "history.sql", project_id=request.project_id))

    async def events(self, request: Request) -> AsyncIterator[Event]:
        yield _step("facts", "facts", "running")
        project = await asyncio.to_thread(self.project, request)
        if project is None:
            raise ResearchError("unknown_project")
        yield _step("facts", "facts", "done", project_id=project["project_id"], project_name=project["project_name"],
                    closing_date=project["closing_date"])
        if request.reuse:
            result = await asyncio.to_thread(self._evidence, request)
            if result["abstention"]:
                raise ResearchError("not_fetched")
            pause = float(self.six_checks.thresholds.value("research.stored_step_seconds")) if request.stored_only else 0
            for event in self._kept_steps(result):
                if pause and event.data["status"] != "running":  # the source's running line shows for the pause
                    await asyncio.sleep(pause)
                yield event
        else:
            async for event in self._read(request, project):
                yield event
            result = await asyncio.to_thread(self._evidence, request)
        try:
            async for event in self._write_and_check(request, project, result):
                yield event
        except Exception as error:
            if not request.stored_only:
                raise
            try:
                kept = await asyncio.to_thread(self.store.latest_brief, request.project_id, request.as_of,
                                               request.team_key if request.field_photos else None)
            except Exception:  # noqa: BLE001 - the store failed too: the run's own error is the one to report
                kept = None
            if kept is None:
                if isinstance(error, KeepStored):
                    raise ResearchError("writer_unavailable") from error
                raise
            log.warning("Run %s: the writer or the judge failed (%s), so the stored brief is kept.", request.run_id, error)
            day = str(kept.get("written_at") or "")[:10] or None
            yield _step("writing", "writing", "done", kept_from=day,
                        label=f"Writing: kept the brief of {long_date(day)}" if day else "Writing: kept the brief")
            yield Event("done", {"run_id": request.run_id, "status": "kept", "brief": kept})

    def _evidence(self, request: Request) -> dict:
        with self.engine_for(request.viewer) as engine:
            return registry.call(TOOL, {"project_id": request.project_id}, self._context(engine, request))

    @staticmethod
    def _kept_steps(result: Mapping) -> list[Event]:
        """The source steps of a run already kept, in the order a live run reads the sources (the registry's): what
        each source gave, done with its items and "read on <day>", or why it was not reached, each with stored_on, the
        day the stored run read the sources."""
        from strata.config import load_research

        summary, steps = result["summary"], []
        day = (result.get("run") or {}).get("as_of")
        reached = {source["key"]: source for source in summary["sources_reached"]}
        missed = {source["key"]: source for source in summary["sources_not_reached"]}
        order = [key for key in load_research() if key in reached or key in missed]
        order += [key for key in [*reached, *missed] if key not in order]
        for key in order:
            source = reached.get(key) or missed[key]
            named = {"source": key, "label": source["label"], "stored_on": day}
            steps.append(_step(f"source-{key}", "source", "running", **named))
            if key in reached:
                steps.append(_step(f"source-{key}", "source", "done", items=source.get("items") or 0,
                                   note=f"read on {long_date(day)}" if day else None, **named))
            else:
                steps.append(_step(f"source-{key}", "source", "not_reached", note=source.get("note"), **named))
        return steps

    async def _read(self, request: Request, project: dict) -> AsyncIterator[Event]:
        """Each enabled source in turn, then the run and its items kept."""
        if self.kit is None:
            raise ResearchError("no_sources")
        started = self.now()
        with self.engine_for(request.viewer) as engine:
            facts = await asyncio.to_thread(self.kit.facts, engine, request.project_id, request.as_of)
            results = []
            for source in self.kit.sources():
                key, label = _key(source), _label(source)
                yield _step(f"source-{key}", "source", "running", source=key, label=label)
                try:
                    found = _plain(await asyncio.to_thread(self.kit.read, source, facts, self.kit.fetch, engine,
                                                           self.now()), source)
                except Exception as error:  # noqa: BLE001 - a reader that fails is a source not reached
                    log.warning("Run %s: the %s reader failed (%s).", request.run_id, key, error)
                    found = {"key": key, "label": label, "items": [], "reached": False, "status": "failed",
                             "note": "The reader failed on this source's answer."}
                results.append(found)
                if found["reached"]:
                    yield _step(f"source-{key}", "source", "done", source=key, label=label, items=len(found["items"]),
                                note=found["note"])
                else:
                    yield _step(f"source-{key}", "source", "not_reached", source=key, label=label, note=found["note"])
        notes = {result["key"]: {"label": result["label"], "status": result["status"], "note": result["note"],
                                 "items": len(result["items"]), **result.get("counts", {})} for result in results}
        run = KeptRun(run_id=request.run_id, project_id=request.project_id, started=started, as_of=request.as_of,
                      sources_asked=tuple(result["key"] for result in results),
                      reached=tuple(result["key"] for result in results if result["reached"]), finished=self.now(),
                      viewer=request.viewer.user_id, source_notes=notes)
        await asyncio.to_thread(self.store.save, run, [item for result in results for item in result["items"]])

    async def _write_and_check(self, request: Request, project: dict, result: dict) -> AsyncIterator[Event]:
        if self.writer is None:
            raise ResearchError("writer_unavailable")
        yield _step("writing", "writing", "running")
        try:
            text = await asyncio.to_thread(self.writer.write, briefs.message(project, result), request.project_id,
                                           result["as_of"])
            placed, groups = briefs.parse(text)
        except WriterError as error:
            log.warning("Run %s: the writer gave no answer (%s).", request.run_id, error)
            raise ResearchError("writer_unavailable") from error
        except briefs.BriefError as error:
            log.warning("Run %s: the writer's answer is not a brief (%s).", request.run_id, error)
            raise ResearchError("writer_shape") from error
        yield _step("writing", "writing", "done", sentences=len(placed))

        yield _step("checking", "checking", "running", sentences=len(placed))
        seen, viewed = Facts(), Facts()
        for row in [*result["rows"], result["summary"], *briefs.coverage_records(result)]:
            seen.record(row["evidence_id"], row, tool=TOOL)
            viewed.record(row["evidence_id"], briefs.checked_row(row), tool=TOOL)
        sentences = [check(index, claim, viewed) for index, (_, claim) in enumerate(placed)]
        answer = self.six_checks.checked(sentences, seen, facts_only=briefs.facts_only(placed))
        verdict: Verdict | None = None
        asker = Asker(request.viewer, request.view, request.as_of, request.run_id)
        async for item in self.six_checks.finish(answer, seen, asker):
            if isinstance(item, Verdict):
                verdict = item
            else:
                yield item
        if request.stored_only and verdict is not None and verdict.judge_called and not verdict.judge_responded:
            raise KeepStored("The judge did not answer.")
        events = answer_events(verdict, seen, [TOOL], self.six_checks.cited_only)
        kept, evidence, checks, removed = {}, {}, None, []
        for event in events:
            data = dict(event.data)
            if event.type == "sentence":
                place = placed[data["index"]][0]
                data.update(section=place.section, group=place.group, part=place.part)
                kept[data["index"]] = data
                event = Event("sentence", data)
            elif event.type == "evidence":
                evidence[data["id"]] = data
            elif event.type == "checks":
                checks = data
            elif event.type == "removed":
                place = placed[data["index"]][0]
                data.update(section=place.section, group=place.group, part=place.part)
                removed.append(data)
                event = Event("removed", data)
            yield event
        yield _step("checking", "checking", "done", kept=len(kept), removed=len(removed))
        items = {row["evidence_id"]: row for row in result["rows"]}
        subject = {"project_id": project["project_id"], "project_name": project["project_name"],
                   "closing_date": project["closing_date"], "as_of": result["as_of"]}
        composed = briefs.compose(placed, groups, kept, items, evidence, checks, removed, result["coverage"],
                                  result["run"], subject)
        composed["summary"] = result["summary"]
        composed["writer"] = getattr(self.writer, "name", None)
        written = self.now()
        # A brief written from a team's field photos is that team's alone (ticket 150), whether or not it cites them.
        team = request.team_key if any(row.get("team") for row in result["rows"]) else None
        await asyncio.to_thread(self.store.save_brief, request.run_id if not request.reuse else result["run"]["run_id"],
                                request.project_id, written, request.as_of, composed, team)
        yield Event("done", {"run_id": request.run_id, "status": "written", "brief": composed})
