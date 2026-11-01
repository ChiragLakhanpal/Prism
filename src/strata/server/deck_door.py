"""The deck's password at the App's server (the user's request of October 31, 2026). The deck's code, its data and the
study guide's diagrams go only to a browser that has given the password, so the slides and the speaker notes stay with
the presenter, even for people signed into the App. config/deck.toml keeps the password's digest, and the browser keeps
a cookie the server signs."""
import hashlib
import hmac

from strata.config import DeckGate

COOKIE = "strata_deck"
# What the password guards: the deck's data and diagrams (web/public/deck), and the deck's own code and styles, the
# chunk Vite names after web/src/deck/Deck.tsx.
GUARDED = ("deck/", "assets/Deck-")
KEEP_SECONDS = 7 * 24 * 60 * 60


def guarded(address: str) -> bool:
    return address.lstrip("/").startswith(GUARDED)


def opens(gate: DeckGate, password: str) -> bool:
    tried = hashlib.pbkdf2_hmac("sha256", password.encode(), gate.salt, gate.iterations)
    return hmac.compare_digest(tried, gate.digest)


def token(gate: DeckGate, secret: str) -> str:
    """The cookie's value, signed with the digest and, inside the Databricks App, the app's own client secret, so the
    repository alone can't make one."""
    return hmac.new(gate.digest + secret.encode(), b"strata-deck-open", hashlib.sha256).hexdigest()


def admits(gate: DeckGate | None, cookie: str | None, secret: str) -> bool:
    return gate is None or (cookie is not None and hmac.compare_digest(cookie, token(gate, secret)))
