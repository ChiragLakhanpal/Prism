"""The shield set: five real passages that hold rule-like sentences reach the agent as tool results, and a
content filter or Prompt Shields refusal on any of them fails the check (evals/shield_passages.toml).

Offline, the tool results come from search_passages on the fixture database, and stand-ins answer for the
agent. ops/agent/shields_live.py sends the same results to the live Foundry agent.
"""

import datetime as dt

import pytest

from strata.agent import shields
from strata.agent.loop import AgentError
from strata.agent.verifier import find_quote
from strata.dbx import Viewer
from strata.lakehouse.engine import DuckDBEngine

AS_OF = dt.date(2026, 10, 23)


@pytest.fixture
def results(fixture_db):
    with DuckDBEngine.open(fixture_db, read_only=True) as engine:
        return {passage.evidence_id: shields.tool_result(passage, engine, Viewer(name="test"), AS_OF)
                for passage in shields.load_passages()}


def test_the_set_holds_five_real_passages_each_found_by_its_own_rule_like_sentence(results):
    passages = shields.load_passages()

    assert len(passages) == 5
    for passage in passages:
        rows = results[passage.evidence_id]["rows"]
        assert [row["evidence_id"] for row in rows] == [passage.evidence_id]
        assert find_quote(passage.sentence, rows[0]["text"]) is not None


class Asks:
    """A stand-in agent that calls search_passages, then answers; refuse_on names a request it refuses."""

    name, version = "strata-orchestrator", None

    def __init__(self, refuse_on=None):
        self.refuse_on, self.requests = refuse_on, []

    def respond(self, items, previous_response_id):
        self.requests.append(items)
        if len(self.requests) == self.refuse_on:
            raise AgentError("content_filter", "Prompt Shields found an indirect attack.")
        if previous_response_id is None:
            return {"id": "resp_1", "output": [{"type": "function_call", "call_id": "call_1",
                                                "name": "search_passages", "arguments": "{}"}]}
        return {"id": "resp_2", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": '{"claims": []}'}]}]}


def test_every_passage_goes_to_the_agent_as_a_tool_result_and_passes(results):
    agents = []

    def agent_for():
        agents.append(Asks())
        return agents[-1]

    outcomes = shields.check(shields.load_passages(), results, agent_for, AS_OF)

    assert [outcome.status for outcome in outcomes] == ["passed"] * 5
    sent = agents[0].requests[1][0]
    assert sent["type"] == "function_call_output" and "The GOR shall ensure" in sent["output"]
    assert shields.summary(outcomes).startswith("All 5 passages reached the agent")


def test_a_prompt_shields_refusal_on_a_tool_result_fails_the_check(results):
    outcomes = shields.check(shields.load_passages(), results, lambda: Asks(refuse_on=2), AS_OF)

    assert {outcome.status for outcome in outcomes} == {"refused"}
    assert "5 of 5 passages were refused" in shields.summary(outcomes)
