# /// script
# requires-python = ">=3.12,<3.14"
# dependencies = ["databricks-sdk==0.156.0", "pyyaml==6.0.3", "duckdb==2.0.0", "sqlglot==30.24.0", "pytz==2026.5"]
# ///
"""Count the notices in strata.silver.notices that still hold what the nightly check looks for: ticket 76's live check.

Run it from the main checkout, before and after the bronze_to_gold run that reads the notices pages again:

    uv run --script ops/notices/contacts_left_live.py --env-file .env
    uv run --script ops/notices/contacts_left_live.py --env-file .env --check-zero

It finds the notices with the contacts_left check's own condition and patterns (strata.lakehouse.quality,
contacts.LEFTOVERS), bound as parameters as the check binds them, and writes nothing. The notices
transform's VERSION is 2 since silver runs the contact removal again on each page it reads, so the first
bronze_to_gold after the deploy reads again every notices page that ticket 75's record holds under version 1.
Since ticket 121 every bronze_to_gold also reads again the pages of the notices this counts.

It exits 0 when it counted, 1 when --check-zero was given and the check still finds a notice, and 2 when it could
not ask. It needs DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID and a token or a service principal.
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
    parser.add_argument("--check-zero", action="store_true", help="exit 1 when the check still finds a notice")
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

    try:
        found = notices.contacts_left(workspace.engine())
    except EngineError as error:
        print(f"I could not ask the SQL warehouse: {error}", file=sys.stderr)
        return 2
    print(f"The nightly check's patterns find {counted(found.notices, 'notice')} on {counted(found.pages, 'page')} "
          "of strata.silver.notices.")
    return 1 if args.check_zero and found.notices else 0


if __name__ == "__main__":
    sys.exit(main())
