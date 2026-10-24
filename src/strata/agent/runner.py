"""The runner the app answers with: the Foundry agent, when the app's environment names it.

On the Databricks App, the app reaches the Foundry agent as its own service principal in Microsoft Entra
ID, never as the viewer: the agent only decides, and every tool it asks for runs in the app with the
viewer's own token (ADR 0003). The environment names the principal:

- FOUNDRY_PROJECT_ENDPOINT   the Foundry project, such as https://wb-strata.services.ai.azure.com/api/projects/Strata
- FOUNDRY_TENANT_ID          the Entra tenant
- FOUNDRY_CLIENT_ID and FOUNDRY_CLIENT_SECRET   the app's principal, which needs the Azure AI User role on
                             the project. The wizard does not make it yet (see the ticket's parked decisions).

Without all four, or without a data service for the tools, there is no runner, and /api/ask says there is
no agent.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping

from strata.agent.foundry import FOUNDRY_SCOPE, FoundryAgent, Token, entra_token
from strata.agent.loop import answer_runner
from strata.config import load_agent, load_draft_kinds
from strata.harness.turn import Runner
from strata.server.engines import EngineFor

NEEDS = ("FOUNDRY_PROJECT_ENDPOINT", "FOUNDRY_TENANT_ID", "FOUNDRY_CLIENT_ID", "FOUNDRY_CLIENT_SECRET")


def _foundry(environ: Mapping[str, str]) -> tuple[str, Token] | None:
    """The Foundry project's endpoint and the app principal's token, or None when the environment lacks any of
    the four values."""
    values = {key: environ.get(key, "").strip() for key in NEEDS}
    if not all(values.values()):
        return None
    token = entra_token(values["FOUNDRY_TENANT_ID"], values["FOUNDRY_CLIENT_ID"], values["FOUNDRY_CLIENT_SECRET"],
                        FOUNDRY_SCOPE)
    return values["FOUNDRY_PROJECT_ENDPOINT"], token


def writers_from_environment(environ: Mapping[str, str]) -> Callable[[str], FoundryAgent | None]:
    """Each draft kind's writer: the Foundry agent its entry in config/drafts.toml names, as the app's own
    principal, or None for every kind when the environment names no Foundry project."""
    foundry = _foundry(environ)
    if foundry is None:
        return lambda kind: None
    endpoint, token = foundry
    kinds = load_draft_kinds()

    def writer(kind: str) -> FoundryAgent | None:
        entry = kinds.kinds.get(kind)
        return FoundryAgent(endpoint, load_agent(entry.agent), token) if entry else None
    return writer


def agent_from_environment(environ: Mapping[str, str], key: str) -> Callable[[], FoundryAgent | None]:
    """One Foundry agent by its key in config/agents.toml, such as the package reader (ticket 15), as the app's
    own principal, or None when the environment names no Foundry project."""
    foundry = _foundry(environ)
    if foundry is None:
        return lambda: None
    endpoint, token = foundry
    spec = load_agent(key)
    return lambda: FoundryAgent(endpoint, spec, token)


def lesson_writer_from_environment(environ: Mapping[str, str]) -> Callable[[], FoundryAgent | None]:
    """The lesson review writer (config/agents.toml, lesson_review_writer), as the app's own principal, or
    None when the environment names no Foundry project (ticket 29)."""
    foundry = _foundry(environ)
    if foundry is None:
        return lambda: None
    endpoint, token = foundry
    return lambda: FoundryAgent(endpoint, load_agent("lesson_review_writer"), token)


def from_environment(environ: Mapping[str, str], engine_for: EngineFor | None) -> Runner | None:
    foundry = _foundry(environ)
    if engine_for is None or foundry is None:
        return None
    endpoint, token = foundry
    spec = load_agent("orchestrator")
    return answer_runner(lambda turn: FoundryAgent(endpoint, spec, token), engine_for)
