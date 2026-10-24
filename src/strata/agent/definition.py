"""A Foundry agent's definition, built from the repo: the agent registry (config/agents.toml), the agent's
instructions file, the model file and the tool registry.

- agent_definition() is the prompt agent as Foundry keeps it: its model deployment, its instructions with
  a section listing every tool, the tool list itself (strata.tools.registry.agent_tools), and the guardrail
  it runs under. Adding a tool to config/tools.toml adds it to both.
- guardrail_policy() is the guardrail as an RAI policy on the Foundry resource: content filters on the
  question and on the answer, and Prompt Shields on the question (a prompt attack) and on what the tools
  return (an indirect attack).

Nothing here calls Foundry; strata.agent.sync compares these with what Foundry holds.
"""

from __future__ import annotations

import re
from pathlib import Path

from strata.config import (CONFIG_DIR, AgentSpec, Guardrail, Thresholds, Tool, load_agent, load_models,
                           load_thresholds, load_tools)
from strata.tools import registry

__all__ = ["AGENTS_FILE", "AgentSpec", "agent_definition", "guardrail_policy", "instructions", "load_agent"]
AGENTS_FILE = CONFIG_DIR / "agents.toml"
INSTRUCTIONS = Path(__file__).resolve().parent / "instructions"
HARMS = ("Hate", "Sexual", "Violence", "Selfharm")
SOURCES = ("Prompt", "Completion")  # the question and the tool results, then the answer
SHIELDS = ("Jailbreak", "Indirect Attack")  # a prompt attack in the question, an attack in a tool result
THRESHOLD = re.compile(r"\{([a-z_]+(?:\.[a-z_]+)+)\}")


def instructions(spec: AgentSpec, folder: Path = INSTRUCTIONS, tools: dict[str, Tool] | None = None,
                 thresholds: Thresholds | None = None) -> str:
    """The agent's instructions: its file, with each threshold it names filled in, then one section that
    lists every tool in the registry with its description. When a tool returns a summary record, the
    section says the agent may cite it."""
    limits = thresholds or load_thresholds()
    registered = tools if tools is not None else load_tools()
    text = (folder / spec.instructions).read_text().rstrip()
    text = THRESHOLD.sub(lambda match: str(limits.value(match.group(1))), text)
    offered = agent_tools(spec, registered, limits)
    if not offered:  # a writer with no tools writes from the facts in its message
        return text + "\n"
    listed = [f"### {tool['name']}\n\n{tool['description']}" for tool in offered]
    lead = ("Each tool is read-only and runs as the person who asked. Its result has rows, each with its "
            "evidence_id, public_from date and source line, a coverage line and, when it gives no rows, an "
            "abstention with its reason.")
    names = {tool["name"] for tool in offered}
    if any(tool.result.summary_fields for tool in registered.values() if tool.name in names):
        lead += (" A tool may also return a summary: one record with its own evidence_id that holds figures "
                 "worked out from the rows, such as a past range or a count. Cite the summary for those "
                 "figures, as you cite a row.")
    return "\n\n".join([text, "## Your tools", lead, *listed]) + "\n"


def agent_tools(spec: AgentSpec, tools: dict[str, Tool] | None = None, thresholds: Thresholds | None = None) -> list[dict]:
    """The tools the agent is offered: every tool in the registry, or only those its entry names."""
    every = registry.agent_tools(tools, thresholds)
    return every if spec.tools is None else [tool for tool in every if tool["name"] in spec.tools]


def agent_definition(spec: AgentSpec, guardrail_id: str, folder: Path = INSTRUCTIONS,
                     tools: dict[str, Tool] | None = None, thresholds: Thresholds | None = None) -> dict:
    """The prompt agent's version as Foundry keeps it, for the agent registry's entry."""
    return {
        "definition": {
            "kind": "prompt",
            "model": load_models()[spec.role].deployment,
            "instructions": instructions(spec, folder, tools, thresholds),
            "tools": agent_tools(spec, tools if tools is not None else load_tools(), thresholds),
            "rai_config": {"rai_policy_name": guardrail_id},
        },
        "description": spec.description,
    }


def guardrail_policy(guardrail: Guardrail) -> dict:
    """The guardrail as an RAI policy: content filters on the question, tool results and answer, and
    Prompt Shields on the question and tool results, each blocking."""
    filters = [{"name": harm, "source": source, "severityThreshold": guardrail.severity, "blocking": True,
                "enabled": True} for harm in HARMS for source in SOURCES]
    filters += [{"name": shield, "source": "Prompt", "blocking": guardrail.prompt_shields,
                 "enabled": guardrail.prompt_shields} for shield in SHIELDS]
    return {"properties": {"mode": "Blocking", "basePolicyName": guardrail.base_policy, "contentFilters": filters}}
