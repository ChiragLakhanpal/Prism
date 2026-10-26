"""The README's "For the panel" links (ticket 46; the 46 brief, section 18).

The block between <!-- proposal:links --> and <!-- /proposal:links --> in README.md is written from config/urls.toml,
the same file the proposal's data sheet and the deck read, so the README and the proposal cannot give different
addresses. `python -m strata.proposal readme --write` writes it, and the gate's proposal check fails when it is out of
date.
"""

from __future__ import annotations

import re
from pathlib import Path

from strata.config import Urls, load_urls

README = Path(__file__).resolve().parents[3] / "README.md"
START, END = "<!-- proposal:links -->", "<!-- /proposal:links -->"
BLOCK = re.compile(re.escape(START) + r"\n(.*?)" + re.escape(END), re.S)


def _address(url: str | None, missing: str) -> str:
    """The address as the end of its sentence, or the sentence that says where to set it."""
    return f"<{url}>." if url else missing


def links(urls: Urls) -> str:
    """The block's lines, one link per line, each with one sentence."""
    not_set = "not set yet. Set `{key}` in `config/urls.toml`."
    lines = [
        "- The proposal: [docs/proposal.md](docs/proposal.md), once it is built from `docs/proposal/source.md` "
        "(`python -m strata.proposal build`). It follows the assessment's modules, and every number in it links to "
        "the result the build measured.",
        "- The deck: " + _address(urls.deck, not_set.format(key="app") + " The deck is the app's address followed by "
                                  "`/present`.") + " The deck is not linked from inside Strata, so this is where to "
        "find it.",
        "- Strata: " + _address(urls.app, not_set.format(key="app")) + " Open it with the account your invitation "
        "went to.",
        "- The dashboard: " + _address(urls.dashboard, not_set.format(key="dashboard")),
        "- The repo: " + _address(urls.repo, not_set.format(key="repo")),
    ]
    return "\n".join(lines) + "\n"


def current(readme: Path = README) -> str | None:
    found = BLOCK.search(readme.read_text())
    return found.group(1) if found else None


def write(urls: Urls | None = None, readme: Path = README) -> None:
    text = readme.read_text()
    if not BLOCK.search(text):
        raise ValueError(f"{readme.name} has no {START} block to write.")
    readme.write_text(BLOCK.sub(lambda _: f"{START}\n{links(urls or load_urls())}{END}", text))


def problem(urls: Urls | None = None, readme: Path = README) -> str | None:
    """A sentence when the README's links differ from config/urls.toml, else None."""
    found = current(readme)
    if found is None:
        return f"README.md has no {START} block. Add it under \"For the panel\"."
    if found != links(urls or load_urls()):
        return ("README.md's links for the panel differ from config/urls.toml. Run "
                "uv run python -m strata.proposal readme --write.")
    return None
