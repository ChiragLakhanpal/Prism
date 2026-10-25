"""Deploy Strata's Genie space from code, and say what changed (ticket 33).

Run it from the main checkout, after the bundle deploy has made the metric views (ops/bundle/deploy.py):

    uv run python ops/genie/deploy_space.py --env-file .env

It needs DATABRICKS_HOST, DATABRICKS_TOKEN and DATABRICKS_WAREHOUSE_ID in the env file. In order:

1. It reads the space from config/genie.toml, its trusted SQL from src/strata/genie/trusted/ and its benchmark
   questions from evals/benchmark.yaml (src/strata/genie/space.py).
2. It finds Strata's space: the one GENIE_SPACE_ID names when its title is Strata's, or else the one with Strata's
   title. It never changes a space with another title, such as the wizard's throwaway space for day-one test 5,
   because the workspace is shared with fairshare. Then it creates the space, updates it, or leaves it as it is,
   and says which. A second run prints "No change."
3. When the space's ID is not the one GENIE_SPACE_ID names, it adds GENIE_SPACE_ID='<id>' as the env file's last
   line and leaves every other line as it was. The live commands read a later line over an earlier one.

It exits 0 when the space matches the repo, 1 when Genie refused a change, and 2 when the env file is not ready.
The full gate (ops/evals/full_gate.py) then asks the space its benchmark questions and stores its pass rate.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
for folder in (REPO / "src", REPO / "ops" / "dayone"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import dayone  # noqa: E402

from strata.genie import space as genie_space  # noqa: E402
from strata.lakehouse.engine import EngineError, http_transport  # noqa: E402

NEEDS = ("DATABRICKS_HOST", "DATABRICKS_TOKEN", "DATABRICKS_WAREHOUSE_ID")


def main(argv: list[str] | None = None, spaces=None) -> int:
    parser = argparse.ArgumentParser(prog="ops/genie/deploy_space.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's env file, which the wizard filled. That file is the default.")
    args = parser.parse_args(argv)
    path = args.env_file or dayone.default_env_path()
    if not path.is_file():
        print(f"There is no env file at {path}. {dayone.WIZARD_FIRST}")
        return 2
    env = dayone.load_env(path)
    missing = dayone.missing_keys(env, list(NEEDS))
    if missing:
        print(f"{path} has no value for {', '.join(missing)}. {dayone.WIZARD_FIRST}")
        return 2
    space = genie_space.load()
    api = spaces or genie_space.RestSpaces(http_transport(env["DATABRICKS_HOST"], env["DATABRICKS_TOKEN"]))
    known = (env.get("GENIE_SPACE_ID") or "").strip() or None
    print(f"1. Building the space {space.title} from config/genie.toml: {len(space.trusted)} trusted questions and "
          f"{len(space.benchmarks)} benchmark questions.")
    try:
        deployed = genie_space.deploy(api, space, env["DATABRICKS_WAREHOUSE_ID"], known)
    except (EngineError, ValueError) as error:
        print(f"I could not deploy the space. {error}")
        return 1
    for note in deployed.notes:
        print(f"   {note}")
    if deployed.action == "created":
        print(f"2. I made the space {deployed.space_id}.")
    elif deployed.action == "updated":
        print(f"2. I updated the space {deployed.space_id}: {', '.join(deployed.changes)}.")
    else:
        print(f"2. The space {deployed.space_id} already matches the repo. No change.")
    if deployed.space_id != known:
        genie_space.append_env(path, "GENIE_SPACE_ID", deployed.space_id)
        print(f"3. I added GENIE_SPACE_ID for {deployed.space_id} as the last line of {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
