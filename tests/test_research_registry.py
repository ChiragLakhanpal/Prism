"""Ticket 147: the research registry, config/research.toml, read by strata.config.load_research().

It defines the ten sources Prism's deep research reads (ticket 154 added site conditions, the agencies' own statements
and the sanctions check) and the seven it does not connect, each with its reason, and a bad key stops it with a
sentence, as load_sources() does."""

import pytest

from strata.config import CONFIG_DIR, ConfigError, load_research, load_research_client

READ = ["isr_narrative", "procurement_notices", "gdelt_news", "outlet_feeds", "inspection_panel", "sentinel2_mosaic",
        "mastodon", "site_conditions", "agency_statements", "sanctions"]
NOT_CONNECTED = ["reddit", "bluesky", "x", "google_news", "wikimedia_commons", "reliefweb", "tender_disputes"]


def test_the_registry_defines_the_ten_sources_and_the_seven_not_connected():
    sources = load_research()

    assert [key for key, source in sources.items() if source.enabled] == READ
    assert [key for key, source in sources.items() if not source.enabled] == NOT_CONNECTED
    kinds = {key: source.kind for key, source in sources.items() if source.enabled}
    assert kinds == {"isr_narrative": "bank_report", "procurement_notices": "procurement", "gdelt_news": "news",
                     "outlet_feeds": "news", "inspection_panel": "complaint", "sentinel2_mosaic": "satellite",
                     "mastodon": "social", "site_conditions": "site_condition",
                     "agency_statements": "agency_statement", "sanctions": "sanctions"}
    assert [(page.agency, page.url) for page in sources["agency_statements"].pages][:2] == [
        ("NWWDA", "https://nwwda.go.ke/index.php/news-events"), ("CWWDA", "https://cwwda.go.ke/news")]
    assert "approved appname" in sources["reliefweb"].limitations[0]
    assert "did not answer Prism's named client" in sources["tender_disputes"].limitations[0]
    assert sources["gdelt_news"].pace_seconds == 5
    assert sources["sentinel2_mosaic"].license.startswith("Sentinel-2 cloudless by EOX IT Services GmbH")
    assert all(source.limitations and source.limitations[0].endswith(".") for source in sources.values())
    assert "refused clients that are not browsers" in sources["reddit"].limitations[0]


def test_the_outlet_feeds_list_each_outlet_with_its_feed():
    feeds = load_research()["outlet_feeds"].feeds

    assert [feed.outlet for feed in feeds][:7] == ["The Star", "The Standard", "Kenya News Agency", "Capital FM", "KBC",
                                                    "People Daily", "Dawan Africa"]
    assert all(feed.url.startswith("https://") for feed in feeds)


def test_the_client_sends_the_named_agent_never_a_browser_s():
    client = load_research_client()

    assert client.user_agent == "prism-research/0.1 (+https://github.com/ChiragLakhanpal/Prism)"
    assert "Mozilla" not in client.user_agent
    assert "Just a moment..." in client.bot_check_markers
    assert "MOWASSCO" in client.press_names["Mombasa Water and Sanitation Services Company"]
    assert "water" in client.sector_words["water"]


@pytest.mark.parametrize("old, new, says", [
    ('kind = "complaint"', 'kind = "rumour"', "sources.inspection_panel.kind must be one of bank_report"),
    ("pace_seconds = 5\n", "", "sources.gdelt_news.pace_seconds is missing"),
    ('reader = "strata.research.sources.mastodon:read"', 'reader = "mastodon"',
     "sources.mastodon.reader must name a module and a function, as module:function"),
    ("enabled = true\n\n[sources.mastodon.settings]", "enabled = true\nsecret = 1\n\n[sources.mastodon.settings]",
     "sources.mastodon has keys I do not know: secret"),
    ("cache_hours = 24\nreader = \"strata.research.sources.inspection_panel",
     "cache_hours = -1\nreader = \"strata.research.sources.inspection_panel",
     "sources.inspection_panel.cache_hours must be a number of hours, 0 or more"),
])
def test_a_bad_key_stops_the_registry_with_a_sentence(tmp_path, old, new, says):
    text = (CONFIG_DIR / "research.toml").read_text()
    assert old in text
    path = tmp_path / "research.toml"
    path.write_text(text.replace(old, new, 1))

    with pytest.raises(ConfigError, match=says.replace(".", r"\.")):
        load_research(path)
