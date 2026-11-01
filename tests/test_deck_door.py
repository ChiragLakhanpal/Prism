"""The deck's password at the App's server (src/strata/server/deck_door.py): the deck's code, data and diagrams go
only to a browser that gave the password, and the rest of the app is untouched."""
import asyncio
import hashlib

import httpx

from strata.config import DeckGate, load_deck_gate
from strata.server import deck_door
from strata.server.app import create_app

# A gate of the test's own, so the deck's real password is written nowhere in the repository.
GATE = DeckGate(b"salt", 1000, hashlib.pbkdf2_hmac("sha256", b"the right one", b"salt", 1000))


def test_the_server_keeps_the_deck_until_the_password_and_serves_the_rest_of_the_app_as_before(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "deck" / "notes").mkdir(parents=True)
    (tmp_path / "index.html").write_text("<!doctype html>")
    (tmp_path / "assets" / "index-a1.js").write_text("app")
    (tmp_path / "assets" / "Deck-b2.js").write_text("deck")
    (tmp_path / "deck" / "data.json").write_text("{}")
    (tmp_path / "deck" / "notes" / "medallion.svg").write_text("<svg/>")
    app = create_app(web_dist=tmp_path, deck_gate=GATE, environ={"DATABRICKS_CLIENT_SECRET": "s"})

    async def go():
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            closed = [(await client.get(path)).status_code for path in
                      ("/api/deck/open", "/deck/data.json", "/deck/notes/medallion.svg", "/assets/Deck-b2.js")]
            app_files = [(await client.get(path)).status_code for path in ("/assets/index-a1.js", "/present/notes")]
            wrong = await client.post("/api/deck/open", json={"password": "not-it"})
            right = await client.post("/api/deck/open", json={"password": "the right one"})
            cookie = right.cookies.get(deck_door.COOKIE)
            header = {"cookie": f"{deck_door.COOKIE}={cookie}"}
            opened = [(await client.get(path, headers=header)).status_code for path in
                      ("/api/deck/open", "/deck/data.json", "/deck/notes/medallion.svg", "/assets/Deck-b2.js")]
            forged = (await client.get("/deck/data.json", headers={"cookie": f"{deck_door.COOKIE}=forged"})).status_code
            return closed, app_files, wrong, right, cookie, opened, forged

    closed, app_files, wrong, right, cookie, opened, forged = asyncio.run(go())
    assert closed == [401, 401, 401, 401]
    assert app_files == [200, 200]
    assert (wrong.status_code, wrong.json()) == (403, {"error": "wrong_password"})
    assert right.status_code == 204 and cookie
    assert "HttpOnly" in right.headers["set-cookie"] and "Secure" in right.headers["set-cookie"]
    assert opened == [204, 200, 200, 200]
    assert forged == 401
    # The deck's own gate is a digest in config/deck.toml, never the password.
    real = load_deck_gate()
    assert real is not None and len(real.digest) == 32 and real.iterations >= 100_000
