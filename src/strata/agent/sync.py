"""The agent sync: make a Foundry agent and its guardrail match the repo (docs/PLAN.md section 6).

run() builds the agent's definition and its guardrail from the repo (strata.agent.definition), reads what
Foundry holds, and compares only what the repo sets: the model, the instructions, the tool list, the
guardrail the agent names, the description, and the guardrail's filters. Fields Foundry adds of its own,
such as a version's id, are ignored. When something differs, it updates the guardrail and makes a new
version of the agent, unless apply is False, as ops/agent/sync.py --check asks. A run right after a sync
finds no difference.

The report says what differed, with a unified diff of the instructions, so a change reads like a commit.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass, field
from pathlib import Path

from strata.agent.definition import INSTRUCTIONS, agent_definition, guardrail_policy
from strata.agent.foundry import Foundry
from strata.config import CONFIG_DIR, Thresholds, Tool, load_agent, load_models

AGENT_KEYS = ("type", "name", "description", "parameters")  # what the repo sets on each tool


@dataclass
class Report:
    agent: str
    guardrail: str
    version: str | None
    differences: list[str] = field(default_factory=list)
    diff: list[str] = field(default_factory=list)
    changed: bool = False

    def text(self) -> str:
        if not self.differences:
            return (f"Foundry's agent {self.agent}, version {self.version}, matches the repo: there is no difference "
                    f"in its model, instructions, tools, description or guardrail ({self.guardrail}).\n")
        lines = [f"Foundry's agent {self.agent} differed from the repo:" if self.changed
                 else f"Foundry's agent {self.agent} differs from the repo:"]
        lines += [f"- {difference}" for difference in self.differences]
        lines += self.diff
        lines.append(f"I made version {self.version} of {self.agent}, which matches the repo." if self.changed
                     else "Run the sync without --check to make Foundry match the repo.")
        return "\n".join(lines) + "\n"


def _agent_view(version: dict | None) -> dict | None:
    """What the repo sets on an agent's version, and nothing Foundry adds."""
    if version is None:
        return None
    definition = version.get("definition") or {}
    return {
        "model": definition.get("model"),
        "instructions": definition.get("instructions"),
        "tools": [{key: tool.get(key) for key in AGENT_KEYS} for tool in definition.get("tools") or []],
        "guardrail": (definition.get("rai_config") or {}).get("rai_policy_name"),
        "description": version.get("description"),
    }


def _policy_view(policy: dict | None) -> dict | None:
    if policy is None:
        return None
    properties = policy.get("properties") or {}
    filters = sorted((item.get("name"), item.get("source"), item.get("severityThreshold"), bool(item.get("blocking")),
                      bool(item.get("enabled"))) for item in properties.get("contentFilters") or [])
    return {"mode": properties.get("mode"), "base": properties.get("basePolicyName"), "filters": filters}


LABELS = {"model": "its model deployment", "instructions": "its instructions", "tools": "its tools",
          "guardrail": "the guardrail it names", "description": "its description"}


def plan(path: Path = CONFIG_DIR / "agents.toml") -> list[tuple[str, str]]:
    """Every agent the sync makes in Foundry, read from the agent registry alone, as (its key, what it is): its
    name, the deployment its role runs on and the guardrail it runs under. The demo-ready command's dry run prints
    it (ops/demo/ready.py --fresh-workspace), one sync per agent, so its list cannot drift from the registry."""
    import tomllib

    models = load_models()
    found = []
    for key in tomllib.loads(path.read_text()).get("agents", {}):
        spec = load_agent(key, path)
        tools = "every tool" if spec.tools is None else f"{len(spec.tools)} tools" if spec.tools else "no tools"
        found.append((key, f"{spec.name} on {models[spec.role].deployment}, with {tools}, under the guardrail "
                           f"{spec.guardrail.name}"))
    return found


def run(foundry: Foundry, key: str = "orchestrator", apply: bool = True, instructions_folder: Path = INSTRUCTIONS,
        tools: dict[str, Tool] | None = None, thresholds: Thresholds | None = None) -> Report:
    """Compare the repo's agent and guardrail with Foundry's, and make Foundry match when apply is True."""
    spec = load_agent(key)
    policy = guardrail_policy(spec.guardrail)
    wanted = agent_definition(spec, foundry.guardrail_id(spec.guardrail.name), instructions_folder, tools,
                              thresholds)
    have = foundry.agent(spec.name)
    report = Report(spec.name, spec.guardrail.name, have.get("version") if have else None)

    policy_differs = _policy_view(foundry.guardrail(spec.guardrail.name)) != _policy_view(policy)
    if policy_differs:
        report.differences.append(f"The guardrail {spec.guardrail.name} is missing or has other filters.")
    want_view, have_view = _agent_view(wanted), _agent_view(have)
    if have_view is None:
        report.differences.append(f"Foundry has no agent {spec.name} yet.")
    else:
        report.differences += [f"It has other values in {LABELS[name]}." for name in LABELS
                               if want_view[name] != have_view[name]]
    agent_differs = have_view != want_view
    if agent_differs:
        before = (have_view or {}).get("instructions") or ""
        report.diff = [line.rstrip("\n") for line in difflib.unified_diff(
            before.splitlines(keepends=True), want_view["instructions"].splitlines(keepends=True),
            fromfile=f"Foundry: {spec.name}" + (f" version {report.version}" if report.version else ""),
            tofile=f"repo: {instructions_folder.name}/{spec.instructions}")]
    if apply and policy_differs:
        foundry.put_guardrail(spec.guardrail.name, policy)
        report.changed = True
    if apply and agent_differs:
        report.version = foundry.create_version(spec.name, wanted)["version"]
        report.changed = True
    return report
