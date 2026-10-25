"""Reading a server-sent event stream back into its events, as the screen does: the answer stream's recordings, the
must-refuse checks (tests/scripted_answers.py, ops/agent/refuse_live.py) and anything else that reads a stream
the app sent."""

from __future__ import annotations

import json


def events(text: str) -> list[tuple[str, dict]]:
    """The stream's (type, data) pairs, in order, without its keep-alive comments."""
    parsed = []
    for block in text.strip().split("\n\n"):
        kind, data = "message", None
        for line in block.splitlines():
            if line.startswith("event: "):
                kind = line[len("event: "):]
            elif line.startswith("data: "):
                data = json.loads(line[len("data: "):])
        if data is not None:
            parsed.append((kind, data))
    return parsed
