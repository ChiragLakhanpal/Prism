"""The README's part for the panel (ticket 46; the 46 brief, section 18): the deck's address and the other links from
config/urls.toml, how to run Prism, and the demo-ready command.

Expected addresses come from docs/workspace-catchup.md, where the App's deploy of October 26, 2026 printed it, never
from the code under test.
"""

import re
from pathlib import Path

from strata import config
from strata.proposal import readme

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
# docs/workspace-catchup.md, ticket 70's redeploy of October 26, 2026: "Prism is running at https://strata-..."
APP = "https://strata-7405609289499029.9.azure.databricksapps.com"


def section(name: str) -> str:
    return README.read_text().split(f"\n## {name}\n")[1].split("\n## ")[0]


def test_the_links_give_the_decks_address_as_the_apps_address_with_present():
    block = readme.links(config.Urls("https://strata-1.aws.databricksapps.com", None, None))
    assert "- The deck: <https://strata-1.aws.databricksapps.com/present>. The deck is not linked from inside " \
           "Prism, so this is where to find it." in block
    assert "- Prism: <https://strata-1.aws.databricksapps.com>. Open it " in block


def test_an_address_not_known_yet_says_where_to_set_it():
    block = readme.links(config.Urls(None, None, None))
    assert "- The repo: not set yet. Set `repo` in `config/urls.toml`." in block


def test_the_committed_readme_gives_the_decks_address_and_agrees_with_config_urls():
    assert config.load_urls().app == APP
    assert f"- The deck: <{APP}/present>" in section("For the panel")
    assert readme.problem() is None


def test_the_readme_says_how_to_run_strata_and_where_the_demo_ready_command_is():
    run = section("Run Prism")
    for anchor in ("#run-the-app", "#deploy-the-app", "#before-a-demo"):
        assert f"]({anchor})" in run
        assert f"\n## {anchor[1:].replace('-', ' ').capitalize()}\n" in README.read_text()
    demo = section("Before a demo")
    assert re.search(r"^    uv run .*ops/demo/", demo, re.M), "the demo-ready command, indented as the README's others"
    assert "Prism is ready for the demo." in demo and "Prism is ready for the demo." in run
