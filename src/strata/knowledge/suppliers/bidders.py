"""The awarded bidders of each Contract Award notice, read from the notice's plain text.

An award notice writes each awarded bidder as its name, with its STEP supplier ID in brackets when it
has one, then its address and a "Country:" line. A works or goods notice heads the list "Awarded
Bidder(s):", a consultant notice "Awarded Firm(s):", and a small assignment "Awarded
Firm/Individual:". Several awarded bidders on one notice are the members of a joint venture. A
consultant notice adds lines such as "Registry ID: 24" and the evaluation scores; none of them is a
bidder, and none is kept, because suppliers are never scored or ranked. A person hired as an
individual consultant is written "Individual Consultant" and is never named.

It reads strata.silver.notices.notice_text, the notice after the fetch removed contact details, and
never the recorded files, which keep them on purpose (data/fixture/README.md). A name the fetch
removed as a person's contact detail stays removed. read() takes the text and gives plain rows, and
store() adds the rows of each notice page not read yet to strata.silver.notice_bidders.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from importlib import resources

from strata.lakehouse.engine import Engine

AWARDED = ("Awarded Bidder(s):", "Awarded Firm(s):", "Awarded Firm/Individual:")
# The lists that follow the awarded bidders, which end their list.
NOT_AWARDED = ("Evaluated Bidder(s):", "Evaluated Firm(s):", "Rejected Bidder(s):", "Rejected Firm(s):")
COUNTRY = "Country:"
# A price heading, whose value is on the next line. Neither line is a bidder.
PRICE_HEADINGS = ("Bid Price at Opening", "Evaluated Bid Price", "Signed Contract price", "Signed Contract Price",
                  "Final Evaluation Price", "Read Out Price", "Reason for Rejection")
LABELLED = re.compile(r"^[A-Za-z][A-Za-z /()]{0,40}:\s*\S")  # a line such as "Registry ID: 24"
WITH_ID = re.compile(r"^(?P<name>.*?)\s*\((?P<id>\d{3,})\)$")
INDIVIDUAL_CONSULTANT = "INDIVIDUAL CONSULTANT"
REMOVED = "[contact removed]"  # what the fetch writes where it removed a contact detail (contacts.py)

COLUMNS = ("notice_id", "position", "project_id", "step_reference", "name", "step_supplier_id", "country",
           "individual_consultant", "page_hash", "fetched_at", "public_from")


@dataclass(frozen=True)
class Bidder:
    position: int
    name: str | None
    step_supplier_id: str | None
    country: str | None
    individual_consultant: bool


def _bidder(line: str, country: str, position: int) -> Bidder:
    written = WITH_ID.match(line)
    name, supplier_id = (written["name"], written["id"]) if written else (line, None)
    name = " ".join(name.split())
    individual = name.upper() == INDIVIDUAL_CONSULTANT
    if individual or REMOVED in name or not name:
        name = None
    return Bidder(position, name, supplier_id, " ".join(country.split()) or None, individual)


def _first_name_line(block: list[str]) -> str | None:
    """The line that names the bidder in the lines before its "Country:" line: the first that writes
    a STEP supplier ID, or else the first that is not a labelled line, a price heading or its value."""
    kept, skip = [], False
    for line in block:
        if skip:
            skip = False
        elif line.startswith(PRICE_HEADINGS):
            skip = True
        elif line and not LABELLED.match(line):
            kept.append(line)
    with_id = [line for line in kept if WITH_ID.match(line)]
    return (with_id or kept or [None])[0]


def read(text: str | None) -> list[Bidder]:
    """The awarded bidders a notice's plain text lists, in its order."""
    bidders: list[Bidder] = []
    inside, block = False, []
    for line in (line.strip() for line in (text or "").split("\n")):
        if line in AWARDED:
            inside, block = True, []
        elif line in NOT_AWARDED:
            inside = False
        elif inside and line.startswith(COUNTRY):
            if (name := _first_name_line(block)) is not None:
                bidders.append(_bidder(name, line[len(COUNTRY):], len(bidders) + 1))
            block = []
        elif inside:
            block.append(line)
    return bidders


def _sql(name: str) -> str:
    return (resources.files("strata.knowledge.suppliers") / "sql" / name).read_text()


def store(engine: Engine) -> int:
    """Add the awarded bidders of each Contract Award notice page not read yet. Returns the rows added."""
    result = engine.run(_sql("notices_to_read.sql"))
    added = []
    for notice in (dict(zip(result.columns, row)) for row in result.rows):
        for bidder in read(notice["notice_text"]):
            added.append((notice["notice_id"], bidder.position, notice["project_id"], notice["step_reference"],
                          bidder.name, bidder.step_supplier_id, bidder.country, bidder.individual_consultant,
                          notice["page_hash"], notice["fetched_at"], notice["public_from"]))
    return engine.insert_rows("strata.silver.notice_bidders", COLUMNS, added)
