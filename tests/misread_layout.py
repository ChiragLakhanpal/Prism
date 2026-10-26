"""A layout parser that misreads the showcase package's Activity Reference No., as the workspace's did (ticket 78).

On the workspace on October 26, 2026, ai_parse_document read KE-NWWDA-229129-CW-RFB on page 3 of the October 9, 2026
Procurement Plan for P156634 as KE-NWWDA-229129-CW-RFQ (docs/workspace-catchup.md). The PDF's own words write RFB
(tests/ground_truth/values.toml, plan-229129-reference-2026-10-09). This stand-in is the recorded layout parser with
that one misreading, so a test can read the plans as the workspace did. tests/test_plans.py and
tests/test_demo_ready.py use it.
"""

import tomllib
from pathlib import Path

from strata.reader.layout import Layout, RecordedLayout, Table, https

ROOT = Path(__file__).resolve().parents[1]
SHOWCASE = next(entry for entry in tomllib.loads((ROOT / "tests" / "ground_truth" / "values.toml").read_text())["value"]
                if entry["id"] == "plan-229129-reference-2026-10-09")
ON_THE_WORKSPACE = "KE-NWWDA-229129-CW-RFQ"  # what ai_parse_document read on October 26, 2026


class MisreadsTheShowcaseReference:
    """The recorded layout parser, except that on the October 9, 2026 plan it reads the showcase package's reference
    as `misread`."""

    def __init__(self, manifest, misread: str = ON_THE_WORKSPACE):
        self.recorded, self.misread = RecordedLayout(manifest), misread
        self.name = self.recorded.name
        self.pdf_url = next(https(source.pdf_url) for source in manifest.sources if source.file == SHOWCASE["document"])

    def parse(self, page):
        found = self.recorded.parse(page)
        if https(page.pdf_url) != self.pdf_url:
            return found
        return Layout(tuple(Table(table.title, table.header_rows,
                                  tuple(tuple(cell.replace(SHOWCASE["value"], self.misread) for cell in row)
                                        for row in table.rows))
                            for table in found.tables), found.text, found.figures)
