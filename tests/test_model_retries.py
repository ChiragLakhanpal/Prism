"""A model call that Azure refuses as busy is tried again before a sentence is removed or an answer fails (ticket 118).

Since October 27, 2026 the agent and the verifier's judge share the gpt-5.4 deployment and its cap of 30,000 tokens a
minute. On October 28, 2026 at 05:54 UTC the judge's call got `429 Your requests to gpt-5.4 for gpt-5.4 in eastus have
exceeded token rate limit`, and the smoke question lost its sentence with judge_unavailable. Now each adapter waits the
seconds Azure's Retry-After header names, or config/thresholds.toml's [azure] retry_seconds, and tries again, up to
azure.retries times, before it gives up as before. These tests ask over HTTP (seam 3) with the live adapters on fake
transports: the judge on Azure OpenAI's chat completions, and the agent on Foundry's Responses API. A fake clock stands
in for the waits, so no test sleeps.
"""

import json
from pathlib import Path

import pytest

from scripted_answers import ask
from strata.agent.foundry import FoundryAgent, FoundryError
from strata.agent.judge import AzureOpenAIJudge, JudgeError
from strata.agent.retries import Retries
from strata.agent.scripted import JUDGED, RECORDED_STREAMS, RECORDED_TRACES
from strata.config import load_agent, load_thresholds

API = Path(__file__).parent / "fixtures" / "api"
# The words Azure OpenAI answered the judge with on October 28, 2026 at 05:54 UTC (docs/workspace-catchup.md, the block
# "Ticket 117, steps 1 and 2 ran"), in the error shape its API documents.
RATE_LIMITED = json.dumps({"error": {"code": "rate_limit_exceeded", "message": (
    "Your requests to gpt-5.4 for gpt-5.4 in eastus have exceeded token rate limit.")}})
JUDGED_CASE = "ke-nwwda-541055-past-range"  # an answer with a sentence only the judge can prove
AZURE = load_thresholds().value("azure")
# The ticket's starting values, for the tests that count tries and waits, so config/thresholds.toml's [azure] can move
# without breaking them (CLAUDE.md rule 9). The tests that give no retries= read the shipped [azure].
TICKET = Retries(retries=3, retry_seconds=5, max_retry_seconds=60, max_wait_seconds=120)


class FakeClock:
    """Records each wait asked for, and never sleeps."""

    def __init__(self):
        self.waits = []

    def sleep(self, seconds):
        self.waits.append(seconds)


def judge_refused(status, headers=None):
    """What the judge's transport raises when Azure OpenAI refuses the call, as the live one does."""
    return JudgeError(f"Azure OpenAI answered {status}: {RATE_LIMITED if status == 429 else 'Forbidden'}",
                      status=status, headers=headers or {})


class AzureOpenAIFake:
    """Azure OpenAI's chat completions behind the judge's transport: each try takes the next answer, a refusal or
    the case's recorded judge answer."""

    def __init__(self, *answers):
        self.answers, self.tries = list(answers), 0

    def __call__(self, url, headers, body):
        self.tries += 1
        answer = self.answers.pop(0)
        if isinstance(answer, Exception):
            raise answer
        return answer


def recorded_judge_answer(case_id=JUDGED_CASE):
    return json.loads((JUDGED / f"{case_id}.json").read_text())["response"]


def judged_sentences(case_id=JUDGED_CASE):
    """The sentence only the judge can prove, "Another, KE-ICTA-571738-CW-RFB, was still open too.", which states no
    number, date or quote for checks 1 to 3 to match, as the case's recorded judge answer was asked it."""
    return json.loads((JUDGED / f"{case_id}.json").read_text())["asked"]


def live_judge(transport, clock, **options):
    return AzureOpenAIJudge("https://judge.example.invalid", "not-a-real-key", "gpt-5.4", post=transport,
                            sleep=clock.sleep, **options)


def waits_logged(caplog):
    return [record.getMessage() for record in caplog.records if "so I am waiting" in record.getMessage()]


# ── The judge ────────────────────────────────────────────────────────────

def test_a_judge_refused_twice_with_429_then_answered_keeps_its_sentences_after_two_logged_waits(fixture_db, caplog):
    """The ticket's case: two 429s, then the judge's answer. The answer streams as recorded, its judged sentence kept."""
    caplog.set_level("WARNING")
    clock = FakeClock()
    azure = AzureOpenAIFake(judge_refused(429, {"Retry-After": "7"}), judge_refused(429, {"retry-after-ms": "2500"}),
                            recorded_judge_answer())

    asked = ask(fixture_db, JUDGED_CASE, judge=live_judge(azure, clock), trace_ids=lambda: RECORDED_TRACES)

    assert asked.of("removed") == []
    assert set(judged_sentences()) < {sentence["text"] for sentence in asked.of("sentence")}
    assert asked.text == (API / RECORDED_STREAMS[JUDGED_CASE]).read_text()
    assert azure.tries == 3 and clock.waits == [7, 2.5]
    assert waits_logged(caplog) == [
        f"The judge on Azure OpenAI answered 429, so I am waiting 7 seconds before retry 1 of {AZURE['retries']}.",
        f"The judge on Azure OpenAI answered 429, so I am waiting 2.5 seconds before retry 2 of {AZURE['retries']}."]


def test_a_judge_refused_four_times_removes_its_sentences_as_judge_unavailable_after_three_waits(fixture_db, caplog):
    """Four 429s that name no wait: the judge waits retry_seconds before each of its 3 retries, then gives up, and
    the verifier removes the sentences it had to judge, as it did before ticket 118."""
    caplog.set_level("WARNING")
    clock = FakeClock()
    azure = AzureOpenAIFake(*[judge_refused(429) for _ in range(4)])

    asked = ask(fixture_db, JUDGED_CASE, judge=live_judge(azure, clock, retries=TICKET))

    assert [(item["sentence"], item["reason"]) for item in asked.of("removed")] == [
        (sentence, "judge_unavailable") for sentence in judged_sentences()]
    assert asked.of("checks")[0]["judge"]["responded"] is False and asked.of("error") == []
    assert azure.tries == 4 and clock.waits == [5, 5, 5]
    assert [line.split("before ")[1] for line in waits_logged(caplog)] == [
        "retry 1 of 3.", "retry 2 of 3.", "retry 3 of 3."]


def test_a_judge_refused_with_403_gives_up_at_once(fixture_db, caplog):
    """A refusal that waiting cannot fix, such as a 403 for a key the deployment does not accept, is never tried
    again."""
    caplog.set_level("WARNING")
    clock = FakeClock()
    azure = AzureOpenAIFake(judge_refused(403, {"Retry-After": "7"}), recorded_judge_answer())

    asked = ask(fixture_db, JUDGED_CASE, judge=live_judge(azure, clock))

    assert [item["reason"] for item in asked.of("removed")] == ["judge_unavailable"]
    assert azure.tries == 1 and clock.waits == [] and waits_logged(caplog) == []


def test_a_503_is_tried_again_and_no_wait_passes_max_retry_seconds_nor_all_of_them_max_wait_seconds(fixture_db, caplog):
    """Azure names ten minutes each time. Each wait is cut to max_retry_seconds (60 here), and a third would take the
    answer's waits on the judge past max_wait_seconds (120 here), so the judge stops there with retries left."""
    caplog.set_level("WARNING")
    clock = FakeClock()
    azure = AzureOpenAIFake(judge_refused(503, {"Retry-After": "600"}), judge_refused(429, {"Retry-After": "600"}),
                            judge_refused(429, {"Retry-After": "600"}), recorded_judge_answer())

    asked = ask(fixture_db, JUDGED_CASE, judge=live_judge(azure, clock, retries=TICKET))

    assert azure.tries == 3 and clock.waits == [60, 60]
    assert [item["reason"] for item in asked.of("removed")] == ["judge_unavailable"]
    assert waits_logged(caplog)[0] == (
        "The judge on Azure OpenAI answered 503, so I am waiting 60 seconds before retry 1 of 3.")
    assert "would pass the 120 seconds one answer may wait, so I stopped trying." in caplog.text


def http_refusal(url, status, headers):
    """urllib's HTTPError for a refused call, with the answer's headers, as urlopen raises it."""
    import email.message
    import io
    import urllib.error

    message = email.message.Message()
    for name, value in headers.items():
        message[name] = value
    body = RATE_LIMITED if status == 429 else '{"error": {"code": "PermissionDenied"}}'
    return urllib.error.HTTPError(url, status, "", message, io.BytesIO(body.encode()))


def test_the_judges_http_transport_hands_azures_status_and_wait_to_the_retries(monkeypatch):
    """http_post is the judge's one live transport, through strata.knowledge.http's post_json: urllib's HTTPError
    carries the status and the headers, so a 429's retry-after-ms reaches the wait."""
    import io

    from strata.agent.judge import Question

    statuses, sent = iter([429, 429, 200]), []

    def urlopen(request, timeout):
        sent.append((request.full_url, timeout))
        if next(statuses) == 429:
            raise http_refusal(request.full_url, 429, {"retry-after-ms": "1500", "Retry-After": "1"})
        return io.BytesIO(json.dumps(recorded_judge_answer()).encode())

    monkeypatch.setattr("urllib.request.urlopen", urlopen)
    clock = FakeClock()
    judge = AzureOpenAIJudge("https://judge.example.invalid/openai/v1", "not-a-real-key", "gpt-5.4", sleep=clock.sleep)

    # The judge answers by each sentence's index in the answer, and the judged one is its third, index 2.
    found = judge.judge([Question(index, sentence, ()) for index, sentence in enumerate(judged_sentences(), 2)])

    assert [judgement.follows for judgement in found] == [True]
    assert clock.waits == [1.5, 1.5] and len(sent) == 3
    assert sent[0] == ("https://judge.example.invalid/openai/v1/chat/completions",
                       load_thresholds().value("verifier.judge_timeout_seconds"))


# ── The agent ────────────────────────────────────────────────────────────

AGENT_CASE = "p130164-rebidding"  # the showcase answer: a search_passages call, then the answer citing ICR ¶54
FOUNDRY = "https://wb-strata.services.ai.azure.com/api/projects/Strata"


def foundry_refused(status, headers=None):
    """What FoundryAgent's HTTP call raises when Foundry refuses the request, as the live one does."""
    return FoundryError(status, RATE_LIMITED if status == 429 else '{"error": {"code": "PermissionDenied"}}',
                        headers=headers or {})


class FoundryFake:
    """Foundry's Responses API behind FoundryAgent's HTTP call. Before each request it answers it raises the refusals
    planned for that request (1 is the run's first call, 2 the call that sends the tool's output), then answers with
    the case's next recorded response, through the scripted agent, which checks the request continues the last."""

    def __init__(self, case_id, refusals):
        from strata.agent.scripted import ScriptedAgent, load_cases

        self.scripted = ScriptedAgent(load_cases()[case_id])
        self.refusals = {request: list(planned) for request, planned in refusals.items()}
        self.tries = 0

    def __call__(self, method, url, headers, body):
        self.tries += 1
        planned = self.refusals.get(len(self.scripted.received) + 1)
        if planned:
            raise planned.pop(0)
        return self.scripted.respond(body["input"], body.get("previous_response_id"))


def live_agent(foundry, clock, **options):
    return FoundryAgent(FOUNDRY, load_agent("orchestrator"), lambda: "not-a-real-token", call=foundry,
                        traceparent=lambda: None, sleep=clock.sleep, **options)


def test_the_agents_run_and_tool_output_calls_each_refused_with_429_still_give_the_recorded_answer(fixture_db, caplog):
    """A 429 on the run's first call and another on the call that sends search_passages' output: the agent waits
    the seconds Foundry names before each, and the answer streams byte for byte as the recorded one."""
    caplog.set_level("WARNING")
    clock = FakeClock()
    foundry = FoundryFake(AGENT_CASE, {1: [foundry_refused(429, {"Retry-After": "11"})],
                                       2: [foundry_refused(429, {"retry-after-ms": "4000"})]})

    asked = ask(fixture_db, AGENT_CASE, agent=live_agent(foundry, clock), trace_ids=lambda: RECORDED_TRACES)

    assert asked.of("error") == [] and asked.of("removed") == []
    assert asked.text == (API / RECORDED_STREAMS[AGENT_CASE]).read_text()
    assert foundry.tries == 4 and clock.waits == [11, 4]
    assert waits_logged(caplog) == [
        f"The agent on Foundry answered 429, so I am waiting 11 seconds before retry 1 of {AZURE['retries']}.",
        f"The agent on Foundry answered 429, so I am waiting 4 seconds before retry 1 of {AZURE['retries']}."]


def test_an_agent_call_refused_four_times_ends_the_answer_with_agent_unavailable_after_three_waits(fixture_db, caplog):
    caplog.set_level("WARNING")
    clock = FakeClock()
    foundry = FoundryFake(AGENT_CASE, {1: [foundry_refused(429) for _ in range(4)]})

    asked = ask(fixture_db, AGENT_CASE, agent=live_agent(foundry, clock, retries=TICKET))

    assert asked.of("error") == [{"code": "agent_unavailable"}] and asked.of("sentence") == []
    assert foundry.tries == 4 and clock.waits == [5, 5, 5]
    assert [line.split("before ")[1] for line in waits_logged(caplog)] == [
        "retry 1 of 3.", "retry 2 of 3.", "retry 3 of 3."]


def test_an_agent_call_refused_with_403_ends_the_answer_with_agent_unavailable_at_once(fixture_db, caplog):
    caplog.set_level("WARNING")
    clock = FakeClock()
    foundry = FoundryFake(AGENT_CASE, {1: [foundry_refused(403, {"Retry-After": "11"})]})

    asked = ask(fixture_db, AGENT_CASE, agent=live_agent(foundry, clock))

    assert asked.of("error") == [{"code": "agent_unavailable"}]
    assert foundry.tries == 1 and clock.waits == [] and waits_logged(caplog) == []


def test_the_agents_calls_in_one_answer_share_max_wait_seconds_through_foundrys_http_transport(monkeypatch):
    """http_call is FoundryAgent's one live transport: urllib's HTTPError carries the status and the Retry-After
    header. Foundry names 60 seconds three times over the answer's two calls; the first two waits use up the 120
    seconds one answer may wait on the agent here, so the second call gives up with retries left, as
    agent_unavailable."""
    import io

    from strata.agent import foundry as live
    from strata.agent.loop import AgentError

    statuses, sent = iter([429, 200, 429, 429]), []

    def urlopen(request, timeout):
        sent.append(request.full_url)
        if next(statuses) == 429:
            raise http_refusal(request.full_url, 429, {"Retry-After": "60"})
        return io.BytesIO(json.dumps({"id": "resp_1", "output": []}).encode())

    monkeypatch.setattr(live.urllib.request, "urlopen", urlopen)
    clock = FakeClock()
    agent = FoundryAgent(FOUNDRY, load_agent("orchestrator"), lambda: "not-a-real-token", traceparent=lambda: None,
                         retries=TICKET, sleep=clock.sleep)

    assert agent.respond([], None)["id"] == "resp_1"
    with pytest.raises(AgentError) as unavailable:
        agent.respond([], "resp_1")

    assert unavailable.value.code == "agent_unavailable" and "429" in str(unavailable.value)
    assert clock.waits == [60, 60] and len(sent) == 4


def test_the_tries_and_the_waits_come_from_the_thresholds_files_azure_section(tmp_path, fixture_db):
    """[azure] in config/thresholds.toml is their one home (CLAUDE.md rule 9): here a file that allows one retry, a
    default wait of 2 seconds, a longest wait of 3 and 10 seconds in all, so two 429s remove the judged sentences after
    one wait of 2 seconds, and a Retry-After of 30 is cut to 3."""
    from strata.agent.retries import Retries

    (tmp_path / "thresholds.toml").write_text(
        "[azure]\nretries = 1\nretry_seconds = 2\nmax_retry_seconds = 3\nmax_wait_seconds = 10\n")
    retries = Retries.from_thresholds(load_thresholds(tmp_path / "thresholds.toml"))
    clock = FakeClock()
    azure = AzureOpenAIFake(judge_refused(429), judge_refused(429), recorded_judge_answer())

    asked = ask(fixture_db, JUDGED_CASE, judge=live_judge(azure, clock, retries=retries))

    assert [item["reason"] for item in asked.of("removed")] == ["judge_unavailable"]
    assert azure.tries == 2 and clock.waits == [2]
    assert retries.wait({"Retry-After": "30"}) == 3
    assert retries.wait({"Retry-After": "Wed, 28 Oct 2026 06:00:00 GMT"}) == 2  # a date names no seconds


@pytest.mark.parametrize("azure_section", [
    "retries = -1\nretry_seconds = 5\nmax_retry_seconds = 60\nmax_wait_seconds = 120\n",
    "retries = 3\nretry_seconds = 5\nmax_retry_seconds = -60\nmax_wait_seconds = 120\n"])
def test_an_azure_section_with_negative_retries_or_waits_is_refused(tmp_path, azure_section):
    from strata.agent.retries import Retries
    from strata.config import ConfigError

    (tmp_path / "thresholds.toml").write_text(f"[azure]\n{azure_section}")

    with pytest.raises(ConfigError, match=r"\[azure\] needs retries and waits of 0 or more"):
        Retries.from_thresholds(load_thresholds(tmp_path / "thresholds.toml"))
