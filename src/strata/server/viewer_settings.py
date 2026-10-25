"""The language of answers and drafts each viewer gets (ticket 42; the 42 design brief, section 6.1).

The first of these that applies wins:

1. ?lang= in the page's address, read by strata.languages.from_link: any case, a region ("fr-CA", "pt_BR") or a
   three-letter code ("fra"). A link never changes the saved choice.
2. The viewer's saved choice, the latest row of strata.ops.viewer_settings, which the app writes as its own service
   principal when the viewer chooses a language in the view popover.
3. The working language of the viewer's team in config/roles.toml ([teams.<key>] working_language).
4. English.

The screens stay in English whatever the choice: only the writer's sentences follow it.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from strata.config import ENGLISH
from strata.lakehouse.engine import Engine

SQL = Path(__file__).resolve().parent / "sql" / "viewer_settings"


def _query(name: str) -> str:
    return (SQL / f"{name}.sql").read_text()


class SettingsStore:
    """Each viewer's saved choices. engine() opens the engine that reads and writes them, as the app."""

    def __init__(self, engine: Callable[[], Engine]):
        self.engine = engine

    def _run(self, name: str, params: dict):
        engine = self.engine()
        try:
            return engine.run(_query(name), params)
        finally:
            close = getattr(engine, "close", None)
            if callable(close):
                close()

    def saved_language(self, viewer_id: str) -> str | None:
        rows = self._run("saved", {"viewer_id": viewer_id}).rows
        return str(rows[0][0]) if rows else None

    def save_language(self, viewer_id: str, code: str, at: dt.datetime) -> None:
        self._run("save", {"viewer_id": viewer_id, "working_language": code,
                           "changed_at": at.astimezone(dt.UTC).replace(tzinfo=None)})


@dataclass(frozen=True)
class WorkingLanguage:
    """The language in effect and where it came from (link, saved, team or default), the saved choice and the team's
    language, and what the link asked for: its language, "unknown" for a value no working language matches, or None."""

    code: str
    source: str
    saved: str | None
    team: str | None
    link: str | None

    def as_dict(self) -> dict:
        return asdict(self)


def working_language(link: str | None, saved: str | None, team: str | None) -> WorkingLanguage:
    """The first of the link's language, the saved choice, the team's and English (the module's docstring)."""
    from strata import languages

    asked = languages.from_link(link) if link else None
    shown_link = None if not link else (asked or "unknown")
    for code, source in ((asked, "link"), (saved, "saved"), (team, "team")):
        if code:
            return WorkingLanguage(code, source, saved, team, shown_link)
    return WorkingLanguage(ENGLISH, "default", saved, team, shown_link)
