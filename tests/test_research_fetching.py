"""Ticket 147: how deep research reaches a source (src/strata/research/fetching.py).

The live fetch sends Prism's named agent and never a browser's; the offline fetch replays the recordings and refuses
any address it has no file for; the pacing waits between two calls to one source; the cache answers within the
source's cache_hours, kept in the research cache table. A refusal is recognised by its status or its bot check page.
Every clock here is injected, so no test sleeps."""

import datetime as dt
import io
import urllib.error

import pytest
from research_world import NOV_5, RECORDED, Clock, answers, research_tables

from strata.research import fetching

UA = "prism-research/0.1 (+https://github.com/ChiragLakhanpal/Prism)"


def test_the_live_fetch_sends_the_named_agent_and_hands_back_a_refusal_as_an_answer():
    sent = []

    class Response(io.BytesIO):
        status, headers = 200, {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def opener(request, timeout):
        sent.append((request.full_url, request.get_header("User-agent"), timeout))
        if "refuses" in request.full_url:
            raise urllib.error.HTTPError(request.full_url, 403, "Forbidden", {"Content-Type": "text/html"},
                                         io.BytesIO(b"no"))
        return Response(b"{}")

    fetch = fetching.live(opener=opener)

    assert fetch("https://example.org/a", headers={"User-Agent": "Mozilla/5.0"}) == (
        200, {"content-type": "application/json"}, b"{}")
    assert fetch("https://example.org/refuses")[0] == 403
    assert [agent for _, agent, _ in sent] == [UA, UA]
    assert sent[0][2] == 30


def test_an_unreachable_host_raises_unreachable_with_the_reason():
    def opener(request, timeout):
        raise urllib.error.URLError("Name or service not known")

    with pytest.raises(fetching.Unreachable, match="Name or service not known"):
        fetching.live(opener=opener)("https://nowhere.example/")


def test_the_offline_fetch_replays_a_recording_and_refuses_an_address_it_has_none_for():
    fetch = fetching.offline(RECORDED)

    status, headers, body = fetch("https://www.inspectionpanel.org/panel-cases/data")
    assert status == 200 and b"extractCases" in body and headers["content-type"].startswith("text/html")
    with pytest.raises(fetching.NotRecorded, match="no recording of https://example.org/never"):
        fetch("https://example.org/never")


def test_every_research_recording_says_what_answered_when_and_to_which_client():
    import json

    files = sorted(RECORDED.glob("*/*.json"))
    assert len(files) > 40
    for path in files:
        entry = json.loads(path.read_text())
        assert path.parent.name == entry["source"] and path.name == fetching.recording_name(entry["url"]), path
        assert entry["url"].startswith("https://") and entry["recorded"] == "2026-11-05", path
        assert entry["read_with"] == UA and entry["license"], path
        assert "unreachable" in entry or isinstance(entry["status"], int), path


def test_two_calls_to_one_source_wait_its_pace_and_another_source_does_not_wait():
    clock = Clock()
    pacer = fetching.Pacer(clock.monotonic, clock.sleep)
    fetch = answers(("https://a.example/1", (200, "one")), ("https://a.example/2", (200, "two")),
                    ("https://b.example/1", (200, "three")))
    gdelt, other = fetching.paced(fetch, "gdelt_news", 5, pacer), fetching.paced(fetch, "mastodon", 1, pacer)

    gdelt("https://a.example/1")
    clock.now += 2
    gdelt("https://a.example/2")
    other("https://b.example/1")

    assert clock.slept == [3.0]


@pytest.mark.parametrize("cache", ["memory", "table"])
def test_the_cache_answers_within_cache_hours_and_asks_again_after(cache):
    engine = research_tables() if cache == "table" else None
    store = fetching.MemoryCache() if cache == "memory" else fetching.TableCache(lambda: engine.cursor())
    now = {"at": NOV_5}
    fetch = answers(("https://a.example/feed", (200, "<rss/>")))
    cached = fetching.cached(fetch, "outlet_feeds", 6, store, lambda: now["at"])

    first = cached("https://a.example/feed")
    now["at"] = NOV_5 + dt.timedelta(hours=5)
    again = cached("https://a.example/feed")
    now["at"] = NOV_5 + dt.timedelta(hours=7)
    cached("https://a.example/feed")

    assert first == again and again[2] == b"<rss/>"
    assert fetch.calls == ["https://a.example/feed", "https://a.example/feed"]


def test_a_refusal_is_never_kept_in_the_cache():
    store = fetching.MemoryCache()
    fetch = answers(("https://a.example/", (429, "slow down")))
    cached = fetching.cached(fetch, "gdelt_news", 12, store, lambda: NOV_5)

    cached("https://a.example/")
    cached("https://a.example/")

    assert len(fetch.calls) == 2


@pytest.mark.parametrize("status, body, says", [
    (429, b"Please limit requests", "429"),
    (403, b"Forbidden", "403"),
    (200, b"<html><title>Just a moment...</title></html>", "bot check"),
    (503, b"<title>Attention Required! | Cloudflare</title>", "bot check"),
])
def test_a_refusal_is_known_by_its_status_or_its_bot_check_page(status, body, says):
    assert fetching.refusal((status, {}, body)) == says


def test_an_ordinary_answer_is_no_refusal():
    assert fetching.refusal((200, {}, b"<rss><channel></channel></rss>")) is None
