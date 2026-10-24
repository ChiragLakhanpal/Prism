"""The agent sync: the orchestrator's instructions, model, tools and guardrail live in the repo, and the
sync makes the Foundry agent match them (docs/PLAN.md section 6).

The offline adapter is a Foundry project kept in memory. The live adapter, the Foundry project's REST
API and Azure's RAI policies, runs on the workspace with ops/agent/sync.py.
"""

import re
import shutil

from strata.agent import sync
from strata.agent.definition import AGENTS_FILE, agent_definition, load_agent
from strata.agent.foundry import LocalFoundry
from strata.tools import registry


def test_the_agents_tools_and_the_tool_section_of_its_instructions_come_from_the_registry():
    wanted = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")

    definition = wanted["definition"]
    assert definition["tools"] == registry.agent_tools()
    tools_section = definition["instructions"].split("## Your tools", 1)[1]
    assert [tool["name"] for tool in registry.agent_tools() if f"### {tool['name']}" in tools_section] == [
        tool["name"] for tool in registry.agent_tools()]
    # The thresholds file allows three rounds of tool calls (agent.tool_rounds).
    assert "at most 3 rounds of tool calls" in definition["instructions"]
    assert definition["model"] == "gpt-5.4-mini"  # config/models.toml, the agent role


def test_the_instructions_name_the_summary_record_wherever_a_tool_returns_one():
    """A tool that declares summary_fields returns its derived figures, such as a past range, as one citable
    record. The agent must be told it may cite it, or it leaves those figures out or cites rows that hold
    them only by chance (CLAUDE.md rules 1 and 2)."""
    from strata.config import load_tools

    summarized = [name for name, tool in load_tools().items() if tool.result.summary_fields]
    instructions = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")[
        "definition"]["instructions"]
    rules, tools_section = instructions.split("## Your tools", 1)

    assert summarized == ["find_comparables"]
    assert "Cite the summary for those figures, as you cite a row." in tools_section
    assert "the evidence_id of each row, summary or passage the sentence rests on" in rules
    assert "If a figure you need is not a value in a row or a summary, leave it out." in rules
    for name in summarized:
        described = tools_section.split(f"### {name}", 1)[1].split("\n### ", 1)[0]
        assert "summary, which you cite for them" in described


def test_the_instructions_give_the_agent_design_md_s_rules_for_the_words_a_person_reads():
    """The agent's sentences reach the page, and the copy lint reads only the copy file, so the agent is
    told DESIGN.md section 7's rules itself: rule 19's words, read here from DESIGN.md, and rules 3, 4,
    8 and 12."""
    wanted = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")
    words = wanted["definition"]["instructions"].split("## Words", 1)[1].split("\n## ", 1)[0]
    design = (AGENTS_FILE.parent.parent / "DESIGN.md").read_text()
    rule_19 = re.search(r"^19\. Never write: (.*?)\. Write", design, re.M).group(1)
    never = [word.strip() for word in re.split(r"[,;]", re.sub(r"\(.*?\)", "", rule_19))]

    assert len(never) == 14
    assert [word for word in never if not re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", words)] == []
    for rule in ('"the Bank"', "no em dashes", "no exclamation marks", "past tense", "one to nine in words",
                 "10 and up in numerals"):
        assert rule in words


def test_the_guardrail_puts_content_filters_and_prompt_shields_on_the_question_and_the_tool_results():
    foundry = LocalFoundry()
    sync.run(foundry)

    agent = foundry.agent("strata-orchestrator")
    policy = agent["definition"]["rai_config"]["rai_policy_name"]
    assert policy == foundry.guardrail_id("strata-guardrail")
    filters = {(item["name"], item["source"]): item for item in
               foundry.guardrail("strata-guardrail")["properties"]["contentFilters"]}
    shields = [filters[("Jailbreak", "Prompt")], filters[("Indirect Attack", "Prompt")]]
    assert all(item["enabled"] and item["blocking"] for item in shields)
    assert all(filters[(name, source)]["blocking"] for name in ("Hate", "Sexual", "Violence", "Selfharm")
               for source in ("Prompt", "Completion"))


def test_after_the_sync_runs_a_second_run_reports_no_difference():
    foundry = LocalFoundry()

    first = sync.run(foundry)
    second = sync.run(foundry)

    assert first.changed and first.version == "1"
    assert not second.changed and second.version == "1"
    assert second.differences == []
    assert "no difference" in second.text()
    assert len(foundry.versions["strata-orchestrator"]) == 1


def test_a_changed_instruction_shows_in_the_diff_and_makes_a_new_version(tmp_path):
    foundry = LocalFoundry()
    sync.run(foundry)
    instructions = tmp_path / "instructions"
    shutil.copytree(AGENTS_FILE.parent.parent / "src" / "strata" / "agent" / "instructions", instructions)
    changed = instructions / "orchestrator.md"
    changed.write_text(changed.read_text() + "\nKeep each sentence under 30 words.\n")

    report = sync.run(foundry, instructions_folder=instructions)

    assert report.changed and report.version == "2"
    assert "+Keep each sentence under 30 words." in report.text()
    assert sync.run(foundry, instructions_folder=instructions).differences == []


def test_a_check_reports_a_difference_and_changes_nothing():
    foundry = LocalFoundry()

    report = sync.run(foundry, apply=False)

    assert report.differences and not report.changed
    assert foundry.agent("strata-orchestrator") is None and foundry.guardrail("strata-guardrail") is None
