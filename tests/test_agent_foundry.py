"""The live Foundry adapters, offline: the requests they send and how they read the answers.

The answers are the recorded tool calls of tests/fixtures/agent and, for a refusal, an answer written by
hand in the shape Azure OpenAI documents (tests/fixtures/azure/responses_content_filter.json). A fake
Foundry project behind the adapters' HTTP call shows that the sync's second run over the live adapter finds
no difference, as it does over the offline one.
"""

import json
from pathlib import Path

import pytest

from strata.agent import sync
from strata.agent.foundry import FoundryAgent, FoundryError, FoundryProject
from strata.agent.loop import AgentError
from strata.config import load_agent

FIXTURES = Path(__file__).parent / "fixtures"
ENDPOINT = "https://wb-strata.services.ai.azure.com/api/projects/Strata"
ACCOUNT = "/subscriptions/sub-0001/resourceGroups/WorldBank-demo/providers/Microsoft.CognitiveServices/accounts/wb-strata"
SPEC = load_agent("orchestrator")


def recorded_response(number):
    return json.loads((FIXTURES / "agent" / "recorded" / "p130164-rebidding.json").read_text())["responses"][number]


def test_the_agent_is_asked_through_the_responses_api_by_reference_with_the_apps_trace():
    sent = []

    def call(method, url, headers, body):
        sent.append((method, url, headers, body))
        return recorded_response(1)

    agent = FoundryAgent(ENDPOINT, SPEC, lambda: "not-a-real-token", call=call,
                         traceparent=lambda: "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01")
    items = [{"type": "function_call_output", "call_id": "call_p130164_rebidding_1", "output": "{}"}]

    reply = agent.respond(items, "resp_p130164_rebidding_1")

    method, url, headers, body = sent[0]
    assert (method, url) == ("POST", f"{ENDPOINT}/openai/responses?api-version=2025-11-15-preview")
    assert headers["Authorization"] == "Bearer not-a-real-token"
    assert headers["traceparent"] == "00-4bf92f3577b34da6a3ce929d0e0e4736-00f067aa0ba902b7-01"
    assert body == {"agent": {"type": "agent_reference", "name": "strata-orchestrator"}, "input": items,
                    "previous_response_id": "resp_p130164_rebidding_1"}
    assert reply["id"] == "resp_p130164_rebidding_2"


def test_a_content_filter_refusal_is_its_own_error_and_any_other_failure_says_the_agent_is_unavailable():
    refusal = json.loads((FIXTURES / "azure" / "responses_content_filter.json").read_text())

    def refused(method, url, headers, body):
        raise FoundryError(refusal["status"], json.dumps(refusal["response"]))

    def down(method, url, headers, body):
        raise FoundryError(503, "Service Unavailable")

    with pytest.raises(AgentError) as filtered:
        FoundryAgent(ENDPOINT, SPEC, lambda: "not-a-real-token", call=refused, traceparent=lambda: None).respond([], None)
    with pytest.raises(AgentError) as unavailable:
        FoundryAgent(ENDPOINT, SPEC, lambda: "not-a-real-token", call=down, traceparent=lambda: None).respond([], None)

    assert (filtered.value.code, unavailable.value.code) == ("content_filter", "agent_unavailable")


def test_the_app_answers_through_the_foundry_agent_only_when_its_environment_names_one():
    from strata.agent.runner import from_environment

    named = {"FOUNDRY_PROJECT_ENDPOINT": ENDPOINT, "FOUNDRY_TENANT_ID": "tenant-0001",
             "FOUNDRY_CLIENT_ID": "client-0001", "FOUNDRY_CLIENT_SECRET": "not-a-real-secret"}

    def engine_for(viewer):
        raise AssertionError("No tool runs until a question is asked.")

    assert from_environment({}, engine_for) is None
    assert from_environment({**named, "FOUNDRY_CLIENT_SECRET": ""}, engine_for) is None
    assert from_environment(named, None) is None  # no data service, so no tool could run
    assert callable(from_environment(named, engine_for))


class FakeProject:
    """A Foundry project and its resource's RAI policies behind the HTTP call, kept in memory."""

    def __init__(self):
        self.agents, self.policies, self.calls = {}, {}, []

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url.split("?")[0]))
        path = url.split("?")[0]
        if "/raiPolicies/" in path:
            name = path.rsplit("/", 1)[1]
            if method == "PUT":
                self.policies[name] = {"id": path.removeprefix("https://management.azure.com"), **body}
            if name not in self.policies:
                raise FoundryError(404, "ResourceNotFound")
            return self.policies[name]
        name = path.split("/agents/")[1].split("/")[0]
        if method == "POST":
            versions = self.agents.setdefault(name, [])
            versions.append({"object": "agent.version", "version": str(len(versions) + 1), **body})
            return versions[-1]
        if name not in self.agents:
            raise FoundryError(404, "Agent not found")
        return {"object": "agent", "name": name, "versions": {"latest": self.agents[name][-1]}}


def test_over_the_live_adapter_the_second_sync_also_finds_no_difference():
    fake = FakeProject()
    project = FoundryProject(ENDPOINT, SPEC, lambda: "not-a-real-token", lambda: "not-a-real-token", ACCOUNT, call=fake)

    first, second = sync.run(project), sync.run(project)

    assert first.changed and first.version == "1"
    assert second.differences == [] and second.version == "1"
    assert ("PUT", f"https://management.azure.com{ACCOUNT}/raiPolicies/strata-guardrail") in fake.calls
    assert ("POST", f"{ENDPOINT}/agents/strata-orchestrator/versions") in fake.calls
    rai = fake.agents["strata-orchestrator"][0]["definition"]["rai_config"]["rai_policy_name"]
    assert rai == f"{ACCOUNT}/raiPolicies/strata-guardrail"
