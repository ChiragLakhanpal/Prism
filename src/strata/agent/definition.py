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
    lists every tool in the registry with its description."""
    limits = thresholds or load_thresholds()
    text = (folder / spec.instructions).read_text().rstrip()
    text = THRESHOLD.sub(lambda match: str(limits.value(match.group(1))), text)
    listed = [f"### {tool['name']}\n\n{tool['description']}" for tool in registry.agent_tools(tools, limits)]
    return "\n\n".join([text, "## Your tools", "Each tool is read-only and runs as the person who asked. "
                        "Its result has rows, each with its evidence_id, public_from date and source line, a "
                        "coverage line and, when it gives no rows, an abstention with its reason.", *listed]) + "\n"


def agent_definition(spec: AgentSpec, guardrail_id: str, folder: Path = INSTRUCTIONS,
                     tools: dict[str, Tool] | None = None, thresholds: Thresholds | None = None) -> dict:
    """The prompt agent's version as Foundry keeps it, for the agent registry's entry."""
    return {
        "definition": {
            "kind": "prompt",
            "model": load_models()[spec.role].deployment,
            "instructions": instructions(spec, folder, tools, thresholds),
            "tools": registry.agent_tools(tools if tools is not None else load_tools(), thresholds),
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
