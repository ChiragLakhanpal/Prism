"""The verifier: it runs on every answer, before anyone sees it (CLAUDE.md rules 1 and 2).

The app ran every tool the agent asked for, so it holds every row and passage the answer may cite
(ADR 0003, the turn's Facts). Each claim is checked against them:

1. Every number and date the sentence states matches a value in a row the sentence cites, at the same
   rounding, or sits inside the words it quotes from a cited passage that is not a table summary. A
   table's summary passage is Strata's own words about the table, so a number it alone holds, quoted
   or not, is removed with a reason of its own (number_only_in_table_summary): the table's rows back
   numbers, its summary never does.
   The numbers and dates are read from the sentence itself, so one the agent left off its list is
   still checked. Every digit run is a number, as in "45-day" or "US$1.2M", unless its token is an id
   (ID_SHAPES); so is a number written in words ("forty-five", "zero", or "one" unless it stands for a
   thing named before), and an amount no row holds as written ("half", but not "the middle half", which
   names a part of a past range). A passage backs only its
   dates, such as its report's date: its text is never a value, and its page, paragraph and version
   numbers say where it is, not what the report counted, so a number from a passage must be quoted.
2. Every id the sentence cites came back from a tool in this turn. A record, quote or advice sentence
   must cite at least one.
3. Every quote is word for word on the cited page, ignoring only whitespace, line-end hyphenation and
   whether a quote mark is curly or straight, and starts and ends where the page's words and numbers
   do: "10" is not a quote from "108 of 328", nor "334 km" from "2,334 km".
   The quote checked is the one the person reads: the words in the sentence's quote marks must be in
   the claim's quote, and that quote on its passage. Quote marks with no quote, or with words that are
   not on the page, fail; so does a quote the sentence never shows in quote marks. Words quoted from a
   cited record's text value, such as a STEP description, are on that record.

Checks 4 to 6 come with ticket 24. A sentence that fails is removed, with its reasons in this order:
an id that did not come back first, since nothing else about that sentence can be checked, then a quote
that is not on its page or not in the sentence, then numbers and dates. A number inside quoted words
that are not on the page is counted as unmatched but gets no reason of its own, because the quote's
reason already explains it.
Each reason has a code, and the copy file (web/src/copy.ts, removed.reasons) has its sentence.
"""

from __future__ import annotations

import datetime as dt
import decimal
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from strata.agent.claims import Claim
from strata.harness.facts import Facts
from strata.harness.turn import Event
from strata.reader.passages import NOTICE_TEXT, TABLE_SUMMARY
from strata.reader.templates import template_for

CHECKS_RUN = (1, 2, 3)
# Reason codes. web/src/copy.ts holds one sentence for each, under removed.reasons.
NUMBER, DATE, NOT_RETURNED, NO_SOURCE, NOT_ON_PAGE, NOT_IN_SENTENCE, ONLY_IN_SUMMARY = (
    "number_not_in_records", "date_not_in_records", "id_not_returned", "no_source", "quote_not_on_page",
    "quote_not_in_sentence", "number_only_in_table_summary")
REASONS = (NUMBER, DATE, NOT_RETURNED, NO_SOURCE, NOT_ON_PAGE, NOT_IN_SENTENCE, ONLY_IN_SUMMARY)
MUST_CITE = ("record", "quote", "advice")

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
MONTH = "|".join(MONTHS)
SHORT = {name[:3]: number for number, name in enumerate(MONTHS, 1)}


# ── Numbers and dates in a sentence ──────────────────────────────────────

@dataclass(frozen=True)
class When:
    """A date as precisely as the sentence gave it: a year, a month or a day."""

    year: int
    month: int | None = None
    day: int | None = None

    def covers(self, day: dt.date) -> bool:
        return day.year == self.year and self.month in (None, day.month) and self.day in (None, day.day)


@dataclass(frozen=True)
class Mention:
    kind: str  # "number" or "date"
    text: str
    value: Decimal | When | str  # a str is an amount no row holds as written, such as "half"
    start: int | None = None
    end: int | None = None


def _month(name: str) -> int:
    return SHORT[name[:3].title()]


DATES = (
    (re.compile(rf"\b({MONTH})\s+(\d{{1,2}}),?\s+(\d{{4}})\b"), lambda m: When(int(m[3]), _month(m[1]), int(m[2]))),
    (re.compile(rf"\b(\d{{1,2}})\s+({MONTH})\s+(\d{{4}})\b"), lambda m: When(int(m[3]), _month(m[2]), int(m[1]))),
    (re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b"), lambda m: When(int(m[1]), int(m[2]), int(m[3]))),
    (re.compile(r"\b(\d{1,2})-(" + "|".join(SHORT) + r")-(\d{4})\b"), lambda m: When(int(m[3]), _month(m[2]),
                                                                                  int(m[1]))),
    (re.compile(rf"\b({MONTH})\s+(\d{{4}})\b"), lambda m: When(int(m[2]), _month(m[1]))),
)
# Every digit run is a number, wherever it sits ("45-day", "US$1.2M", "300k", "10-15"), unless its whole
# token is one of these ids. A fiscal year is read before them, so FY19-20 is not taken for a name.
ID_SHAPES = (
    r"\bstrata\.\w+\.\w+:[^\s,;()\"]*[^\s,;()\".]",  # an evidence id, strata.gold.passage:31525018/v1/54
    r"\b\d+/v\d+/[\w.]*\w",  # a passage id, 31525018/v1/54
    r"\bP\d{6}\b",  # a project, P130164
    # A credit, loan or trust fund with four digits or more: IDA-60290, IBRD 8541, TF0A1234, IDA 51030KE,
    # or as STEP writes it, IDA / 60300 or IDA \u2013 6030 KE. "IBRD 45 contracts" is a count, and a year
    # alone after it, as in "the IDA 2019 funds", is a year.
    r"\b(?:IDA|IBRD|TF)\s*[-/\u2013]?\s*(?!(?:19|20)\d\d\b)[A-Z0-9]{0,2}\d{4,}[A-Z]{0,2}\b",
    # A STEP reference has three parts or more: KE-NWWDA-541062-CW-RFQ, NWWDA-WSDP-03-2019-2020 or
    # MWI-WSDP-001. Q3-2020 and FY-2019 have two, so their numbers are read.
    r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}\b",
    # A bid or contract reference written with slashes, with three parts or more: KE/TAVEVO/82755/GO/RFQ or
    # KALRO/HQTS/053/23-24. It starts with a letter, so 2019/20 is two numbers.
    r"\b[A-Z][A-Z0-9.]*(?:/[A-Z0-9.\-]+){2,}\b",
    r"\bCOVID-19\b",
    r"\b(?:[IVX]+|\d+)\.[A-Za-z]\b",  # a section label, III.B or 10.b
)
ID = re.compile("|".join(ID_SHAPES))
DIGITS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?")
# A World Bank fiscal year, FY2019 or FY19: a number a row must hold, such as a fiscal_year column.
FISCAL_YEAR = re.compile(r"\bFY ?(\d{4}|\d{2})\b")
YEARS = range(1900, 2101)
# DESIGN.md section 7 writes one to nine in words, and a model may write any number so. Words joined by a
# space or a hyphen make one number: "forty-five", "three hundred and twenty-eight", "a dozen". "One" alone
# is a number ("one bid", "one of 37") except where it stands for a thing named before: after a word in
# PRONOUN_BEFORE ("no one", "each one", "the middle one", the package at a past range's middle), or before
# "another" or "of the" with no count after it, unless a word in ONLY comes first ("only one of the firms"
# is a count).
SMALL = {"zero": 0} | {word: value for value, word in enumerate((
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen",
    "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"), 1)}
SMALL |= {word: value for value, word in zip(range(20, 100, 10), (
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"), strict=True)}
SCALES = {"hundred": 100, "thousand": 1000, "dozen": 12}
# Amounts no row holds as written: a proportion or a vague count. A sentence that states one is removed.
VAGUE = {"half", "twice", "double", "triple", "hundreds", "thousands", "dozens"}
FRACTIONS = {"third", "quarter"}  # as "a third" or "a quarter"
WORD = re.compile(r"[A-Za-z]+")
COUNT_AFTER_ONE = re.compile(r" (?:of|in) (?:the )?(?:\d|(?:" + "|".join(SMALL) + r")\b)", re.I)
PRONOUN_BEFORE = {"no", "any", "each", "every", "this", "that", "which", "the", "middle"}
PRONOUN_AFTER = re.compile(r" (?:another|of (?:the|its|their|these|those))\b", re.I)
ONLY = {"only", "just"}
# "The first half" and "the first half of the year" are times, not amounts; "the first half of the
# packages" is an amount. "The middle half" names a part of a past range, the band from the quarter to the
# three-quarter point, whose ends are the numbers checked.
TIME_BEFORE_HALF = {"first", "second"}
PART_BEFORE_HALF = {"middle"}
HALF_OF = re.compile(r" of\b", re.I)
HALF_OF_A_TIME = re.compile(
    r" of (?:the )?(?:(?:fiscal |calendar )?year|month|week|quarter|period|decade|FY ?\d{2,4}|fiscal \d{4}|\d{4})\b",
    re.I)


def _word_value(words: list[str]) -> Decimal:
    total = current = 0
    for word in words:
        if word in SMALL:
            current += SMALL[word]
        elif word in ("a", "an"):
            current = 1
        elif word == "thousand":
            total, current = total + (current or 1) * 1000, 0
        elif word in SCALES:
            current = (current or 1) * SCALES[word]
    return Decimal(total + current)


def _number_words(text: str) -> list[tuple[int, int, Decimal | str]]:
    """Each number written in words: where it is, and its value, or its word when no row can hold it."""
    tokens = list(WORD.finditer(text))
    lower = [token.group(0).lower() for token in tokens]

    def gap(i: int) -> str:
        return text[tokens[i].end():tokens[i + 1].start()] if i + 1 < len(tokens) else ""

    def half_is_a_time(i: int) -> bool:
        after_half = tokens[i].end()
        return i > 0 and lower[i - 1] in TIME_BEFORE_HALF and (
            not HALF_OF.match(text, after_half) or bool(HALF_OF_A_TIME.match(text, after_half)))

    found, i = [], 0
    while i < len(tokens):
        word, after = lower[i], lower[i + 1] if i + 1 < len(tokens) else ""
        if word in VAGUE:
            names_a_part = word == "half" and i > 0 and gap(i - 1) == " " and lower[i - 1] in PART_BEFORE_HALF
            if not (word == "half" and half_is_a_time(i)) and not names_a_part:
                found.append((tokens[i].start(), tokens[i].end(), word))
        elif word in ("a", "an") and gap(i) == " " and after in FRACTIONS:
            found.append((tokens[i].start(), tokens[i + 1].end(), f"a {after}"))
            i += 1
        elif word in SMALL or (word in ("a", "an") and gap(i) == " " and after in SCALES):
            j = i
            while j + 1 < len(tokens):
                if gap(j) in (" ", "-") and (lower[j + 1] in SMALL or lower[j + 1] in SCALES):
                    j += 1
                elif lower[j] in SCALES and gap(j) == " " and lower[j + 1] == "and" and gap(j + 1) == " " \
                        and j + 2 < len(tokens) and lower[j + 2] in SMALL:
                    j += 2
                else:
                    break
            pronoun = j == i and word == "one" and not COUNT_AFTER_ONE.match(text, tokens[i].end()) and (
                (i > 0 and gap(i - 1) == " " and lower[i - 1] in PRONOUN_BEFORE)
                or (PRONOUN_AFTER.match(text, tokens[i].end()) and not (i > 0 and lower[i - 1] in ONLY)))
            if not pronoun:
                found.append((tokens[i].start(), tokens[j].end(), _word_value(lower[i:j + 1])))
            i = j
        i += 1
    return found


def mentions(text: str) -> list[Mention]:
    """The numbers and dates a text states, each with its place in the text. A four-digit number that
    could be a year is read as a year."""
    found: list[Mention] = []
    ids: list[tuple[int, int]] = []

    def free(start: int, end: int) -> bool:
        return all(end <= other.start or start >= other.end for other in found) and all(
            end <= id_start or start >= id_end for id_start, id_end in ids)

    for pattern, build in DATES:
        for match in pattern.finditer(text):
            if not free(*match.span()):
                continue
            try:
                when = build(match)
                dt.date(when.year, when.month or 1, when.day or 1)
            except ValueError:
                continue  # not a real date, such as February 30
            found.append(Mention("date", match.group(0), when, *match.span()))
    for match in FISCAL_YEAR.finditer(text):
        if free(*match.span()):
            year = int(match[1]) if len(match[1]) == 4 else 2000 + int(match[1])
            found.append(Mention("number", match.group(0), Decimal(year), *match.span()))
    ids += [match.span() for match in ID.finditer(text) if free(*match.span())]
    for start, end, value in _number_words(text):
        if free(start, end):
            found.append(Mention("number", text[start:end], value, start, end))
    for match in DIGITS.finditer(text):
        if not free(*match.span()):
            continue
        written = match.group(0)
        if written.isdigit() and len(written) == 4 and int(written) in YEARS:
            found.append(Mention("date", written, When(int(written)), *match.span()))
        else:
            found.append(Mention("number", written, Decimal(written.replace(",", "")), *match.span()))
    return sorted(found, key=lambda mention: mention.start)


def _declared(claim: Claim, stated: list[Mention]) -> list[Mention]:
    """The numbers and dates the claim lists but the sentence does not show: they are checked too, each as
    what its text reads as, whichever list it came in."""
    extra = []
    for text in claim.numbers + claim.dates:
        for mention in mentions(text):
            if not any(mention.value == other.value for other in stated + extra):
                extra.append(Mention(mention.kind, mention.text, mention.value))
    return extra


# ── Values in a row ──────────────────────────────────────────────────────

NOT_VALUES = {"text", "header", "rank", "score"}  # a passage's words, and the search's own ranking
ISO_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")
PLAIN_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")


def row_values(row: Any, numbers: set | None = None, days: set | None = None) -> tuple[set, set]:
    """The numbers and dates a row holds as values, at any depth, leaving out a passage's text."""
    numbers = set() if numbers is None else numbers
    days = set() if days is None else days
    if isinstance(row, Mapping):
        for key, value in row.items():
            if key not in NOT_VALUES:
                row_values(value, numbers, days)
    elif isinstance(row, list | tuple):
        for value in row:
            row_values(value, numbers, days)
    elif isinstance(row, bool) or row is None:
        pass
    elif isinstance(row, int | float | Decimal):
        numbers.add(Decimal(str(row)))
    elif isinstance(row, dt.datetime):
        days.add(row.date())
    elif isinstance(row, dt.date):
        days.add(row)
    elif isinstance(row, str):
        if day := ISO_DAY.match(row.strip()):
            try:
                days.add(dt.date(int(day[1]), int(day[2]), int(day[3])))
            except ValueError:
                pass
        elif PLAIN_NUMBER.match(row.strip()):
            numbers.add(Decimal(row.strip()))
    return numbers, days


def _supports(mention: Mention, numbers: set, days: set) -> bool:
    if mention.kind == "number":
        return mention.value in numbers
    return any(mention.value.covers(day) for day in days) or (
        mention.value.month is None and Decimal(mention.value.year) in numbers)


# ── Quotes on their page ─────────────────────────────────────────────────

HYPHEN_BREAK = re.compile(r"(?<=\w)-[ \t]*\r?\n\s*(?=\w)")


# Curly quote marks, written straight before quotes are compared, since a model often straightens them.
STRAIGHT = str.maketrans({"\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"'})


def _normalized(text: str) -> tuple[str, list[int]]:
    """The text with each run of whitespace as one space, each line-end hyphenation joined and each curly
    quote mark straight, and where each of its characters sits in the original text."""
    text = text.translate(STRAIGHT)  # one character for one, so each place in the text stays where it was
    out: list[str] = []
    where: list[int] = []
    i = 0
    while i < len(text):
        joined = HYPHEN_BREAK.match(text, i)
        if joined:
            i = joined.end()
            continue
        if text[i].isspace():
            if out and out[-1] != " ":
                out.append(" ")
                where.append(i)
            while i < len(text) and text[i].isspace():
                i += 1
            continue
        out.append(text[i])
        where.append(i)
        i += 1
    while out and out[-1] == " ":
        out.pop()
        where.pop()
    return "".join(out), where


# The words a sentence puts in quote marks. The agent is told to use straight double ones in every language;
# curly ones count too, and so do the « » French writes, without the spaces inside them, and single ones,
# straight or curly, as British English writes them. A single mark inside or at the end of a word is an
# apostrophe ("the contractors' bids", "the World Bank's review"), so it neither opens nor closes a quote.
QUOTED = re.compile(r'"([^"]+)"|\u201c([^\u201d]+)\u201d|\u00ab\s*([^\u00bb]+?)\s*\u00bb'
                    r"|(?<![\w'\u2019])\u2018(.+?)\u2019(?!\w)|(?<![\w'\u2019])'(.+?)'(?!\w)")


def quoted_spans(sentence: str) -> list[tuple[int, int]]:
    """Where each run of quoted words sits in the sentence, inside its quote marks."""
    return [match.span(match.lastindex) for match in QUOTED.finditer(sentence)]


def find_quote(quote: str, text: str) -> tuple[int, int] | None:
    """Where the quote is in the text, word for word but for whitespace and line-end hyphenation. It must
    start and end where the text's words or numbers do, so "10" is not in "108 of 328", "ding" is not in
    "rebidding", "US$177" is not in "US$177.6" and "334 km" is not in "2,334 km". A number is read as
    mentions() reads one, so "45" is in "45-day" and "10" in "10-15"."""
    wanted, _ = _normalized(quote)
    if not wanted:
        return None
    held, where = _normalized(text)
    numbers = [match.span() for match in DIGITS.finditer(held)]
    start = held.find(wanted)
    while start >= 0:
        end = start + len(wanted)
        cut_at_start = wanted[0].isalnum() and start > 0 and held[start - 1].isalnum()
        cut_at_end = wanted[-1].isalnum() and end < len(held) and held[end].isalnum()
        inside_a_number = any(left < start < right or left < end < right for left, right in numbers)
        if not (cut_at_start or cut_at_end or inside_a_number):
            return where[start], where[end - 1] + 1
        start = held.find(wanted, start + 1)
    return None


# ── The checks ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Reason:
    check: int
    code: str
    text: str | None = None  # the number, date or id the reason is about


@dataclass(frozen=True)
class Checked:
    """One claim after the checks: its reasons (none when it is kept), and for each number and date it
    states, the evidence id that supports it or None."""

    index: int
    claim: Claim
    reasons: tuple[Reason, ...]
    numbers: tuple[tuple[Mention, str | None], ...]
    dates: tuple[tuple[Mention, str | None], ...]
    quote_span: tuple[int, int] | None  # where the quote sits in its passage's text, when it was found
    quoted: bool = False  # the sentence quotes: it has quote marks, or a quote
    quote_found: bool = False  # and every quoted word is on the page it cites

    @property
    def kept(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class Verdict:
    sentences: tuple[Checked, ...]

    @property
    def kept(self) -> list[Checked]:
        return [sentence for sentence in self.sentences if sentence.kept]

    @property
    def removed(self) -> list[Checked]:
        return [sentence for sentence in self.sentences if not sentence.kept]

    def counts(self) -> dict:
        """The counts behind the check line, over everything the agent wrote, removed sentences included."""
        numbers = [found for sentence in self.sentences for _, found in sentence.numbers]
        dates = [found for sentence in self.sentences for _, found in sentence.dates]
        quotes = [sentence for sentence in self.sentences if sentence.quoted]
        cited = {evidence: sentence for sentence in self.sentences for evidence in sentence.claim.evidence_ids}
        not_back = {reason.text for sentence in self.sentences for reason in sentence.reasons
                    if reason.code == NOT_RETURNED}
        return {
            "checks_run": list(CHECKS_RUN),
            "sentences": {"written": len(self.sentences), "kept": len(self.kept), "removed": len(self.removed)},
            "numbers": {"total": len(numbers), "matched": sum(found is not None for found in numbers)},
            "dates": {"total": len(dates), "matched": sum(found is not None for found in dates)},
            "quotes": {"total": len(quotes), "found": sum(sentence.quote_found for sentence in quotes)},
            "sources": {"total": len(cited), "returned": len(set(cited) - not_back)},
        }


def _is_passage(row: Mapping | None) -> bool:
    return row is not None and "passage_id" in row and isinstance(row.get("text"), str)


def _summary(row: Mapping | None) -> bool:
    """Whether a cited row is a table's summary passage, which Strata wrote and which backs no number."""
    return _is_passage(row) and row.get("kind") == TABLE_SUMMARY


def _holds_number(text: str, mention: Mention) -> bool:
    """Whether a passage's text writes the number the sentence states."""
    return any(isinstance(found.value, Decimal) and found.value == mention.value for found in mentions(text))


def _values(row: Mapping | None) -> tuple[set, set]:
    """The numbers and dates a cited row backs. A passage backs its dates and no number."""
    numbers, days = row_values(row)
    return (set(), days) if _is_passage(row) else (numbers, days)


def _texts(row: Any) -> list[str]:
    """The text values a row holds at any depth, leaving out a passage's text."""
    if isinstance(row, Mapping):
        return [text for key, value in row.items() if key not in NOT_VALUES for text in _texts(value)]
    if isinstance(row, list | tuple):
        return [text for value in row for text in _texts(value)]
    return [row] if isinstance(row, str) else []


def _name_words(text: str) -> str:
    """The text's words with each run of spaces, hyphens and dashes as one space, as written."""
    return " ".join(re.sub(r"[\s\-\u2013\u2014]+", " ", text).split())


def _in_a_value(mention: Mention, sentence: str, texts: list[str]) -> bool:
    """A number word that is part of a name in a text value of a cited row, such as "Two" in STEP's market
    approach "Single Stage - Two Envelope": a name, not a count. It starts with a capital and is not the
    sentence's first word, and with a neighbouring word that also starts with a capital, it stands in the
    value as written, case for case and as whole words. So "a total of two firms" is a count even when a
    value holds "Supply of Two Airside Fire Tenders"."""
    if mention.start is None or not isinstance(mention.value, Decimal) or any(ch.isdigit() for ch in mention.text):
        return False
    if not mention.text[0].isupper() or not re.search(r"[A-Za-z]", sentence[:mention.start]):
        return False
    after = re.match(r"[\s-]+([A-Z][A-Za-z]*)", sentence[mention.end:])
    before = re.search(r"([A-Z][A-Za-z]*)[\s-]+$", sentence[:mention.start])
    phrases = [f"{mention.text} {after[1]}"] if after else []
    phrases += [f"{before[1]} {mention.text}"] if before else []
    values = [_name_words(text) for text in texts]
    return any(re.search(rf"\b{re.escape(_name_words(phrase))}\b", value) for phrase in phrases for value in values)


def check(index: int, claim: Claim, facts: Facts) -> Checked:
    reasons: list[Reason] = []
    # Check 2: every cited id came back this turn.
    returned = [evidence for evidence in claim.evidence_ids if facts.came_back(evidence)]
    reasons += [Reason(2, NOT_RETURNED, evidence) for evidence in claim.evidence_ids if evidence not in returned]
    if not claim.evidence_ids and claim.kind in MUST_CITE:
        reasons.append(Reason(2, NO_SOURCE))
    records = [(evidence, facts.get(evidence)) for evidence in returned if not _is_passage(facts.get(evidence))]
    # Check 3: the words in the sentence's quote marks are its quote, and its quote is on its page. Words
    # quoted from a cited record's text value, such as a STEP description, are on that record.
    quote, span, backs = claim.quote, None, False
    if quote is not None:
        passage = facts.get(quote.evidence_id)
        if _is_passage(passage):
            span = find_quote(quote.text, passage["text"])
            backs = span is not None and not _summary(passage)
        if span is None and facts.came_back(quote.evidence_id):
            reasons.append(Reason(3, NOT_ON_PAGE, quote.evidence_id))
    spans = []  # each run of quoted words: where it is in the sentence, and the evidence id that holds it
    for start, end in quoted_spans(claim.sentence):
        words = claim.sentence[start:end]
        source = quote.evidence_id if quote is not None and span is not None and find_quote(words, quote.text) \
            else next((evidence for evidence, row in records if any(find_quote(words, text) for text in _texts(row))),
                      None)
        spans.append((start, end, source))
    if quote is None or span is not None:
        if any(source is None for *_, source in spans):
            reasons.append(Reason(3, NOT_ON_PAGE, None if quote is None else quote.evidence_id))
        elif quote is not None and not any(source == quote.evidence_id for *_, source in spans):
            reasons.append(Reason(3, NOT_IN_SENTENCE, quote.evidence_id))
    quote_reasons = [reason for reason in reasons if reason.check == 3]
    explained = bool(quote_reasons) or any(reason.code == NOT_RETURNED for reason in reasons)
    # Check 1: every number and date matches a value in a cited row, or sits inside quoted words that a
    # cited row's text or a cited passage that is not a table summary holds.
    rows = [(evidence, _values(facts.get(evidence))) for evidence in returned]
    texts = [text for _, row in records for text in _texts(row)]
    stated = [mention for mention in mentions(claim.sentence) if not _in_a_value(mention, claim.sentence, texts)]
    checked: dict[str, list] = {"number": [], "date": []}
    for mention in stated + _declared(claim, stated):
        found = next((evidence for evidence, (numbers, days) in rows if _supports(mention, numbers, days)), None)
        inside = next((source for start, end, source in spans
                       if mention.start is not None and start <= mention.start and mention.end <= end), False)
        if found is None and inside and (inside != getattr(quote, "evidence_id", None) or backs):
            found = inside
        checked[mention.kind].append((mention, found))
        # A number inside quoted words that are not on the page, or whose page did not come back, gets no
        # reason of its own: the quote's or the id's reason explains it. A number only a cited table
        # summary holds says so, since the summary is Strata's words, not the table's rows.
        if found is None and not (inside is None and explained):
            only_summary = mention.kind == "number" and any(
                _summary(facts.get(evidence)) and _holds_number(facts.get(evidence)["text"], mention)
                for evidence in returned)
            reasons.append(Reason(1, ONLY_IN_SUMMARY if only_summary else NUMBER if mention.kind == "number" else DATE,
                                  mention.text))
    quoted = bool(spans) or quote is not None
    # A quote counts as on its page only when its page was checked: a quote whose passage did not come
    # back this turn was compared with nothing, so the check line may not count it.
    on_page = quoted and not quote_reasons and (quote is None or span is not None)
    return Checked(index, claim, tuple(reasons), tuple(checked["number"]), tuple(checked["date"]), span,
                   quoted=quoted, quote_found=on_page)


def verify(claims: Iterable[Claim], facts: Facts) -> Verdict:
    """Checks 1 to 3 on each claim, in the order the agent wrote them."""
    return Verdict(tuple(check(index, claim, facts) for index, claim in enumerate(claims)))


# ── The answer's events ──────────────────────────────────────────────────

def labels(row: Mapping | None) -> dict:
    """What the evidence card and the source switcher call a source: its stratum (GLOSSARY.md) and its
    document's short name, from the reader's templates. A record is in the What stratum and has none."""
    if not _is_passage(row):
        return {"stratum": "What", "short_name": None}
    if row.get("kind") == NOTICE_TEXT:  # a notice is a record, though search returns its text as a passage
        return {"stratum": "What", "short_name": "Notice"}
    template = template_for(str(row.get("document_type") or ""))
    return {"stratum": template.stratum if template else None, "short_name": template.short_name if template else None}


def _supported(pairs) -> list[dict]:
    return [{"text": mention.text, "evidence_id": found} for mention, found in pairs]


def answer_events(verdict: Verdict, facts: Facts, tools: Iterable[str] = ()) -> list[Event]:
    """The answer contract's events, in the spec's order: the kept sentences with their evidence ids,
    the evidence they cite, the check counts, then each removed sentence with its reasons."""
    events = []
    cited: dict[str, list[dict]] = {}
    for sentence in verdict.kept:
        claim = sentence.claim
        events.append(Event("sentence", {
            "index": sentence.index, "text": claim.sentence, "kind": claim.kind,
            "evidence_ids": list(claim.evidence_ids), "numbers": _supported(sentence.numbers),
            "dates": _supported(sentence.dates),
            "quote": None if claim.quote is None else {"text": claim.quote.text,
                                                       "evidence_id": claim.quote.evidence_id},
        }))
        for evidence in claim.evidence_ids:
            highlights = cited.setdefault(evidence, [])
            if claim.quote is not None and claim.quote.evidence_id == evidence and sentence.quote_span:
                highlights.append({"sentence": sentence.index, "start": sentence.quote_span[0],
                                   "end": sentence.quote_span[1]})
    for evidence, highlights in cited.items():
        row = facts.get(evidence)
        events.append(Event("evidence", {"id": evidence, "kind": "passage" if _is_passage(row) else "record",
                                         "tool": facts.tool(evidence), **labels(row), "row": _plain(row),
                                         "highlights": highlights}))
    events.append(Event("checks", {**verdict.counts(), "tools": sorted(set(tools))}))
    for sentence in verdict.removed:
        events.append(Event("removed", {
            "index": sentence.index, "sentence": sentence.claim.sentence, "reason": sentence.reasons[0].code,
            "reasons": [{"check": reason.check, "code": reason.code, "text": reason.text}
                        for reason in sentence.reasons]}))
    return events


def _plain(value):
    """A row as JSON can carry it: dates as ISO text and decimals as numbers."""
    if isinstance(value, Mapping):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, Decimal):
        try:
            return int(value) if value == value.to_integral_value() else float(value)
        except decimal.InvalidOperation:
            return str(value)
    return value
