"""The awarded bidders of each Contract Award notice, read from the notice's plain text.

An award notice writes each awarded bidder as its name, with its STEP supplier ID in brackets when it
has one, then its address and a "Country:" line. A works or goods notice heads the list "Awarded
Bidder(s):", a consultant notice "Awarded Firm(s):", and a small assignment "Awarded
Firm/Individual:". Several awarded bidders on one notice are the members of a joint venture. A
consultant notice adds lines such as "Registry ID: 24" and the evaluation scores; none of them is a
bidder, and none is kept, because suppliers are never scored or ranked. A person hired as an
individual consultant is never named: a notice writes "Individual Consultant", or writes the person
with a personal title such as DR. or MR., which the awards transform also reads as a person
(strata.lakehouse.clean.titled).

It reads strata.silver.notices.notice_text, the notice after the fetch removed contact details, and
never the recorded files, which keep them on purpose (data/fixture/README.md). A name the fetch
removed as a person's contact detail stays removed. read() takes the text and gives plain rows, and
store() adds the rows of each notice page not read yet to strata.silver.notice_bidders.

read_bids() reads every bid the notice lists, in its order: the awarded, evaluated and rejected ones,
each with its prices as the notice writes them and its Reason for Rejection word for word (ticket 22).
The members of a joint venture are listed one after another before their one price, so they share one
bid. store_bids() adds them to strata.silver.notice_bids, which the contract trail shows. A notice that
lists evaluation scores or ranks is marked, and the scores are never kept.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import resources

from strata.lakehouse import clean
from strata.lakehouse.engine import Engine

AWARDED = ("Awarded Bidder(s):", "Awarded Firm(s):", "Awarded Firm/Individual:")
# The parts that follow the awarded bidders, which end their list. A notice's beneficial ownership
# details name the firm again, and the people who own it, who are never bidders.
NOT_AWARDED = ("Evaluated Bidder(s):", "Evaluated Firm(s):", "Rejected Bidder(s):", "Rejected Firm(s):",
               "Beneficial Ownership Details")
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
    individual = name.upper() == INDIVIDUAL_CONSULTANT or clean.titled(name)
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


# ── Every bid an award notice lists (ticket 22) ─────────────────────────

SECTIONS = {"Awarded Bidder(s):": "awarded", "Awarded Firm(s):": "awarded", "Awarded Firm/Individual:": "awarded",
            "Evaluated Bidder(s):": "evaluated", "Evaluated Firm(s):": "evaluated",
            "Rejected Bidder(s):": "rejected", "Rejected Firm(s):": "rejected"}
END = ("Beneficial Ownership Details",)
# Each price heading, whose value is on the next line, by the field it fills.
PRICES = {"Bid Price at Opening": "price_at_opening", "Read Out Price": "price_at_opening",
          "Evaluated Bid Price": "evaluated_price", "Final Evaluation Price": "evaluated_price",
          "Signed Contract price": "signed_price", "Signed Contract Price": "signed_price",
          "Reason for Rejection": "reason"}
SCORES = re.compile(r"^(Scores\b|Rank:|Combined:|Technical:|Financial:)", re.IGNORECASE)
PRICE = re.compile(r"^(?P<currency>[A-Z]{3})\b\s*(?P<amount>.*)$")

BID_COLUMNS = ("notice_id", "bid", "member", "project_id", "step_reference", "section", "name", "step_supplier_id",
               "country", "individual_consultant", "currency", "price_at_opening", "evaluated_price", "signed_price",
               "reason", "price_at_opening_label", "evaluated_price_label", "notice_lists_scores", "page_hash",
               "fetched_at", "public_from")


@dataclass
class Bid:
    bid: int
    section: str
    members: list[Bidder]
    currency: str | None = None
    price_at_opening: str | None = None
    evaluated_price: str | None = None
    signed_price: str | None = None
    reason: str | None = None
    labels: dict = field(default_factory=dict)


def _price(value: str) -> tuple[str | None, str | None]:
    """A price line as the notice writes it, split into its currency and its amount: "KES 61503269.60"."""
    written = PRICE.match(value.strip())
    if not written:
        return None, value.strip() or None
    return written["currency"], written["amount"].strip() or None


def read_bids(text: str | None) -> tuple[list[Bid], bool]:
    """Every bid a notice's plain text lists, in its order, and whether it lists evaluation scores or ranks."""
    bids: list[Bid] = []
    section, block, current, priced, expect, scores = None, [], None, False, None, False
    for line in (line.strip() for line in (text or "").split("\n")):
        if expect is not None:  # the line after a price heading holds its value
            key, label = expect
            expect = None
            if current is not None:
                if key == "reason":
                    current.reason = line or None
                else:
                    currency, amount = _price(line)
                    current.currency = current.currency or currency
                    setattr(current, key, amount)
                    current.labels[key] = label
                priced = True
            continue
        if line in SECTIONS:
            section, block, current, priced = SECTIONS[line], [], None, False
        elif line.startswith(END):
            section, current = None, None
        elif section is None:
            continue
        elif line.startswith(COUNTRY):
            name, block = _first_name_line(block), []
            if name is None:
                continue
            member = _bidder(name, line[len(COUNTRY):], 1)
            if current is not None and not priced:  # a joint venture's next member, before their one price
                current.members.append(Bidder(len(current.members) + 1, member.name, member.step_supplier_id,
                                              member.country, member.individual_consultant))
            else:
                current, priced = Bid(len(bids) + 1, section, [member]), False
                bids.append(current)
        elif line in PRICES:
            expect = (PRICES[line], line)
        elif SCORES.match(line):
            scores = True
        else:
            block.append(line)
    return bids, scores


def store_bids(engine: Engine) -> int:
    """Add every bid of each Contract Award notice page not read yet. Returns the rows added."""
    result = engine.run(_sql("bid_notices_to_read.sql"))
    added = []
    for notice in (dict(zip(result.columns, row)) for row in result.rows):
        bids, scores = read_bids(notice["notice_text"])
        for bid in bids:
            for member in bid.members:
                added.append((notice["notice_id"], bid.bid, member.position, notice["project_id"],
                              notice["step_reference"], bid.section, member.name, member.step_supplier_id,
                              member.country, member.individual_consultant, bid.currency, bid.price_at_opening,
                              bid.evaluated_price, bid.signed_price, bid.reason, bid.labels.get("price_at_opening"),
                              bid.labels.get("evaluated_price"), scores, notice["page_hash"], notice["fetched_at"],
                              notice["public_from"]))
    return engine.insert_rows("strata.silver.notice_bids", BID_COLUMNS, added)
