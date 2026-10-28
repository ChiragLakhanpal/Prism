"""The agent sync: the orchestrator's instructions, model, tools and guardrail live in the repo, and the
sync makes the Foundry agent match them (docs/PLAN.md section 6).

The offline adapter is a Foundry project kept in memory. The live adapter, the Foundry project's REST
API and Azure's RAI policies, runs on the workspace with ops/agent/sync.py.
"""

import json
import re
import shutil

from strata import config
from strata.agent import definition as agent_file
from strata.agent import sync
from strata.agent.definition import AGENTS_FILE, agent_definition, load_agent
from strata.agent.claims import parse_answer
from strata.agent.foundry import LocalFoundry
from strata.agent.verifier import verify
from strata.config import load_models
from strata.harness.facts import Facts
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
    # The agent role's deployment in config/models.toml, the one place a model is swapped (the change drill).
    assert definition["model"] == load_models()["agent"].deployment


def test_the_instructions_name_the_summary_record_wherever_a_tool_returns_one():
    """A tool that declares summary_fields returns its derived figures, such as a past range, as one citable
    record. The agent must be told it may cite it, or it leaves those figures out or cites rows that hold
    them only by chance (CLAUDE.md rules 1 and 2)."""
    from strata.config import load_tools

    summarized = [name for name, tool in load_tools().items() if tool.result.summary_fields]
    instructions = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")[
        "definition"]["instructions"]
    rules, tools_section = instructions.split("## Your tools", 1)

    assert "find_comparables" in summarized
    assert "Cite the summary for those figures, as you cite a row." in tools_section
    assert "the evidence_id of each row, summary or passage the sentence rests on" in rules
    assert "If a figure you need is not a value in a row or a summary, leave it out." in rules
    for name in summarized:
        described = tools_section.split(f"### {name}", 1)[1].split("\n### ", 1)[0]
        assert "summary, which you cite for them" in described


def test_the_instructions_say_a_record_inside_a_row_is_cited_by_its_own_evidence_id():
    """get_disagreements returns each side of a disagreement as a record of its own (nested_rows), get_lessons each
    quote a lesson rests on (ticket 30), compare_criteria each requirement's notice passage (ticket 31), and
    rebidding_risk each record that says a package was advertised again (ticket 28), so the agent is told it may
    cite such a record, and quote it only from its text (CLAUDE.md rule 2)."""
    from strata.config import load_tools

    nested = [name for name, tool in load_tools().items() if tool.result.nested_rows]
    instructions = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")[
        "definition"]["instructions"]
    tools_section = instructions.split("## Your tools", 1)[1]

    # project_signals (ticket 37) returns the records each signal rests on the same way.
    assert nested == ["project_signals", "get_lessons", "get_disagreements", "compare_criteria", "rebidding_risk"]
    assert "Cite such a record by its evidence_id, and quote it only from its text." in tools_section


def test_the_agent_is_told_which_words_go_with_the_plan_s_share():
    """"About 1 in 10" and "fewer than 1 in 10" state the same numbers, so find_comparables returns the words
    with them, and its description tells the agent what each code says (CLAUDE.md rule 1)."""
    instructions = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")[
        "definition"]["instructions"]
    described = instructions.split("### find_comparables", 1)[1].split("\n### ", 1)[0]

    for code, phrase in (("fewer_than", "fewer than 1 in 10"), ("about", "about N in 10"),
                         ("more_than", "more than 9 in 10")):
        assert f'{code} for "{phrase}"' in described


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
    # One rule says which quote marks to use, straight double ones; the words rule only says where none go (ticket
    # 13's review round 5, P3), so no line reads as leave to use single ones.
    instructions = wanted["definition"]["instructions"]
    assert "in straight double quotes in the sentence, in every language" in instructions
    assert "Put no quote marks, double or single, around words you do not quote word for word." in words
    assert "of any kind" not in instructions


def test_the_instructions_show_one_worked_quote_claim_that_passes_the_verifier_and_say_to_copy_the_quote_exactly():
    """Ticket 109: on October 27, 2026 the live agent found the passage the smoke question needs, then wrote its sentence
    in its own words, or capitalized the quote's first word, and the verifier removed it both times. So the
    instructions show one worked quote claim instead of an abstract shape: the passage's text, then a claim whose
    sentence holds the passage's words in straight double quotes and whose quote.text is those same words. The worked
    claim must pass the verifier's checks 1 to 3 against that passage, or it teaches the agent a claim the app
    removes."""
    instructions = agent_definition(load_agent("orchestrator"), guardrail_id="local/strata-guardrail")[
        "definition"]["instructions"]
    rules = instructions.split("## Your tools", 1)[0]
    [shown] = [line for line in rules.splitlines() if line.startswith('{"claims": [{')]
    [passage] = [line[2:] for line in rules.splitlines() if line.startswith("> ")]
    [claim] = json.loads(shown)["claims"]
    evidence_id = claim["quote"]["passage_id"]
    words = claim["quote"]["text"]
    facts = Facts()
    facts.record(evidence_id, {"evidence_id": evidence_id, "passage_id": evidence_id.split(":", 1)[1],
                               "text": passage}, tool="search_passages")

    assert "Copy the quote exactly as the passage writes it, starting at a word, with its own first letter." in rules
    assert (claim["kind"], claim["evidence_ids"]) == ("quote", [evidence_id])
    assert f'"{words}"' in claim["sentence"] and words in passage
    verdict = verify(parse_answer(shown).claims, facts)
    assert [sentence.reasons for sentence in verdict.sentences] == [()]
    assert verdict.counts()["quotes"] == {"total": 1, "found": 1}


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


def test_swapping_the_agents_model_is_one_line_and_the_next_sync_changes_only_its_model(tmp_path, monkeypatch):
    """The change drill's "Swap the model" (docs/change-drill.md): one line in a copy of config/models.toml, and
    the next sync finds the agent's model deployment changed and nothing else, and makes a new version."""
    foundry = LocalFoundry()
    sync.run(foundry)
    text = (config.CONFIG_DIR / "models.toml").read_text()
    current = load_models()["agent"].deployment
    line = f'deployment = "{current}"'
    assert text.count(line) == 1, "the agent's deployment line is not one line of config/models.toml"
    swapped = tmp_path / "models.toml"
    swapped.write_text(text.replace(line, f'deployment = "{current}-swapped"'))
    monkeypatch.setattr(agent_file, "load_models", lambda: config.load_models(swapped))

    report = sync.run(foundry)

    assert report.differences == ["It has other values in its model deployment."]
    assert report.changed and report.version == "2"
    assert foundry.agent("strata-orchestrator")["definition"]["model"] == f"{current}-swapped"


def test_a_check_reports_a_difference_and_changes_nothing():
    foundry = LocalFoundry()

    report = sync.run(foundry, apply=False)

    assert report.differences and not report.changed
    assert foundry.agent("strata-orchestrator") is None and foundry.guardrail("strata-guardrail") is None


def test_the_review_notes_writer_runs_on_the_drafting_model_with_no_tools_and_design_md_s_words():
    """Ticket 35's writer writes from the plan rows the app hands it, so Foundry offers it no tool, and its
    notes go into a Word file, so it is told rule 19's words and the document's voice."""
    wanted = agent_definition(load_agent("review_notes_writer"), guardrail_id="local/strata-guardrail")

    definition = wanted["definition"]
    assert definition["tools"] == []
    assert "## Your tools" not in definition["instructions"]
    assert definition["model"] == "gpt-5.4"  # config/models.toml, the draft role
    words = definition["instructions"].split("## Words", 1)[1]
    design = (AGENTS_FILE.parent.parent / "DESIGN.md").read_text()
    rule_19 = re.search(r"^19\. Never write: (.*?)\. Write", design, re.M).group(1)
    never = [word.strip() for word in re.split(r"[,;]", re.sub(r"\(.*?\)", "", rule_19))]
    assert [word for word in never if not re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", words)] == []
    assert 'never "I" or "you"' in words


def test_the_sync_makes_the_writer_in_foundry_and_a_second_run_finds_no_difference():
    foundry = LocalFoundry()

    first = sync.run(foundry, "review_notes_writer")
    second = sync.run(foundry, "review_notes_writer", apply=False)

    assert first.changed and foundry.agent("strata-review-notes-writer")["definition"]["tools"] == []
    assert second.differences == []
