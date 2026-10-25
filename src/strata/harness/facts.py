"""The evidence one turn has seen: every row and passage a tool returned, by evidence id.

The app runs every tool, so it holds what an answer may cite (ADR 0003). The verifier
accepts only ids that came back in the current turn, so each turn starts with an empty
Facts and never shares it.

It also keeps each abstention a tool returned this turn (the envelope's abstention, such as
check_plan's version_not_public): a summary that cites nothing may say what a tool could not
answer, and the verifier judges it against these alone (src/strata/agent/verifier.py, check 4).
"""

from collections.abc import Mapping
from typing import Any


class Facts:
    def __init__(self) -> None:
        self._rows: dict[str, Mapping[str, Any]] = {}
        self._tools: dict[str, str | None] = {}
        self._abstentions: list[tuple[str, Mapping[str, Any]]] = []

    def record(self, evidence_id: str, row: Mapping[str, Any], tool: str | None = None) -> None:
        """Keep a row or passage a tool returned this turn, with the tool that returned it."""
        self._rows[evidence_id] = row
        self._tools[evidence_id] = tool

    def abstained(self, tool: str, abstention: Mapping[str, Any]) -> None:
        """Keep an abstention a tool returned this turn: its reason and whatever it said with it."""
        self._abstentions.append((tool, abstention))

    def abstentions(self) -> list[tuple[str, Mapping[str, Any]]]:
        """Every abstention a tool returned this turn, with the tool's name, in the order kept."""
        return list(self._abstentions)

    def tool(self, evidence_id: str) -> str | None:
        """The tool that returned this evidence id in this turn."""
        return self._tools.get(evidence_id)

    def came_back(self, evidence_id: str) -> bool:
        """Whether a tool returned this evidence id in this turn."""
        return evidence_id in self._rows

    def get(self, evidence_id: str) -> Mapping[str, Any] | None:
        return self._rows.get(evidence_id)

    def returned_by(self, tool: str) -> list[tuple[str, Mapping[str, Any]]]:
        """Every row and passage this tool returned in this turn, by evidence id, in the order kept."""
        return [(evidence_id, row) for evidence_id, row in self._rows.items() if self._tools.get(evidence_id) == tool]

    def __len__(self) -> int:
        return len(self._rows)
