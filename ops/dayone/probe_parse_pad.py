# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pypdf==6.21.2"]
# ///
"""Day-one test 3: ai_parse_document runs on a PAD of 120 pages or more.

Run it from the main checkout after the wizard:

    uv run --script ops/dayone/probe_parse_pad.py --env-file .env

It finds a Project Appraisal Document of at least the page count in dayone.toml, downloading it
to this computer so the test does not depend on test 1. It uploads the file to the volume named
in dayone.toml, runs ai_parse_document on the SQL warehouse, and counts the pages it read. It
writes test 3 in docs/day-one-results.md.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import dayone  # noqa: E402
from dayone import Outcome, ProbeError, SetupError  # noqa: E402

NEEDS = ["DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID"]


def check(workspace, env: dict, config: dict) -> Outcome:
    settings = config["pad"]
    try:
        pad = workspace.find_pad(settings)
    except ProbeError as error:
        return Outcome("not run", f"I found no PAD of {settings['min_pages']} pages or more, so I could not run "
                                  "the test. Add a project with a longer PAD to [pad] in ops/dayone/dayone.toml.",
                       [str(error)])
    found = f"{pad['project']} PAD: {pad['url']}, {pad['pages']} pages."
    try:
        parsed = workspace.parse(f"{pad['project']}-pad.pdf", pad["data"])
    except SetupError as error:  # the PAD never reached ai_parse_document
        return dayone.not_run(error, [found])
    except ProbeError as error:
        return Outcome("failed", "ai_parse_document did not run on the PAD.", [found, str(error)])
    evidence = [found, f"Uploaded to {parsed['path']}.",
                f"Statement {parsed['statement']} took {parsed['seconds']:.0f} seconds and read {parsed['pages']} pages."]
    if parsed.get("error"):
        evidence.append(f"ai_parse_document reported: {parsed['error']}")
    if parsed.get("error") or not parsed.get("pages"):
        return Outcome("failed", "ai_parse_document returned an error or no pages for the PAD.", evidence)
    if parsed["pages"] < pad["pages"]:
        return Outcome("partly", f"ai_parse_document read {parsed['pages']} of {pad['pages']} pages of the PAD.",
                       evidence)
    return Outcome("passed", f"ai_parse_document read all {pad['pages']} pages of the PAD.", evidence)


class CannedWorkspace:
    """A long PAD that parses in full, for --dry-run."""

    def __init__(self, env: dict, config: dict):
        self.pages = config["pad"]["min_pages"] + 11

    def find_pad(self, settings):
        return {"project": settings["projects"][0], "url": "https://documents.worldbank.org/dry-run.pdf",
                "pages": self.pages, "data": b""}

    def parse(self, name, data):
        return {"pages": self.pages, "error": None, "statement": "dry-run", "seconds": 0.0,
                "path": f"/Volumes/dry-run/{name}"}


def live(env: dict, config: dict):
    from live import LivePad
    return LivePad(env, config)


def main(argv: list[str] | None = None, service=None) -> int:
    return dayone.run_probe(3, argv, __doc__, NEEDS, live, CannedWorkspace, check, service)


if __name__ == "__main__":
    sys.exit(main())
