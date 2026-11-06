"""The demo's Sentinel-2 tiles (ticket 158): every tile of every stored run's grids, kept in strata.ops.research_cache
once, so the Deep research tab and its PDF never depend on EOX answering live.

    uv run python ops/research/seed_tiles.py --all --env-file .env                  # on the workspace, as the app
    uv run python ops/research/seed_tiles.py --project P156634 --state-file state.duckdb   # in a local DuckDB file
    uv run python ops/research/seed_tiles.py --all --env-file .env --routes          # also print each tile's route

It reads each stored run's sentinel2_mosaic items (strata.ops.research_items, their image_urls: two grids of nine
addresses each) and the addresses strata.ops.research_cache keeps already, one query each. A tile kept already is left
as it is; a missing one is fetched from EOX with the named client prism-research/0.1, paced by the source's
pace_seconds, as the App's tile route asks (src/strata/server/research_tiles.py), and kept in inserts of BATCH rows, so
a thousand tiles on the warehouse take tens of statements, not thousands. It prints, for each project, how many tiles it kept now, how many were
kept already, and how many EOX refused, so a second seed keeps 0. --routes prints each tile's path on the App, one a
line, for the request that warms the App's memory after a deploy.
"""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import re
import sys
from collections.abc import Callable

from strata.lakehouse.engine import Engine
from strata.research import fetching
from strata.server.research_tiles import SOURCE_KEY, Tiles

ADDRESS = re.compile(r"s2cloudless-(\d{4})_3857/default/g/(\d+)/(\d+)/(\d+)\.jpg$")
ITEMS = ("SELECT DISTINCT project_id, image_urls FROM strata.ops.research_items "
         "WHERE source_key = :source AND project_id = :project_id")
PROJECTS = "SELECT DISTINCT project_id FROM strata.ops.research_items WHERE source_key = :source ORDER BY project_id"
KEPT = "SELECT DISTINCT url FROM strata.ops.research_cache WHERE source_key = :source AND status = 200"
# The rows one insert keeps: about 260 KB of base64 tiles, so a seed of a thousand tiles takes tens of statements.
BATCH = 20


def route_of(url: str) -> str | None:
    """The App's path for an EOX tile address, as web/src/lib/research.ts tileRoute builds it."""
    found = ADDRESS.search(url)
    return "/api/research/tiles/{}/{}/{}/{}.jpg".format(*found.groups()) if found else None


def addresses(engine_factory: Callable[[], Engine], project_id: str) -> list[str]:
    """Every tile address of the project's stored grids, each once, in the order the runs list them."""
    with fetching.opened(engine_factory) as engine:
        rows = engine.run(ITEMS, {"source": SOURCE_KEY, "project_id": project_id}).rows
    seen: dict[str, None] = {}
    for _, image_urls in rows:
        for grid in json.loads(image_urls) if isinstance(image_urls, str) else (image_urls or []):
            for url in grid:
                seen.setdefault(url, None)
    return list(seen)


def projects_with_tiles(engine_factory: Callable[[], Engine]) -> list[str]:
    with fetching.opened(engine_factory) as engine:
        return [row[0] for row in engine.run(PROJECTS, {"source": SOURCE_KEY}).rows]


def seed(engine_factory: Callable[[], Engine], projects: list[str], tiles: Tiles, say=print,
         routes: bool = False, now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.UTC)
         ) -> dict[str, dict[str, int]]:
    """Keep every tile of each project's stored grids; the counts for each project: kept now, kept already, refused."""
    with fetching.opened(engine_factory) as engine:
        kept = {row[0] for row in engine.run(KEPT, {"source": SOURCE_KEY}).rows}
    pending: list[tuple] = []

    def flush() -> None:
        if pending:
            with fetching.opened(engine_factory) as engine:
                engine.insert_rows("strata.ops.research_cache", fetching.TableCache.COLUMNS, list(pending))
            pending.clear()

    counts: dict[str, dict[str, int]] = {}
    for project_id in projects:
        found = addresses(engine_factory, project_id)
        tally = {"kept": 0, "already": 0, "refused": 0}
        for url in found:
            if url in kept:
                tally["already"] += 1
            else:
                answer = tiles.from_eox(url)
                if answer is None:
                    tally["refused"] += 1
                    say(f"{project_id}: the tile server refused {url}.")
                    continue
                at = now().astimezone(dt.UTC)
                pending.append((url, SOURCE_KEY, 200, json.dumps({"content-type": "image/jpeg"}),
                                base64.b64encode(answer[2]).decode(), at.replace(tzinfo=None), at.date()))
                kept.add(url)
                tally["kept"] += 1
                if len(pending) >= BATCH:
                    flush()
            if routes:
                say(route_of(url))
        flush()
        counts[project_id] = tally
        say(f"{project_id}: {len(found)} tiles in its grids; kept {tally['kept']} now, {tally['already']} kept "
            f"already, {tally['refused']} refused by the tile server.")
    return counts


def main(argv: list[str] | None = None, environ: dict[str, str] | None = None, fetch: fetching.Fetch | None = None) -> int:
    import os

    from strata.seed_examples import read_env_file
    from strata.server.settings import _the_app_s_engine, app_state_file

    arguments = _parser().parse_args(argv)
    environ = dict(os.environ if environ is None else environ)
    if arguments.env_file:
        engine = _the_app_s_engine(environ | read_env_file(arguments.env_file))
        if engine is None:
            print("I need the workspace: DATABRICKS_HOST, DATABRICKS_WAREHOUSE_ID, DATABRICKS_CLIENT_ID and "
                  "DATABRICKS_CLIENT_SECRET, in the env file --env-file names.")
            return 1
    elif arguments.state_file:
        engine = app_state_file({"STRATA_APP_STATE_FILE": arguments.state_file})
    else:
        print("Name where to write: --env-file for the workspace, or --state-file for a local DuckDB file.")
        return 1
    projects = projects_with_tiles(engine) if arguments.all else arguments.project
    if not projects:
        print("Name a project with --project, once for each project, or seed every stored run's tiles with --all.")
        return 1
    tiles = Tiles.from_registry(fetch=fetch, cache=fetching.TableCache(engine))
    counts = seed(engine, projects, tiles, routes=arguments.routes)
    refused = sum(tally["refused"] for tally in counts.values())
    print(f"Tiles kept now: {sum(tally['kept'] for tally in counts.values())}; kept already: "
          f"{sum(tally['already'] for tally in counts.values())}; refused: {refused}.")
    return 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Keep every Sentinel-2 tile of the stored runs' grids in the cache.")
    parser.add_argument("--project", action="append", default=[], help="a project with a stored run; repeat it")
    parser.add_argument("--all", action="store_true", help="every project with a stored run's grids")
    parser.add_argument("--env-file", help="the env file that names the workspace: write as the app on it")
    parser.add_argument("--state-file", help="a local DuckDB file to write instead, as scripts/dev's app state")
    parser.add_argument("--routes", action="store_true", help="print each tile's path on the App, to warm it")
    return parser


if __name__ == "__main__":
    sys.exit(main())
