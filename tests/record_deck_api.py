"""Writes tests/fixtures/api/deck-data.json, the deck's data the screen tests serve at /deck/data.json (ticket 47).

It is built the way `python -m strata.proposal deck` builds the real one, from the fixture database's snapshot with
the made-up month for what the fixture never measures (tests/proposal_seed.py), and from the demo package's recorded
find_comparables and estimate_time answers. None of it is a finding. tests/test_deck_data.py checks that the file is
still what this script writes. Build the fixture database first, then run:

    uv run --frozen python tests/record_deck_api.py
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.append(str(ROOT / "tests"))

from proposal_seed import merged  # noqa: E402
from strata.proposal import deck  # noqa: E402

RECORDED = ROOT / "tests" / "fixtures" / "api"
FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"


def main() -> None:
    demo = {"comparables": json.loads((RECORDED / "comparables-ke-nwwda-541055.json").read_text()),
            "estimate": json.loads((RECORDED / "estimate-ke-nwwda-541055.json").read_text())}
    data = deck.build(merged(FIXTURE_DB), demo)
    out = RECORDED / "deck-data.json"
    out.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {out.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
