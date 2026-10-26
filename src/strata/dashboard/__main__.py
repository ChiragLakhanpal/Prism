"""Write the dashboard files from their definition, or check that they are current.

    uv run --frozen python -m strata.dashboard --write
    uv run --frozen python -m strata.dashboard --write --no-query-history

The first writes "Strata operations" and its test copy with the table of who queried what. If the workspace doesn't
let Strata read its query history (docs/workspace-catchup.md), the second writes them with the dated text tile in its
place (the 45 design brief, section 6.4); deploy and commit what it wrote.
"""

import sys

from strata.dashboard import FILE, TEST_FILE, written


def main(argv: list[str]) -> int:
    history = "--no-query-history" not in argv
    files = ((FILE, written(False, history)), (TEST_FILE, written(True, history)))
    if "--write" in argv:
        for path, text in files:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
            print(f"Wrote {path.name}.")
        return 0
    stale = [path.name for path, text in files if not path.exists() or path.read_text() != text]
    if stale:
        print(f"{', '.join(stale)} out of date. Run: uv run --frozen python -m strata.dashboard --write")
        return 1
    print(f"{FILE.name} and {TEST_FILE.name} say what src/strata/dashboard says.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
