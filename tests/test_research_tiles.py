"""Ticket 158: Prism serves the Sentinel-2 tiles of a brief's grids, so a page or its PDF never waits on EOX answering
the browser. GET /api/research/tiles/{year}/{zoom}/{row}/{col}.jpg answers from memory, then strata.ops.research_cache,
then EOX with the named client; ops/research/seed_tiles.py keeps every tile of the stored runs' grids once.

Every fetch here is a fake that counts its calls; no test reaches EOX. The tile is P156634's centre tile at zoom 15
(row 16666, column 20005), whose 2018 and 2025 addresses the registry builds.
"""

import asyncio
import sys
from pathlib import Path

import httpx
from research_world import research_tables, seed_run, seeded_copy

from strata.lakehouse.engine import DuckDBEngine
from strata.research import fetching
from strata.server import research_tiles
from strata.server.app import create_app

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ops" / "research"))
import seed_tiles  # noqa: E402

EOX = "https://tiles.maps.eox.at/wmts/1.0.0/s2cloudless-2025_3857/default/g/15/16666/20005.jpg"
ROUTE = "/api/research/tiles/2025/15/16666/20005.jpg"
TILE = b"\xff\xd8\xff\xe0" + b"tile" * 64
USER_AGENT = "prism-research/0.1 (+https://github.com/ChiragLakhanpal/Prism)"


def call(app, path):
    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            return await client.get(path)
    return asyncio.run(go())


def eox(status: int = 200, body: bytes = TILE, kind: str = "image/jpeg"):
    """A fake EOX that answers every address with the same answer, keeping the addresses it was asked."""
    calls: list[str] = []

    def fetch(url, *, headers=None):
        calls.append(url)
        return status, {"content-type": kind}, body

    fetch.calls = calls
    return fetch


def tiles(fetch, engine=None) -> research_tiles.Tiles:
    cache = fetching.TableCache(lambda: engine.cursor()) if engine is not None else None
    return research_tiles.Tiles.from_registry(fetch=fetch, cache=cache)


def test_a_miss_asks_eox_once_with_the_named_client_and_keeps_the_answer_in_the_cache_table():
    asked: list[tuple[str, str]] = []

    class Answer:
        status, headers = 200, {"Content-Type": "image/jpeg"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return TILE

    def opener(request, timeout):
        asked.append((request.full_url, request.get_header("User-agent")))
        return Answer()

    engine = research_tables()
    app = create_app(research_tiles=tiles(fetching.live(opener=opener), engine))
    first = call(app, ROUTE)
    assert first.status_code == 200
    assert first.content == TILE
    assert first.headers["content-type"] == "image/jpeg"
    assert first.headers["cache-control"] == "public, max-age=86400"
    assert asked == [(EOX, USER_AGENT)]
    # The answer is kept in strata.ops.research_cache under the source's key, the body in base64.
    rows = engine.run("SELECT url, source_key, status FROM strata.ops.research_cache").rows
    assert [tuple(row) for row in rows] == [(EOX, "sentinel2_mosaic", 200)]
    # A second request is answered from memory: EOX is not asked again.
    assert call(app, ROUTE).content == TILE
    assert len(asked) == 1


def test_a_tile_in_the_cache_table_is_served_without_asking_eox():
    engine = research_tables()
    fetching.TableCache(lambda: engine.cursor()).put("sentinel2_mosaic", EOX, (200, {"content-type": "image/jpeg"}, TILE),
                                                      research_tiles.EVER)
    fetch = eox(status=500)
    app = create_app(research_tiles=tiles(fetch, engine))
    answer = call(app, ROUTE)
    assert answer.status_code == 200
    assert answer.content == TILE
    assert fetch.calls == []


def test_a_refusal_answers_502_with_the_code_and_is_never_kept():
    engine = research_tables()
    for refused in (eox(status=429, body=b"slow down", kind="text/plain"), eox(status=404, body=b"<xml/>", kind="text/xml"),
                    eox(status=200, body=b"<html>bot check</html>", kind="text/html")):
        app = create_app(research_tiles=tiles(refused, engine))
        answer = call(app, ROUTE)
        assert answer.status_code == 502
        assert answer.json() == {"code": "tile_server"}
        assert answer.headers["cache-control"] == "no-store"
    assert engine.run("SELECT count(*) FROM strata.ops.research_cache").rows[0][0] == 0


def test_a_host_it_cannot_reach_answers_502_too():
    def unreachable(url, *, headers=None):
        raise fetching.Unreachable(url, "timed out")

    answer = call(create_app(research_tiles=tiles(unreachable)), ROUTE)
    assert answer.status_code == 502
    assert answer.json() == {"code": "tile_server"}


def test_the_route_asks_eox_only_for_a_year_and_zoom_the_registry_lists():
    fetch = eox()
    app = create_app(research_tiles=tiles(fetch))
    for path in ("/api/research/tiles/2015/15/16666/20005.jpg", "/api/research/tiles/2025/12/16666/20005.jpg",
                 "/api/research/tiles/2025/15/99999/20005.jpg"):
        answer = call(app, path)
        assert answer.status_code == 404
        assert answer.json() == {"code": "unknown_tile"}
    assert fetch.calls == []


def test_the_seed_keeps_every_tile_of_the_stored_grids_once_and_a_second_seed_keeps_none(fixture_db, tmp_path):
    database = seeded_copy(fixture_db, tmp_path)
    with DuckDBEngine.open(database) as engine:
        state = lambda: engine.cursor()  # noqa: E731
        expected = seed_tiles.addresses(state, "P156634")
        # Two grids of nine tiles for each of the seeded run's locations, each address once.
        assert expected and len(expected) % 18 == 0
        assert all(url.startswith("https://tiles.maps.eox.at/") for url in expected)
        said: list[str] = []
        fetch = eox()
        first = seed_tiles.seed(state, ["P156634"], tiles(fetch, engine), say=said.append)
        assert first == {"P156634": {"kept": len(expected), "already": 0, "refused": 0}}
        assert fetch.calls == expected
        assert said[-1] == (f"P156634: {len(expected)} tiles in its grids; kept {len(expected)} now, 0 kept already, "
                            "0 refused by the tile server.")
        # A second seed, in a new process with nothing in memory, finds every tile in the table and asks EOX nothing.
        again = eox()
        second = seed_tiles.seed(state, ["P156634"], tiles(again, engine), say=said.append)
        assert second == {"P156634": {"kept": 0, "already": len(expected), "refused": 0}}
        assert again.calls == []
        assert seed_tiles.projects_with_tiles(state) == ["P156634"]


def test_the_seed_counts_what_eox_refused_and_prints_the_routes_to_warm(fixture_db, tmp_path):
    database = seeded_copy(fixture_db, tmp_path)
    with DuckDBEngine.open(database) as engine:
        state = lambda: engine.cursor()  # noqa: E731
        expected = seed_tiles.addresses(state, "P156634")
        said: list[str] = []
        counts = seed_tiles.seed(state, ["P156634"], tiles(eox(status=429, body=b"", kind="text/plain"), engine),
                                 say=said.append, routes=True)
        assert counts["P156634"] == {"kept": 0, "already": 0, "refused": len(expected)}
        assert not any(line.startswith("/api/research/tiles/") for line in said)
        said.clear()
        seed_tiles.seed(state, ["P156634"], tiles(eox(), engine), say=said.append, routes=True)
        paths = [line for line in said if line.startswith("/api/")]
        assert paths == [seed_tiles.route_of(url) for url in expected]
        assert seed_tiles.route_of(EOX) == ROUTE


def test_the_seed_on_a_state_file_reads_the_stored_runs(fixture_db, tmp_path, capsys):
    from strata.research.store import ResearchStore

    database = tmp_path / "state.duckdb"
    run, items = seed_run(fixture_db)
    with research_tables(database) as engine:
        assert ResearchStore(lambda: engine.cursor()).save(run, items)
    fetch = eox()
    assert seed_tiles.main(["--all", "--state-file", str(database)], environ={}, fetch=fetch) == 0
    out = capsys.readouterr().out
    assert len(fetch.calls) > 0
    assert f"Tiles kept now: {len(fetch.calls)}; kept already: 0; refused: 0." in out
