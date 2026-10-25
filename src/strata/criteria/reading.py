"""Reading text through the item registry (config/criteria_items.toml): what a notice requires, why an award
notice rejected a bid, and how a notice's requirement compares with yours (ticket 31).

- rejection_reasons() gives an award notice's Reason for Rejection values, word for word, in the order the
  notice lists them, and never a bidder: a line that names a bidder (one with a STEP supplier ID in brackets,
  one before a "Country:" line, a contact removed at ingestion) is never taken for a reason, even when a
  notice leaves a reason blank. reason_item() puts a reason under the first item whose synonyms it holds.
- requirements() finds, in one notice passage, each sentence that sets a requirement: it holds an item's
  synonym, and it or the passage's section heading holds one of the registry's cues ("at least",
  "criteria"). parts() reads the numbers a requirement states: how many contracts, a minimum amount in its
  currency, the years a contract must fall within, and a minimum number of years.
- relation() compares a notice's requirement with yours, part by part, over the parts your text sets: a part
  the notice does not set asks less than yours, and a longer window of years asks less. All parts equal is
  "same", none more and one less is "less", none less and one more is "more", and anything else, including
  an amount in another currency (no exchange-rate source is registered), is "different": the notice set it
  in other terms.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from strata.config import CriteriaItem, CriteriaItems

NUMBER_WORDS = {word: value for value, word in enumerate((
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
    "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"))}
SCALES = {"million": Decimal(1_000_000), "m": Decimal(1_000_000), "mn": Decimal(1_000_000),
          "billion": Decimal(1_000_000_000), "bn": Decimal(1_000_000_000), "thousand": Decimal(1000)}
USD = "USD"
CURRENCIES = {"US$": USD, "US $": USD, "USD": USD, "$": USD, "US DOLLARS": USD, "KES": "KES", "KSH": "KES",
              "KSHS": "KES", "EUR": "EUR", "€": "EUR"}
REASON = "reason for rejection"
NOT_A_REASON = re.compile(r"\(\d{3,}\)\s*$|\[contact removed\]|^country\s*:|^(bid price|evaluated bid price|signed "
                          r"contract price|rejected (bidder|firm)|evaluated (bidder|firm)|awarded (bidder|firm))",
                          re.IGNORECASE)
COUNT = re.compile(r"(?P<n>[A-Za-z]+|\d+)\s*(?:\((?P<d>\d+)\))?\s+(?:no\.?\s+)?(?:similar\s+|successful\s+)?"
                   r"(?:assignments?|projects?|contracts?|works)\b", re.IGNORECASE)
WINDOW = re.compile(r"\b(?:in|within|during|over)\s+the\s+(?:last|past|preceding)\s+(?P<n>[A-Za-z]+|\d+)\s*"
                    r"(?:\((?P<d>\d+)\))?\s+years?\b", re.IGNORECASE)
YEARS = re.compile(r"(?P<n>[A-Za-z]+|\d+)\s*(?:\((?P<d>\d+)\))?\s+years?\s+(?:of\s+)?(?:\w+\s+){0,2}?experience\b",
                   re.IGNORECASE)
# "A minimum of 10 years in consultancy as a core business": a minimum of years with no word for experience.
MINIMUM_YEARS = re.compile(r"\b(?:a\s+minimum\s+of|minimum\s+of|at\s+least)\s+(?P<n>[A-Za-z]+|\d+)\s*"
                           r"(?:\((?P<d>\d+)\))?\s+years?\b", re.IGNORECASE)
AMOUNT = re.compile(r"(?P<cur>US\s?\$|USD|US dollars|KES|KShs?|EUR|€|\$)\s?(?P<num>\d[\d,]*(?:\.\d+)?)\s*"
                    r"(?P<scale>million|billion|thousand|mn|bn|m)?\b", re.IGNORECASE)
SENTENCE_END = re.compile(r"(?<=[.;:])\s+(?=[A-Z(\"'])|\n+")


def _holds(text: str, word: str) -> bool:
    """Whether the text holds the word or phrase whole, whatever its case."""
    return re.search(rf"(?<![\w-]){re.escape(word)}(?![\w-])", text, re.IGNORECASE) is not None


def items_in(text: str, items: Iterable[CriteriaItem]) -> list[CriteriaItem]:
    """The items whose synonyms the text holds, in the registry's order."""
    return [item for item in items if any(_holds(text, word) for word in item.synonyms)]


# ── Award notices ────────────────────────────────────────────────────────

PRICE_LINE = re.compile(r"^(bid price|evaluated bid price|signed contract price|final evaluation price|read out "
                        r"price|[A-Z]{3}\s+[\d.,]+$|[A-Z]{3}$)", re.IGNORECASE)


def _named_lines(lines: list[str]) -> set[str]:
    """The lines of an award notice that name a bidder: the lines before each "Country:" line, back to the
    last reason, price or heading, and each line that ends with a STEP supplier ID in brackets."""
    reasons = {index + 1 for index, line in enumerate(lines) if line.strip().lower() == REASON}
    named = set()
    for index, line in enumerate(lines):
        stripped = line.strip()
        if re.search(r"\(\d{3,}\)\s*$", stripped):
            named.add(stripped)
        if not stripped.lower().startswith("country:"):
            continue
        back = index - 1
        while back >= 0 and back >= index - 4:
            above = lines[back].strip()
            if (not above or back in reasons or above.lower() == REASON or above.endswith(":")
                    or PRICE_LINE.search(above)):
                break
            named.add(above)
            back -= 1
    return named


def rejection_reasons(text: str) -> list[str]:
    """The award notice's Reason for Rejection values, word for word, in the order it lists them."""
    lines = (text or "").splitlines()
    named = _named_lines(lines)
    found = []
    for index, line in enumerate(lines):
        if line.strip().lower() != REASON or index + 1 >= len(lines):
            continue
        reason = lines[index + 1].strip()
        if not reason or NOT_A_REASON.search(reason) or reason in named:
            continue
        found.append(reason)
    return found


def reason_item(reason: str, items: CriteriaItems) -> str:
    """The item a rejection reason concerned: the first whose synonyms it holds, or other."""
    found = items_in(reason, items.items)
    return found[0].key if found else "other"


# ── Notices' requirements ────────────────────────────────────────────────

@dataclass(frozen=True)
class Amount:
    value: Decimal
    currency: str
    written: str


@dataclass(frozen=True)
class Requirement:
    item_key: str
    text: str  # the sentence that sets it, word for word
    start: int  # where it sits in its passage's text
    end: int
    parts: dict


def sentences(text: str) -> list[tuple[int, int]]:
    """Where each sentence of a passage starts and ends: at a stop, a semicolon or a colon before a capital,
    and at each line end."""
    spans, start = [], 0
    for match in SENTENCE_END.finditer(text):
        if match.start() > start:
            spans.append((start, match.start()))
        start = match.end()
    if start < len(text):
        spans.append((start, len(text)))
    return [(begin, end) for begin, end in spans if text[begin:end].strip()]


def _number(word: str | None, digits: str | None) -> int | None:
    if digits:
        return int(digits)
    if word is None:
        return None
    if word.isdigit():
        return int(word)
    return NUMBER_WORDS.get(word.lower())


def _first(pattern: re.Pattern, text: str) -> int | None:
    for match in pattern.finditer(text):
        value = _number(match.group("n"), match.group("d"))
        if value is not None and value > 0:
            return value
    return None


def amount_in(text: str) -> Amount | None:
    match = AMOUNT.search(text)
    if not match:
        return None
    try:
        value = Decimal(match.group("num").replace(",", ""))
    except InvalidOperation:
        return None
    scale = (match.group("scale") or "").lower()
    value *= SCALES.get(scale, Decimal(1))
    currency = CURRENCIES.get(re.sub(r"\s+", " ", match.group("cur").upper()).replace("US $", "US$"), match.group("cur"))
    return Amount(value, currency, match.group(0).strip())


def parts(text: str, item: CriteriaItem) -> dict:
    """The numbers a requirement states, for the parts its item can measure."""
    found = {}
    if "contracts" in item.parts:
        found["contracts"] = _first(COUNT, text)
    if "window_years" in item.parts:
        found["window_years"] = _first(WINDOW, text)
    if "years" in item.parts:
        without_windows = WINDOW.sub(" ", text)
        found["years"] = _first(YEARS, without_windows) or _first(MINIMUM_YEARS, without_windows)
    if "amount" in item.parts:
        amount = amount_in(text)
        found["amount"] = None if amount is None else {"value": str(amount.value), "currency": amount.currency,
                                                       "written": amount.written}
    return found


def requirements(text: str, section: str | None, items: CriteriaItems) -> list[Requirement]:
    """Every requirement one notice passage sets, each sentence once under each criterion item it names."""
    found = []
    heading_cued = any(_holds(section or "", cue) for cue in items.cues)
    for start, end in sentences(text):
        sentence = text[start:end].strip()
        offset = text.index(sentence, start)
        if not (heading_cued or any(_holds(sentence, cue) for cue in items.cues)):
            continue
        for item in items_in(sentence, items.criteria):
            found.append(Requirement(item.key, sentence, offset, offset + len(sentence), parts(sentence, item)))
    return found


# ── Comparing ────────────────────────────────────────────────────────────

LESS, SAME, MORE, DIFFERENT = "less", "same", "more", "different"
RELATIONS = (LESS, SAME, MORE, DIFFERENT)


def _sign(value: Decimal) -> int:
    return (value > 0) - (value < 0)


def relation(yours: dict, theirs: dict) -> str:
    """How a notice's requirement compares with yours, over the parts your text sets: less, same, more or
    different (set in other terms)."""
    directions = []
    for part, mine in yours.items():
        if mine is None:
            continue
        given = theirs.get(part)
        if part == "amount":
            mine_amount = Decimal(str(mine["value"]))
            if given is None:
                directions.append(-1)
            elif given["currency"] != mine["currency"]:
                return DIFFERENT
            else:
                directions.append(_sign(Decimal(given["value"]) - mine_amount))
        elif part == "window_years":
            # A longer window lets older contracts count, so it asks less; no window asks least.
            directions.append(-1 if given is None else _sign(Decimal(mine) - Decimal(given)))
        else:
            directions.append(-1 if given is None else _sign(Decimal(given) - Decimal(mine)))
    if not directions:
        return DIFFERENT
    if all(direction == 0 for direction in directions):
        return SAME
    if all(direction <= 0 for direction in directions):
        return LESS
    if all(direction >= 0 for direction in directions):
        return MORE
    return DIFFERENT
