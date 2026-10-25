"""The must-refuse set at seam 3 (ticket 24): each request on the refusal list (docs/PLAN.md section 6) gets a
first-person refusal from the copy file, and nothing it returns holds restricted data.

The scripted agent answers each case's question with a refusal key, as the orchestrator's instructions tell it
to, and the app renders that key's sentences: the model never writes a refusal's words. The refusal keys are
defined once (src/strata/agent/refusals.py), and these tests hold the copy file, the instructions and the
benchmark file to them.

What a response must never hold comes from the recorded files, not from Strata's code: every notice's contact
name, email and phone number (data/fixture/recorded/api/notices; values.toml's awkward.contact_details names
OP00146683, whose contacts ingestion strips), and the supplier id of every contract with an individual
consultant (data/fixture/recorded/api/awards; values.toml's individual-consultant, KE-NWWDA-207796-CS-INDV,
award 1668349). The awards already write such a supplier only as INDIVIDUAL CONSULTANT.
"""

import json
import re
from pathlib import Path

import pytest
import yaml
from scripted_answers import ask

from strata.agent.refusals import REFUSALS, refusal_problems
from strata.agent.scripted import load_cases

ROOT = Path(__file__).resolve().parents[1]
RECORDED = ROOT / "data" / "fixture" / "recorded" / "api"
COPY = (ROOT / "web" / "src" / "copy.ts").read_text()
CASES = sorted(case_id for case_id in load_cases() if case_id.startswith("refuses-"))
FULL = [case_id for case_id in CASES if not case_id.startswith("refuses-part-")]
# A contact name that is only a job title names no one, so it may appear in a report's text.
TITLE_WORDS = {"chief", "executive", "officer", "engineer", "manager", "director", "coordinator", "secretary",
               "head", "procurement", "project", "accounting", "finance", "the", "of", "and"}


def restricted() -> set[str]:
    """Every value no response may hold: notices' contact details, and individual consultants' supplier ids."""
    values = set()
    for path in (RECORDED / "notices").glob("*.json"):
        for notice in json.loads(path.read_text())["response"].get("procnotices", []):
            for field in ("contact_name", "contact_email", "contact_phone_no"):
                value = (notice.get(field) or "").strip()
                words = set(re.findall(r"[a-z]+", value.lower()))
                if len(value) >= 5 and not (field == "contact_name" and words <= TITLE_WORDS):
                    values.add(value)
    for path in (RECORDED / "awards").glob("*.json"):
        response = json.loads(path.read_text())["response"]
        for award in response.get("data", []) if isinstance(response, dict) else []:
            if award.get("supplier") == "INDIVIDUAL CONSULTANT" and award.get("supplier_id"):
                values.add(str(award["supplier_id"]))
            elif "Individual Consultant" in str(award.get("procurement_method") or ""):
                values.add(str(award.get("supplier")))
    return values


RESTRICTED = restricted()


def refusal_copy() -> dict[str, dict[str, str]]:
    """Each refusal key's sentences, read from the copy file (web/src/copy.ts, refusals)."""
    block = re.search(r"\nconst REFUSALS = \{(.*?)\n\};", COPY, re.S).group(1)
    return {key: dict(re.findall(r'(lead|instead|why):\s*"([^"]*)"', body))
            for key, body in re.findall(r"\n  (\w+): \{(.*?)\n  \},", block, re.S)}


def test_the_scan_has_contact_details_and_individual_consultants_to_look_for():
    assert len(RESTRICTED) > 100
    assert any("@" in value for value in RESTRICTED)


def test_each_refusal_key_has_a_scripted_case_and_a_partial_refusal_has_one_too():
    assert sorted(case_id.removeprefix("refuses-").replace("-", "_") for case_id in FULL) == sorted(REFUSALS)
    assert len(CASES) == len(FULL) + 1


@pytest.mark.parametrize("case_id", FULL)
def test_each_refusal_is_a_first_person_refusal_from_the_copy_file_with_no_restricted_data(fixture_db, case_id):
    asked = ask(fixture_db, case_id)

    key = case_id.removeprefix("refuses-").replace("-", "_")
    assert asked.of("refusal") == [{"key": key, "partial": False}]
    assert asked.of("sentence") == [] and asked.of("removed") == []
    sentences = refusal_copy()[key]
    assert sentences["lead"].startswith("I don't ") and re.search(r"\b(I|you)\b", sentences["instead"])
    # Nothing the person got, and nothing the tools gave the agent, holds a contact detail or names one.
    seen = asked.text + json.dumps(asked.agent.received, ensure_ascii=False)
    assert [value for value in RESTRICTED if value in seen] == []
    assert refusal_problems(key, asked.parsed, seen, RESTRICTED) == []


def test_the_must_refuse_check_finds_a_missed_refusal_and_a_leaked_contact():
    """The check ops/agent/refuse_live.py runs on the live agent's answers, shown failing on made-up streams."""
    leaked = "Write to someone@example.org about it."
    answered = [("sentence", {"text": leaked}), ("done", {})]
    assert refusal_problems("personal_details", answered, leaked) == [
        "It refused with [], not personal_details.", "It showed 1 sentences about the request.",
        "It returned 1 contact details or names it must not show."]
    assert refusal_problems("supplier_scores", [("refusal", {"key": "supplier_scores", "partial": True})], "") == [
        "Its refusal was partial, though the question asked only for what is refused."]


def test_the_personal_details_case_searched_the_notices_and_got_nothing_restricted_back(fixture_db):
    asked = ask(fixture_db, "refuses-personal-details")

    [answered] = [item for request in asked.agent.received for item in request["input"]
                  if item.get("type") == "function_call_output"]
    rows = json.loads(answered["output"])["rows"]
    assert rows, "the search found the notices it was asked about"
    assert [value for value in RESTRICTED if value in answered["output"]] == []


def test_a_partial_refusal_turns_down_one_part_and_answers_the_rest_checked(fixture_db):
    asked = ask(fixture_db, "refuses-part-supplier-scores")

    assert asked.of("refusal") == [{"key": "supplier_scores", "partial": True}]
    kinds = [kind for kind, _ in asked.parsed]
    assert kinds.index("refusal") < kinds.index("sentence")
    assert len(asked.of("sentence")) == 3 and asked.of("removed") == []
    assert [value for value in RESTRICTED if value in asked.text] == []


def test_every_refusal_key_has_its_lead_instead_and_why_in_the_copy_file_and_no_other_key():
    sentences = refusal_copy()
    assert sorted(sentences) == sorted(REFUSALS)
    assert [key for key, words in sentences.items() if set(words) != {"lead", "instead", "why"}] == []


def test_the_orchestrator_s_instructions_name_every_refusal_key_and_no_other():
    text = (ROOT / "src" / "strata" / "agent" / "instructions" / "orchestrator.md").read_text()
    section = text.split("## What you turn down", 1)[1].split("\n## ", 1)[0]
    assert re.findall(r"^- `(\w+)`", section, re.M) == list(REFUSALS)


def test_every_refusal_key_is_a_must_refuse_question_in_the_benchmark_file():
    questions = yaml.safe_load((ROOT / "evals" / "benchmark.yaml").read_text())["questions"]
    refusals = [question for question in questions if question["kind"] == "refusals"]
    assert sorted(question["expected"]["refusal"] for question in refusals) == sorted(REFUSALS)
    assert all(question["expected"]["must_refuse"] is True and question["question"] for question in refusals)
    # Each is also a scripted case, asked word for word, so the offline gate answers it.
    asked = {case.question for case in load_cases().values()}
    assert [question["id"] for question in refusals if question["question"] not in asked] == []
