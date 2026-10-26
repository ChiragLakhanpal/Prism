# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Count the notices in strata.silver.notices that still hold what the nightly check looks for, and, with --forget,
take the rows of their pages out so the next bronze_to_gold reads those pages again: ticket 76's live step.

Run it from the main checkout:

    uv run --script ops/notices/contacts_left_live.py --env-file .env
    uv run --script ops/notices/contacts_left_live.py --env-file .env --forget

It finds the notices with the contacts_left check's own condition and patterns (strata.lakehouse.quality,
contacts.LEFT_EMAIL and LEFT_PHONE), bound as parameters as the check binds them. With --forget, it deletes every row
of those notices' pages from strata.silver.notices (a DELETE with a WHERE, CLAUDE.md rule 5). Bronze still holds the
pages, so the next bronze_to_gold reads them again, and silver runs the contact removal on them as it is now. Once
ticket 75 has landed, its record of what silver wrote reads every notices page again on its own (the notices
module's VERSION), and --forget is not needed.

It exits 0 when it ran, 1 when --check-zero was given and the check still finds a notice, and 2 when it could not
run. It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID and a token or a service principal.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

from strata.lakehouse.engine import EngineError  # noqa: E402
from strata.lakehouse.silver import notices  # noqa: E402
from workspace_env import WorkspaceEnvError, load_workspace_env  # noqa: E402


def counted(number: int, word: str) -> str:
    return f"{number:,} {word}{'' if number == 1 else 's'}"


def main(argv: list[str] | None = None, workspace=None, env: dict | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ops/notices/contacts_left_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, help="the env file with the workspace's address, warehouse and token")
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--forget", action="store_true",
                        help="take the rows of the flagged notices' pages out of strata.silver.notices")
    choice.add_argument("--check-zero", action="store_true", help="exit 1 when the check still finds a notice")
    args = parser.parse_args(argv)
    if env is None:
        try:
            env = load_workspace_env(args.env_file)
        except WorkspaceEnvError as error:
            print(error, file=sys.stderr)
            return 2
    if workspace is None:
        from bundle_live import LiveWorkspace

        workspace = LiveWorkspace(env)

    engine = workspace.engine()
    try:
        found = notices.contacts_left(engine)
        print(f"The nightly check's patterns find {counted(found.notices, 'notice')} on "
              f"{counted(found.pages, 'page')} of strata.silver.notices.")
        if args.forget and found.pages:
            removed = notices.forget_pages_with_contacts_left(engine)
            print(f"I took {counted(removed, 'row')} out of strata.silver.notices, every row of those pages. The next "
                  "bronze_to_gold reads the pages again from bronze, with the contact removal as it is now.")
    except EngineError as error:
        print(f"I could not ask the SQL warehouse: {error}", file=sys.stderr)
        return 2
    return 1 if args.check_zero and found.notices else 0


if __name__ == "__main__":
    sys.exit(main())
