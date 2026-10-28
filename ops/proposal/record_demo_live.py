"""Record the demo package's comparable packages and time estimate on the shared workspace, for the deck (ticket 47).

Run it from the main checkout, after the nightly job and the estimates loop have run:

    uv run --frozen python ops/proposal/record_demo_live.py --env-file .env

It asks the app's own routes, in this process, on the workspace's SQL warehouse with the env file's token, for the
demo package config/slice.toml names: GET /api/packages/<package>/comparables and /estimate, the same answers the
package workspace draws. It writes both to docs/proposal/demo-package.json. Then
`uv run python -m strata.proposal deck` builds web/public/deck/data.json from it and the measures snapshot. The deck's
package demo opens the live App in a new tab; when the App is down, its "Show the recorded answer" button draws the
recorded comparables instead (ticket 116). The deck's data keeps both answers, checked against the demo package.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections.abc import Callable
from pathlib import Path

import httpx

from strata import config
from strata.proposal import deck
from strata.server.app import create_app

REPO = Path(__file__).resolve().parents[2]

NEEDS = ("DATABRICKS_HOST", "DATABRICKS_WAREHOUSE_ID", "DATABRICKS_TOKEN")
VIEWER = "deck.recording@strata.local"


def record(engine_for: Callable, token: str) -> dict:
    """The demo package's find_comparables and estimate_time answers, as the app's routes give them."""
    package = config.load_slice().demo_plan.package
    app = create_app(engine_for=engine_for)
    headers = {"X-Forwarded-Email": VIEWER, "X-Forwarded-Preferred-Username": VIEWER,
               "X-Forwarded-User": VIEWER, "X-Forwarded-Access-Token": token}

    async def ask() -> dict:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.local", timeout=120) as client:
            for name in deck.DEMO_ANSWERS:
                path = f"/api/packages/{package}/{name}"
                response = await client.get(path, headers=headers)
                if response.status_code != 200:
                    raise RuntimeError(f"{path} answered {response.status_code}: {response.text[:300]}")
                found[name] = response.json()
        return found

    return asyncio.run(ask())


def main(argv=None) -> int:
    for folder in (REPO / "ops" / "dayone", REPO / "ops" / "bundle"):
        if str(folder) not in sys.path:
            sys.path.insert(0, str(folder))
    from strata.server.engines import warehouse_as_viewer
    from workspace_env import WorkspaceEnvError, load_workspace_env

    parser = argparse.ArgumentParser(prog="ops/proposal/record_demo_live.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", help="the env file with the workspace's address, warehouse and token")
    parser.add_argument("--out", default=str(deck.DEMO_FILE), help="where to write the demo package's answers")
    args = parser.parse_args(argv)
    try:
        env = load_workspace_env(Path(args.env_file) if args.env_file else None)
    except WorkspaceEnvError as error:
        print(error)
        return 2
    missing = [key for key in NEEDS if not env.get(key)]
    if missing:
        print(f"The env file has no value for {', '.join(missing)}. Run the setup wizard first "
              "(ops/wizard/strata-setup.sh).")
        return 2
    try:
        answers = record(warehouse_as_viewer(env["DATABRICKS_HOST"], env["DATABRICKS_WAREHOUSE_ID"]),
                         env["DATABRICKS_TOKEN"])
        deck.build(None, answers)
    except (RuntimeError, deck.DeckError) as error:
        print(f"I could not record the demo package: {error}")
        return 2
    out = Path(args.out)
    out.write_text(json.dumps(answers, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote {out}. Now run uv run python -m strata.proposal deck, which builds the deck's data from it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
