"""Ticket 147: the deep research readers that read the web, over the recordings of November 5, 2026
(data/fixture/recorded/research/, made by ops/research/record.py with Prism's named client), with the network off.

Each turns its recording into items of the one shape, with a stable evidence id, a public_from, an address a person
can open and contact details stripped. A refusal (403, 429, a bot check page) or a host Prism cannot reach gives
reached False, the status and a one-sentence note, and never an item."""

import dataclasses
import re

import pytest
from research_world import NOV_5, RECORDED, answers

from strata.config import load_research
from strata.research import fetching
from strata.research.items import ITEM_KEYS
from strata.research.project import project_facts
from strata.research.sources import read

STAR_SOLAR = ("https://www.the-star.co.ke/counties/coast/2026-01-14-solar-water-project-set-to-cut-power-costs-"
              "improve-supply-in-kilifi")
EASTLEIGH = ("https://eastleighvoice.co.ke/coast/196147/mombasa-water-project-sparks-outrage-in-mwembe-tayari-over-job-"
             "promises,-disruptions")


@pytest.fixture(scope="module")
def project():
    return project_facts("P156634")


@pytest.fixture(scope="module")
def recorded():
    return fetching.offline(RECORDED)


def source(key):
    return load_research()[key]


def one_sentence(note: str) -> bool:
    return note.endswith(".") and note.count(". ") == 0


def well_formed(item, key):
    assert set(item) == set(ITEM_KEYS)
    assert item["evidence_id"].startswith(f"strata.research.item:P156634/{key}/")
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["public_from"])
    assert item["url"].startswith("https://")
    assert not re.search(r"[\w.]+@[\w-]+\.[a-z]{2,}", item["text"] + (item["author"] or ""))
    assert len(item["text"]) <= 4000 and item["title"] and "\n" not in item["title"]


def test_gdelt_s_429_reaches_nothing_and_says_gdelt_limited_calls(project, recorded):
    result = read(source("gdelt_news"), project, recorded, None, NOV_5)

    assert (result.reached, result.status, result.items) == (False, "429", [])
    assert result.note == "GDELT limited calls from this network."


def test_gdelt_s_query_quotes_the_project_s_names_and_its_places_with_water():
    from strata.research.sources.gdelt_news import query

    asked = query(project_facts("P156634"), 24)

    assert asked.startswith('("Water and Sanitation Development Project" OR "CWWDA" OR ')
    assert '"NWWDA"' in asked and '"MOWASSCO"' in asked and '"Wajir water"' in asked
    assert asked.count('"') == 48


def test_the_inspection_panel_register_names_no_case_for_the_project_and_one_for_a_project_it_lists(project, recorded):
    none = read(source("inspection_panel"), project, recorded, None, NOV_5)
    other = read(source("inspection_panel"), dataclasses.replace(project, project_id="P153836"), recorded, None, NOV_5)

    assert (none.reached, none.items) == (True, [])
    assert none.note == "The Inspection Panel's register lists 197 cases, 0 of them naming P156634."
    assert [item["evidence_id"] for item in other.items] == ["strata.research.item:P153836/inspection_panel/1086"]
    assert other.items[0]["title"].startswith("High Priority Roads Reopening and Maintenance")
    assert other.items[0]["url"] == "https://www.inspectionpanel.org/node/1086"
    assert other.items[0]["date_known"] is False and other.items[0]["public_from"] == "2026-11-05"


def test_the_sentinel_grids_are_two_years_of_nine_tiles_around_each_location_and_fetch_nothing(project):
    def never(url, *, headers=None):
        raise AssertionError(f"the mosaic reader fetched {url}")

    result = read(source("sentinel2_mosaic"), project, never, None, NOV_5)

    baricho = next(item for item in result.items if item["location"]["geo_loc_id"] == "200577")
    assert baricho["evidence_id"] == "strata.research.item:P156634/sentinel2_mosaic/200577-2018-2025"
    first, last = baricho["image_urls"]
    assert len(first) == len(last) == 9
    assert first[4] == "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2018_3857/default/g/15/16666/20005.jpg"
    assert last[0] == "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/g/15/16665/20004.jpg"
    assert baricho["url"] == last[4] and baricho["public_from"] == "2025-12-31"
    assert "Prism reads no pixels" in baricho["text"]
    assert len(result.items) == 18
    for item in result.items:
        well_formed(item, "sentinel2_mosaic")


def test_mastodon_keeps_only_posts_that_name_a_place_or_agency_with_a_sector_word(project, recorded):
    result = read(source("mastodon"), project, recorded, None, NOV_5)

    assert result.reached and result.status == "200"
    assert "strata.research.item:P156634/mastodon/109425868094219767" in [item["evidence_id"] for item in result.items]
    for item in result.items:
        well_formed(item, "mastodon")
        assert re.search(r"\b(?:water|sewer|borehole|sanitation|dam)\w*", item["text"], re.I), item["evidence_id"]
        assert item["author"] and "@" not in item["author"].lstrip("@")
    # The posts that name Mombasa with no sector word, about its music, come in on the tag alone and stay out.
    assert not [item for item in result.items if "Mombasa Vikings" in item["text"]]


def test_the_outlet_feeds_read_seven_feeds_and_say_the_star_gives_none(project, recorded):
    result = read(source("outlet_feeds"), project, recorded, None, NOV_5)

    assert result.reached and result.status == "200"
    assert result.note.startswith("Prism read 7 of 8 feeds")
    assert "The Star's feed address answered a web page, not a feed." in result.note


FEED = f"""<?xml version="1.0"?><rss version="2.0"><channel><title>A test feed, written by hand</title>
<item><title>Solar water project set to cut power costs, improve supply in Kilifi</title><link>{STAR_SOLAR}</link>
<pubDate>Wed, 14 Jan 2026 08:00:00 +0300</pubDate><description>CWWDA unveils a solar plant at Baricho.</description></item>
<item><title>Mombasa water project sparks outrage in Mwembe Tayari</title><link>{EASTLEIGH}</link>
<description>Residents say MOWASSCO began trench works without notice. Call 0722 123 456.</description></item>
<item><title>Mombasa derby ends in a draw</title><link>https://www.example.org/sport</link>
<description>A football match in Mombasa.</description></item>
</channel></rss>"""


def test_a_kept_entry_s_page_gives_its_paragraphs_and_a_page_that_refuses_gives_the_feed_s_summary(project, recorded):
    star = dataclasses.replace(source("outlet_feeds"), feeds=(dataclasses.replace(source("outlet_feeds").feeds[0],
                                                                                   url="https://feed.example/rss"),))

    def fetch(url, *, headers=None):
        return (200, {"content-type": "application/rss+xml"}, FEED.encode()) if url == "https://feed.example/rss" \
            else recorded(url)

    result = read(star, project, fetch, None, NOV_5)

    solar, outrage = result.items
    assert solar["evidence_id"] == ("strata.research.item:P156634/outlet_feeds/"
                                    + fetching.recording_name(STAR_SOLAR).removesuffix(".json"))
    assert solar["published"] == solar["public_from"] == "2026-01-14"
    assert "Residents of Kilifi County are set to benefit" in solar["text"]
    assert solar["location"]["name"] == "Kilifi" and solar["author"] == "The Star"
    assert outrage["text"] == "Residents say MOWASSCO began trench works without notice. Call [contact removed]."
    assert outrage["date_known"] is False and outrage["public_from"] == "2026-11-05"
    assert "could not be read, so the feed's own summary stands in" in result.note
    for item in result.items:
        well_formed(item, "outlet_feeds")


@pytest.mark.parametrize("status, body, says", [
    (403, b"Forbidden", "Inspection Panel answered 403 to Prism's named client"),
    (429, b"Too many requests", "World Bank Inspection Panel limited calls from this network."),
    (200, b"<html><head><title>Just a moment...</title></head></html>", "answered with a bot check page"),
])
def test_a_refusal_gives_no_item_and_a_one_sentence_note(project, status, body, says):
    fetch = answers(("https://www.inspectionpanel.org/panel-cases/data", (status, body)))

    result = read(source("inspection_panel"), dataclasses.replace(project, project_id="P153836"), fetch, None, NOV_5)

    assert (result.reached, result.items) == (False, [])
    assert result.status == ("bot check" if status == 200 else str(status))
    assert says in result.note and one_sentence(result.note)


def test_an_unreachable_host_gives_no_item_and_says_so(project):
    def unreachable(url, *, headers=None):
        raise fetching.Unreachable(url, "Name or service not known")

    result = read(source("mastodon"), project, unreachable, None, NOV_5)

    assert (result.reached, result.items, result.status) == (False, [], "Name or service not known")
    assert one_sentence(result.note)
    gdelt = read(source("gdelt_news"), project, unreachable, None, NOV_5)
    assert (gdelt.reached, gdelt.status) == (False, "unreachable")
    assert gdelt.note == "Prism could not reach GDELT (Name or service not known)."


def test_a_source_the_registry_does_not_connect_gives_its_reason(project):
    result = read(source("reddit"), project, None, None, NOV_5)

    assert (result.reached, result.items, result.status) == (False, [], "not connected")
    assert result.note.startswith("Reddit refused clients that are not browsers")
