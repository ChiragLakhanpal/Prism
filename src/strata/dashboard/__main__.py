"""Write the dashboard file from its definition, or check that it is current.

    uv run --frozen python -m strata.dashboard --write
"""

import sys

from strata.dashboard import FILE, written


def main(argv: list[str]) -> int:
    if "--write" in argv:
        FILE.parent.mkdir(parents=True, exist_ok=True)
        FILE.write_text(written())
        print(f"Wrote {FILE.name}.")
        return 0
    if not FILE.exists() or FILE.read_text() != written():
        print(f"{FILE.name} is out of date. Run: uv run --frozen python -m strata.dashboard --write")
        return 1
    print(f"{FILE.name} says what src/strata/dashboard says.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
