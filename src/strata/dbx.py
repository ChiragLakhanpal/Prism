"""Who is asking: the viewer identity a Databricks App forwards with each request.

Prism runs as each viewer (ADR 0003). The App's proxy adds the viewer's email, user name,
user id and access token to every request it passes on. Each request builds its own
Viewer from those headers, and nothing about a viewer is kept in a module global
(CLAUDE.md rule 7). Written from the description of fairshare's dbx.py in docs/PLAN.md
section 12, because fairshare could not be read on the build machine.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field

EMAIL = "x-forwarded-email"
NAME = "x-forwarded-preferred-username"
USER_ID = "x-forwarded-user"
TOKEN = "x-forwarded-access-token"


@dataclass(frozen=True)
class Viewer:
    """One person's identity for one request. The token never appears in a repr or a log line."""

    email: str | None = None
    name: str | None = None
    user_id: str | None = None
    token: str | None = field(default=None, repr=False)

    @property
    def signed_in(self) -> bool:
        return bool(self.email or self.user_id)


def viewer_from_headers(headers: Mapping[str, str]) -> Viewer:
    """The viewer a request's forwarded headers name. With no headers, no one is signed in."""
    lowered = {key.lower(): value.strip() for key, value in headers.items() if value and value.strip()}
    email = lowered.get(EMAIL)
    return Viewer(email=email, name=lowered.get(NAME) or email, user_id=lowered.get(USER_ID), token=lowered.get(TOKEN))
