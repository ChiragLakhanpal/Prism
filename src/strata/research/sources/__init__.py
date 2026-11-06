"""The deep research readers, one module per source, behind one interface (ticket 147):

    read(source: ResearchSource, project: ProjectFacts, fetch: Fetch, engine: Engine | None, now: dt.datetime)
        -> SourceResult

read() calls the reader the registry names for the source (config/research.toml, reader = "module:function"), which
takes the same arguments. A source the registry lists as not enabled gives no item and its reason. A refusal (403,
429, a bot check page, another status on the call that decides the result) or a host Prism cannot reach gives
reached False, the status and a one-sentence note, and never an item: read() drops whatever the reader held.

SourceResult is {source, items, reached, status, note}: status is the decisive answer's HTTP status as text ("200",
"429"), "bot check", "unreachable", or "read" for a source read from the lakehouse; note is one sentence.
"""

from __future__ import annotations

import datetime as dt
import importlib
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import cache
from importlib import resources

from strata.config import ResearchSource
from strata.lakehouse.engine import Engine, EngineError
from strata.research.fetching import Fetch, Refused, Unreachable
from strata.research.items import ITEM_KEYS
from strata.research.project import ProjectFacts

READ = "read"  # the status of a source read from the lakehouse, which has no HTTP status
NOT_CONNECTED = "not connected"


@dataclass
class SourceResult:
    source: str
    items: list[dict] = field(default_factory=list)
    reached: bool = True
    status: str = READ
    note: str = ""

    def as_dict(self) -> dict:
        return {"source": self.source, "items": self.items, "reached": self.reached, "status": self.status,
                "note": self.note}


Reader = Callable[[ResearchSource, ProjectFacts, Fetch, Engine | None, dt.datetime], SourceResult]


@cache
def _sql(name: str) -> str:
    return (resources.files("strata.research") / "sql" / f"{name}.sql").read_text()


def rows(engine: Engine, name: str, **params) -> list[dict]:
    """The rows of one of the readers' queries (src/strata/research/sql), as dicts."""
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def long_date(value) -> str:
    """A date as a sentence writes it: June 30, 2026."""
    day = value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])
    return f"{day:%B} {day.day}, {day.year}"


def as_of(now: dt.datetime) -> dt.date:
    """The day a run reads as of: now's date in UTC."""
    return now.astimezone(dt.UTC).date() if now.tzinfo else now.date()


def reader_of(source: ResearchSource) -> Reader:
    module, function = source.reader.split(":")
    return getattr(importlib.import_module(module), function)


def not_connected(source: ResearchSource, project: ProjectFacts, fetch: Fetch, engine: Engine | None,
                  now: dt.datetime) -> SourceResult:
    """The reader of a source Prism does not connect: no item, and the registry's reason."""
    return SourceResult(source.key, [], False, NOT_CONNECTED, source.limitations[0])


def read(source: ResearchSource, project: ProjectFacts, fetch: Fetch, engine: Engine | None,
         now: dt.datetime) -> SourceResult:
    """What one source says about the project, as of now."""
    if not source.enabled:
        return not_connected(source, project, fetch, engine, now)
    try:
        result = reader_of(source)(source, project, fetch, engine, now)
    except Refused as refused:
        return SourceResult(source.key, [], False, refused.status, refused.note)
    except Unreachable as unreachable:
        return SourceResult(source.key, [], False, "unreachable",
                            f"Prism could not reach {source.label} ({unreachable.reason}).")
    except EngineError as error:
        return SourceResult(source.key, [], False, "unreadable",
                            f"Prism could not read {source.label} from the lakehouse ({str(error)[:160]}).")
    if not result.reached:
        result.items = []
    for item in result.items:
        missing = [key for key in ITEM_KEYS if key not in item]
        if missing:
            raise ValueError(f"The {source.key} reader made an item without {', '.join(missing)}.")
    return result
