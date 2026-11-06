"""The verifier: it runs on every answer, before anyone sees it (CLAUDE.md rules 1 and 2).

The app ran every tool the agent asked for, so it holds every row and passage the answer may cite
(ADR 0003, the turn's Facts). Each claim is checked against them:

1. Every number and date the sentence states matches a value in a row the sentence cites, at the same
   rounding, or sits inside the words it quotes from a cited passage that is not a table summary. Each
   number is checked against the field that holds it. A number written with a unit (months, days, weeks or
   years, or a range ending in one, "3.3 to 7.9 months") never matches a value whose field names another unit
   or a count, so "45 months" is not the plan's 45 days, nor the 49 comparables a coverage line used; a value
   in days, months or weeks backs only a number written in its unit, so one comparable's 17 days never backs
   "17 of 25 comparable packages" (ticket 27's verify finding 1); and a number written with decimals never
   matches a whole number, so "8.0" is not an 8 (ticket 12's verify V1). Units are read in English sentences.
   A natural frequency ("8 in 10", "about 3 in 10", "fewer than 1 in 10") is one value, which only a frequency
   the record holds with the same words backs: a frequencies pair, a field named in10, or the q80 that "8 in
   10" names (ticket 12's review P3, ticket 28's verify F2); those back no other number. A
   table's summary passage is Prism's own words about the table, so a number it alone holds, quoted
   or not, is removed with a reason of its own (number_only_in_table_summary): the table's rows back
   numbers, its summary never does.
   The numbers and dates are read from the sentence itself, so one the agent left off its list is
   still checked. Every digit run is a number, as in "45-day", "US$1.2M" or "12,50,000" (grouped in lakhs),
   unless its token is an id (ID_SHAPES; a token that starts with FY, a quarter or a half is a period); so is a
   number written in words ("forty-five", "zero", or "one" unless it stands for a thing named before), and an
   amount no row holds as written ("half" or "doubled", but not "the middle half", which names a part of a past
   range). A passage backs only its
   dates, such as its report's date: its text is never a value, and its page, paragraph and version
   numbers say where it is, not what the report counted, so a number from a passage must be quoted.
2. Every id the sentence cites came back from a tool in this turn. A record, quote or advice sentence
   must cite at least one. So must a summary, unless a tool abstained this turn: a summary that cites nothing
   may only say what a tool could not answer ("That version of the plan was not yet public..."), and check 4
   judges it against those abstentions. Any other sentence that cites nothing is removed (no_source), since
   nothing could show it is true (ticket 24's verify F1).
3. Every quote is word for word on the cited page, ignoring only whitespace, line-end hyphenation,
   whether a quote mark is curly or straight, and a capital first letter where the page has a small one, as
   "[T]he" marks it in print ("The works contract estimates" from "...is that the works contract estimates",
   ticket 109), and starts and ends where the page's words and numbers do: "10" is not a quote from "108 of
   328", nor "334 km" from "2,334 km".
   The quote checked is the one the person reads: the words in the sentence's quote marks must be in
   the claim's quote, and that quote on its passage. Quote marks with no quote, or with words that are
   not on the page, fail; so does a quote the sentence never shows in quote marks. Words quoted from a
   cited record's text value, at any depth, such as a STEP description or the reason rebidding_risk quotes
   from a notice (quote.text), are on that record, with or without the claim's quote.

4. Each sentence follows from the sources it cites, judged in one batched call to the judge
   (src/strata/agent/judge.py) and skipped where checks 1 to 3 already prove it. A record or quote sentence
   is proven when it states at least one number, date or quote, every one of them matched, and every run
   of quoted words holds a word, not only a number or an identifier: 'Only "108" works contracts were
   signed' quotes a number that backs any meaning, and 'Another, "KE-ICTA-571738-CW-RFB", was still open'
   quotes a reference, so both go to the judge. Advice and summary sentences always go to the
   judge, which also says whether each sentence advises; one that does is held to check 5 whatever its kind.
   A summary that cites nothing goes with the turn's abstentions as its only sources (each named
   "<tool>:abstention", as the agent read it, with no date after the as-of date), so it follows only when it
   says no more than what a tool could not answer. A sentence the judge says does not follow is removed
   (not_supported, or beyond_abstention when it cites nothing, so the screen tells it apart from check 2's
   no_source, ticket 58). When the judge does not respond, every sentence it
   had to judge is removed (judge_unavailable), so none is shown unchecked.
5. A sentence of kind advice cites at least one lesson or comparable package: evidence from a tool whose
   registry entry says its rows back advice (config/tools.toml, backs_advice).
6. A sentence that rests on one side of a disagreement shows both sides. The stream asks get_disagreements
   about each project the standing sentences cite, as the viewer, and the disagreements whose side a kept
   sentence cites are attached to the first such sentence, with both sides, whether or not the agent's
   draft showed the other one. Their rows and sides join the turn's evidence, so each side's marker opens.
   When the stream cannot ask, every sentence citing that project's evidence is removed
   (disagreements_unavailable), since it could not be checked.

A sentence that fails is removed, with its reasons in this order: an id that did not come back first,
since nothing else about that sentence can be checked, then a quote that is not on its page or not in the
sentence, then numbers and dates, then checks 5, 6 and 4 in the order they run. Only sentences that pass
checks 1 to 3, 5 and 6 go to the judge. A number inside quoted words that are not on the page is counted
as unmatched but gets no reason of its own, because the quote's reason already explains it.
Each reason has a code, and the copy file (web/src/copy.ts, removed.reasons) has its sentence.
"""

from __future__ import annotations

import dataclasses
import datetime as dt
import decimal
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from strata import languages
from strata.agent.claims import Claim
from strata.agent.judge import ABSTENTION, Judgement, Question, Source
from strata.config import ENGLISH, load_project_page
from strata.harness.facts import Facts
from strata.harness.turn import Event
from strata.reader.passages import NOTICE_TEXT, TABLE_SUMMARY
from strata.reader.templates import template_for

CHECKS_RUN = (1, 2, 3)  # what verify() runs; AnswerCheck adds checks 4 to 6
ALL_CHECKS = (1, 2, 3, 4, 5, 6)  # what every answer and draft gets (ticket 24, src/strata/agent/answer_check.py)
# Reason codes. web/src/copy.ts holds one sentence for each, under removed.reasons.
NUMBER, DATE, NOT_RETURNED, NO_SOURCE, NOT_ON_PAGE, NOT_IN_SENTENCE, ONLY_IN_SUMMARY = (
    "number_not_in_records", "date_not_in_records", "id_not_returned", "no_source", "quote_not_on_page",
    "quote_not_in_sentence", "number_only_in_table_summary")
NOT_SUPPORTED, JUDGE_UNAVAILABLE, ADVICE_UNBACKED, DISAGREEMENTS_UNAVAILABLE = (
    "not_supported", "judge_unavailable", "advice_without_lesson_or_comparable", "disagreements_unavailable")
# Check 4's removal of a sentence that cites nothing and says more than what a tool could not answer (ticket 58).
BEYOND_ABSTENTION = "beyond_abstention"
REASONS = (NUMBER, DATE, NOT_RETURNED, NO_SOURCE, NOT_ON_PAGE, NOT_IN_SENTENCE, ONLY_IN_SUMMARY, NOT_SUPPORTED,
           JUDGE_UNAVAILABLE, ADVICE_UNBACKED, DISAGREEMENTS_UNAVAILABLE, BEYOND_ABSTENTION)
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
class Frequency:
    """A natural frequency a sentence states as one value, with the words before it: "8 in 10", "about 3 in 10",
    "fewer than 1 in 10" or "more than 9 in 10". Only a frequency a cited record holds backs it (frequency_backs)."""

    words: str | None  # "about", "fewer_than", "more_than", or None when the sentence writes none
    k: Decimal
    of: Decimal


@dataclass(frozen=True)
class Mention:
    kind: str  # "number" or "date"
    text: str
    value: Decimal | When | Frequency | str  # a str is an amount no row holds as written, such as "half"
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
    # MWI-WSDP-001. Q3-2020 and FY-2019 have two, so their numbers are read. A token that starts with FY, a
    # quarter (Q1 to Q4) or a half (H1 or H2) is a period, so its numbers are read, as in Q3-2020-21 or FY/2019/20.
    r"\b(?!(?:FY|Q[1-4]|H[12])[-/])[A-Z][A-Z0-9]*(?:-[A-Z0-9]+){2,}\b",
    # A bid or contract reference written with slashes, with three parts or more: KE/TAVEVO/82755/GO/RFQ or
    # KALRO/HQTS/053/23-24. It starts with a letter, so 2019/20 is two numbers.
    r"\b(?!(?:FY|Q[1-4]|H[12])[-/])[A-Z][A-Z0-9.]*(?:/[A-Z0-9.\-]+){2,}\b",
    r"\bCOVID-19\b",
    r"\b(?:[IVX]+|\d+)\.[A-Za-z]\b",  # a section label, III.B or 10.b
)
ID = re.compile("|".join(ID_SHAPES))
# Indian reports group digits in lakhs and crores, as in 12,50,000, which is one number.
DIGITS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d{1,2}(?:,\d{2})+,\d{3}(?:\.\d+)?|\d+(?:\.\d+)?")
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
VAGUE = {"half", "twice", "double", "triple", "hundreds", "thousands", "dozens", "doubled", "tripled", "halved",
         "quadrupled"}
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
# A natural frequency, as DESIGN.md section 7 writes a share: "8 in 10", "about 3 in 10", "fewer than 1 in 10" or "more
# than 9 in 10", in digits or in words. It is one value, not two numbers (ticket 12's review P3), so an 8 or a 10 held
# elsewhere in a record never backs it, and the record's frequencies back nothing else. "5 in 10 days" is not one.
FREQUENCY_WORDS = {"about": "about", "fewer than": "fewer_than", "more than": "more_than"}
FREQUENCY = re.compile(
    r"\b(?:(about|fewer than|more than)\s+)?(\d+|" + "|".join(word for word, value in SMALL.items() if value <= 10)
    + r")[\s-]+in[\s-]+(?:10|ten)\b(?![-\u2013]\d)(?!\s*-?\s*(?:months?|days?|weeks?|years?)\b)", re.I)


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


def _dates(language: str):
    """The date forms of a language: English's, or the registry's long forms for French, Spanish or Portuguese,
    with the ISO form every language may use."""
    if language == ENGLISH:
        return DATES
    iso = DATES[2]
    return (*((pattern, lambda m, read=read: When(*read(m))) for pattern, read in languages.dates(language)), iso)


def _digits(language: str) -> re.Pattern:
    return DIGITS if language == ENGLISH else languages.digits(language)


def _number(written: str, language: str) -> Decimal:
    return Decimal(written.replace(",", "")) if language == ENGLISH else languages.parse_number(written, language)


def _frequency(match: re.Match) -> Frequency:
    k = match[2].lower()
    return Frequency(FREQUENCY_WORDS[" ".join(match[1].lower().split())] if match[1] else None,
                     Decimal(k) if k.isdigit() else Decimal(SMALL[k]), Decimal(10))


def mentions(text: str, language: str = ENGLISH) -> list[Mention]:
    """The numbers and dates a text states, each with its place in the text, read in the text's language
    (config/languages.toml): "1 287 515,60" is one number in French and "22 juin 2026" one date. A four-digit
    number that could be a year is read as a year."""
    language = languages.language(language).code
    found: list[Mention] = []
    ids: list[tuple[int, int]] = []

    def free(start: int, end: int) -> bool:
        return all(end <= other.start or start >= other.end for other in found) and all(
            end <= id_start or start >= id_end for id_start, id_end in ids)

    for pattern, build in _dates(language):
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
    if language == ENGLISH:
        for match in FREQUENCY.finditer(text):
            if free(*match.span()):
                found.append(Mention("number", match.group(0), _frequency(match), *match.span()))
    words = _number_words(text) if language == ENGLISH else languages.number_words(text, language)
    for start, end, value in words:
        if free(start, end):
            found.append(Mention("number", text[start:end], value, start, end))
    for match in _digits(language).finditer(text):
        if not free(*match.span()):
            continue
        written = match.group(0)
        if written.isdigit() and len(written) == 4 and int(written) in YEARS:
            found.append(Mention("date", written, When(int(written)), *match.span()))
        else:
            found.append(Mention("number", written, _number(written, language), *match.span()))
    return sorted(found, key=lambda mention: mention.start)


def _declared(claim: Claim, stated: list[Mention], language: str = ENGLISH) -> list[Mention]:
    """The numbers and dates the claim lists but the sentence does not show: they are checked too, each as
    what its text reads as, whichever list it came in. The two numbers of a frequency the sentence states, listed
    alone ("8" and "10" for "8 in 10"), are that frequency."""
    extra: list[Mention] = []
    parts = {part for other in stated if isinstance(other.value, Frequency) for part in (other.value.k, other.value.of)}
    for text in claim.numbers + claim.dates:
        for mention in mentions(text, language):
            if mention.value not in parts and not any(mention.value == other.value for other in stated + extra):
                extra.append(Mention(mention.kind, mention.text, mention.value))
    return extra


# ── Values in a row ──────────────────────────────────────────────────────

NOT_VALUES = {"text", "header", "rank", "score", "public_from", "frequencies"}  # a passage's words, the search's own
# ranking, the day a record became public in Prism (ADR 0002), which says when a source could be read, not what it
# says, and the pairs a natural frequency states, which back only that frequency (frequency_backs)
ISO_DAY = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:[T ].*)?$")
PLAIN_NUMBER = re.compile(r"^-?\d+(?:\.\d+)?$")
IN10 = re.compile(r"(?:^|_)in10$")  # a field that gives a share as k in 10, such as a model's in10 or middle_in10


# The units a field name can give its values. A count is never a time, so "45 months" is not 45 signed packages, nor
# the 49 comparables a coverage line used; and a value in days, months or weeks backs only a number written with its
# unit, so one comparable's 17 days never backs "17 of 25 comparable packages" (ticket 27's verify finding 1). A year
# is left out of that rule, since a fiscal year is written with no unit after it.
UNIT_STEMS = ("month", "day", "week", "year", "count")
COUNT_WORDS = {"coverage", "matched", "used", "within", "total", "n", "m", "k"}
TIMES = ("month", "day", "week")
UNIT = r"(months?|days?|weeks?|years?)\b"
UNIT_AFTER = re.compile(r"\s*-?\s*" + UNIT, re.I)
RANGE_UNIT_AFTER = re.compile(r"\s*(?:-|\u2013|to|and)\s*" + DIGITS.pattern + r"\s*-?\s*" + UNIT, re.I)


def unit_of(sentence: str, mention: Mention) -> str | None:
    """The unit the sentence writes a number in, after it or after the range it starts: month, day, week or year."""
    if mention.end is None or not isinstance(mention.value, Decimal):
        return None
    after = sentence[mention.end:]
    found = UNIT_AFTER.match(after) or RANGE_UNIT_AFTER.match(after)
    return found.group(found.lastindex).lower().rstrip("s") if found else None


def _whole(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, Decimal):
        return value.as_tuple().exponent >= 0
    return isinstance(value, str) and value.strip().lstrip("-").isdigit()


def row_numbers(row: Any, path: tuple[str, ...] = ()) -> list[tuple[Decimal, tuple[str, ...], bool]]:
    """Each number a row holds as a value, with the field names on the way to it and whether it is whole."""
    if isinstance(row, Mapping):
        return [found for key, value in row.items() if key not in NOT_VALUES and not IN10.search(str(key))
                for found in row_numbers(value, (*path, str(key)))]
    if isinstance(row, list | tuple):
        return [found for value in row for found in row_numbers(value, path)]
    numbers, _ = row_values(row)
    return [(number, path, _whole(row)) for number in numbers]


def frequency_backs(row: Any) -> list[tuple[str, str | None, Decimal, Decimal]]:
    """The natural frequencies a record holds, at any depth, each as (kind, words, k, of): each pair under a field
    named frequencies, [8, 10] or {"words": "fewer_than", "states": [1, 10]} (find_comparables); each value of a field
    named in10, k in 10 (a model's share, or a step date's); and the 8 in 10 that a past range's or an estimate's q80
    names, the months by which 8 in 10 were signed."""
    found: list[tuple[str, str | None, Decimal, Decimal]] = []

    def number(value: Any) -> Decimal | None:
        if isinstance(value, bool) or not isinstance(value, int | float | Decimal):
            return None
        return Decimal(str(value))

    def walk(value: Any) -> None:
        if isinstance(value, list | tuple):
            for inner in value:
                walk(inner)
        if not isinstance(value, Mapping):
            return
        for key, inner in value.items():
            if key == "frequencies" and isinstance(inner, Mapping):
                for pair in inner.values():
                    words, states = (pair.get("words"), pair.get("states")) if isinstance(pair, Mapping) else (None, pair)
                    if isinstance(states, list | tuple) and len(states) == 2 and None not in map(number, states):
                        found.append(("pair", words, number(states[0]), number(states[1])))
            elif IN10.search(str(key)) and number(inner) is not None:
                found.append(("in10", None, number(inner), Decimal(10)))
            elif key == "q80" and number(inner) is not None:
                found.append(("q80", None, Decimal(8), Decimal(10)))
            elif key not in NOT_VALUES:
                walk(inner)

    walk(row)
    return found


def _frequency_backed(frequency: Frequency, backs: list) -> bool:
    """Whether a record's frequency backs the sentence's: the same k in 10, with the same words. "About" and no words
    are one ("about 3 in 10" and "3 in 10"); "fewer than" and "more than" must be the record's own. A q80 names only
    "8 in 10", with no words."""
    loose = (None, "about")
    for kind, words, k, of in backs:
        if (k, of) != (frequency.k, frequency.of):
            continue
        if kind == "q80" and frequency.words is None:
            return True
        if kind == "in10" and frequency.words in loose:
            return True
        if kind == "pair" and (frequency.words == words or (frequency.words in loose and words in loose)):
            return True
    return False


UNREAD = "unread"  # the unit of a number in a sentence whose units are not read: only English's are, so far


def _unit_conflict(path: tuple[str, ...], unit: str | None) -> bool:
    """Whether a value under these field names cannot back a number written in this unit (None: written with none;
    UNREAD: in a language whose units are not read, where no field conflicts)."""
    if unit == UNREAD:
        return False
    words = [word for name in path for word in re.split(r"[_\W\d]+", name.lower()) if word]
    if unit is None:
        return any(word.startswith(stem) for word in words for stem in TIMES)
    return any(word.startswith(stem) for word in words for stem in UNIT_STEMS if stem != unit) or any(
        word in COUNT_WORDS for word in words)


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


def _supports(mention: Mention, numbers: list, days: set, unit: str | None = None, frequencies: list = ()) -> bool:
    if isinstance(mention.value, Frequency):
        return _frequency_backed(mention.value, list(frequencies))
    if mention.kind == "number":
        decimals = isinstance(mention.value, Decimal) and "." in mention.text
        return any(value == mention.value and not _unit_conflict(path, unit) and not (decimals and whole)
                   for value, path, whole in numbers)
    return any(mention.value.covers(day) for day in days) or (
        mention.value.month is None and any(value == Decimal(mention.value.year) for value, _, _ in numbers))


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


def find_quote(quote: str, text: str, language: str = ENGLISH) -> tuple[int, int] | None:
    """Where the quote is in the text, word for word but for whitespace, line-end hyphenation and a capital first
    letter where the text has a small one: a quote that starts a sentence takes a capital, as "[T]he" marks it in
    print, so "The works contract estimates" is in "...is that the works contract estimates" (ticket 109), when the
    text never writes it with the capital. Every other letter keeps its case, so "108 OF 328 CASES" is not in "108 of
    328 cases". It must
    start and end where the text's words or numbers do, so "10" is not in "108 of 328", "ding" is not in
    "rebidding", "US$177" is not in "US$177.6" and "334 km" is not in "2,334 km". A number is read as
    mentions() reads one, so "45" is in "45-day" and "10" in "10-15", in the language of the text searched: "3" is not
    a quote from the French "3,5"."""
    found = find_quotes(quote, text, language)
    return found[0] if found else None


def find_quotes(quote: str, text: str, language: str = ENGLISH) -> list[tuple[int, int]]:
    """Every place the quote is in the text, word for word, as find_quote() finds the first."""
    wanted, _ = _normalized(quote)
    if not wanted:
        return []
    held, where = _normalized(text)
    numbers = [match.span() for match in _digits(languages.language(language).code).finditer(held)]
    # The quote as written, and, only when the text never writes it so, with its first letter small when it starts
    # with a capital (the "[T]he" convention). A quote the text holds as written keeps only those places, so a
    # rating quoted as "Low" is highlighted where the table writes Low, never at a "low" in the prose before it.
    forms = [wanted] + ([wanted[0].lower() + wanted[1:]] if wanted[0].isupper() else [])
    for form in forms:
        found = []
        start = held.find(form)
        while start >= 0:
            end = start + len(form)
            cut_at_start = form[0].isalnum() and start > 0 and held[start - 1].isalnum()
            cut_at_end = form[-1].isalnum() and end < len(held) and held[end].isalnum()
            inside_a_number = any(left < start < right or left < end < right for left, right in numbers)
            if not (cut_at_start or cut_at_end or inside_a_number):
                found.append((where[start], where[end - 1] + 1))
            start = held.find(form, start + 1)
        if found:
            return found
    return []


# An ISR's ratings table writes each row's previous rating, then its current one (ISR 7's section s4).
RATING_COLUMNS = re.compile(r"Previous\s+Rating\s+Current\s+Rating", re.I)
SHARED_WORD = re.compile(r"[^\W\d_]{3,}")


def highlight_of(quote: str, text: str, about: str, language: str = ENGLISH) -> tuple[int, int] | None:
    """Where to highlight a quote in its passage. When it occurs more than once, the match that follows the words the
    sentence (about) shares with the passage: the one with the most of those words between it and the match before
    it, the first on a tie. In an ISR's ratings table a row holds the previous rating, then the current one, with no
    words between them, and a sentence about the report's rating means its own, the Current Rating (ticket 24's
    critique rounds 2 and 3)."""
    found = find_quotes(quote, text, language)
    if len(found) < 2:
        return found[0] if found else None
    quoted = {word.lower() for word in SHARED_WORD.findall(quote)}
    shared = {word.lower() for word in SHARED_WORD.findall(about)} - quoted
    scores, previous = [], 0
    for start, end in found:
        scores.append(sum(1 for word in SHARED_WORD.findall(text[previous:start]) if word.lower() in shared))
        previous = end
    best = max(range(len(found)), key=lambda index: (scores[index], -index))
    same_row = best + 1 < len(found) and not re.search(r"[^\W\d_]", text[found[best][1]:found[best + 1][0]])
    return found[best + 1] if RATING_COLUMNS.search(text) and same_row else found[best]


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
    quoted_words: bool = False  # and every run of quoted words holds a word, not only a number
    judged: bool = False  # check 4 sent it to the judge
    proven: bool = False  # checks 1 to 3 proved it, so check 4 did not need the judge

    @property
    def kept(self) -> bool:
        return not self.reasons


@dataclass(frozen=True)
class Attached:
    """A disagreement check 6 shows under the first kept sentence that rests on it."""

    after: int  # the index of that sentence
    row: Mapping  # get_disagreements' row, with both sides
    changes_answer: bool  # a kept sentence states one side, so keeping the other side would change it
    by_verifier: bool  # the agent's draft left the other side out
    changes: tuple[int, ...] = ()  # the kept sentences that state one side only, which keeping the other would change


@dataclass(frozen=True)
class Verdict:
    sentences: tuple[Checked, ...]
    checks_run: tuple[int, ...] = CHECKS_RUN
    attached: tuple[Attached, ...] = ()
    judge_called: bool = False
    judge_responded: bool | None = None  # None when the judge was not called
    advice: tuple[int, int] = (0, 0)  # sentences that gave advice, and those that cited a lesson or comparable
    cited_tools: tuple[str, ...] = ()  # the tools whose evidence the kept sentences cite
    # The judged sentences on screen that cite a source written in another language than theirs (ticket 42): a model
    # judged them across two languages, a weaker kind of checking than an exact match, which the check line says.
    cross_language_judged: int = 0

    @property
    def kept(self) -> list[Checked]:
        return [sentence for sentence in self.sentences if sentence.kept]

    @property
    def removed(self) -> list[Checked]:
        return [sentence for sentence in self.sentences if not sentence.kept]

    def counts(self) -> dict:
        """The counts behind the check line and the steps' six-check list. numbers, dates, quotes and sources
        are over everything the agent wrote, removed sentences included, as the step log and the run log
        give them; shown is over the sentences on screen, as the check line gives them (the 24 brief).

        Ticket 58 adds three counts, each only when it is above 0, so an answer that cites a source in every
        sentence sends what it always sent (as cross_language does): sources.uncited, the sentences check 2 removed
        for citing nothing; shown.sources, when a sentence on screen cites nothing, with the sources the sentences
        on screen cite (total) and how many cite none (uncited); and judge.on_abstention, the sentences a model
        judged against what a tool could not answer, because they cite nothing."""
        numbers = [found for sentence in self.sentences for _, found in sentence.numbers]
        dates = [found for sentence in self.sentences for _, found in sentence.dates]
        quotes = [sentence for sentence in self.sentences if sentence.quoted]
        cited = {evidence: sentence for sentence in self.sentences for evidence in sentence.claim.evidence_ids}
        not_back = {reason.text for sentence in self.sentences for reason in sentence.reasons
                    if reason.code == NOT_RETURNED}
        counts = {
            "checks_run": list(self.checks_run),
            "sentences": {"written": len(self.sentences), "kept": len(self.kept), "removed": len(self.removed)},
            "numbers": {"total": len(numbers), "matched": sum(found is not None for found in numbers)},
            "dates": {"total": len(dates), "matched": sum(found is not None for found in dates)},
            "quotes": {"total": len(quotes), "found": sum(sentence.quote_found for sentence in quotes)},
            "sources": {"total": len(cited), "returned": len(set(cited) - not_back),
                        **_when_some("uncited", sum(any(reason.code == NO_SOURCE for reason in sentence.reasons)
                                                    for sentence in self.sentences))},
        }
        if 4 not in self.checks_run:
            return counts
        # Check 1's item in the steps counts numbers and dates together, so the screen adds nothing itself.
        counts["checked"] = {"total": len(numbers) + len(dates),
                             "matched": sum(found is not None for found in numbers + dates)}
        kept = self.kept
        shown_numbers = [found for sentence in kept for _, found in sentence.numbers]
        shown_dates = [found for sentence in kept for _, found in sentence.dates]
        shown_quotes = [sentence for sentence in kept if sentence.quoted]
        judged = [sentence for sentence in self.sentences if sentence.judged]
        unjudged = [sentence for sentence in judged if any(reason.code == JUDGE_UNAVAILABLE
                                                           for reason in sentence.reasons)]
        disputed = {sentence.index for sentence in kept for found in self.attached
                    if _rests_on(sentence, found.row)}
        uncited = [sentence for sentence in kept if not sentence.claim.evidence_ids]
        shown_sources = {"total": len({evidence for sentence in kept for evidence in sentence.claim.evidence_ids}),
                         "uncited": len(uncited)}
        return {**counts,
                "shown": {"numbers": {"total": len(shown_numbers), "matched": sum(f is not None for f in shown_numbers)},
                          "dates": {"total": len(shown_dates), "matched": sum(f is not None for f in shown_dates)},
                          "quotes": {"total": len(shown_quotes),
                                     "found": sum(sentence.quote_found for sentence in shown_quotes)},
                          "judged": sum(sentence.judged for sentence in kept),
                          "proven": sum(sentence.proven for sentence in kept),
                          # Only when some do, so an answer in one language sends what it always sent (ticket 42).
                          **({"cross_language": self.cross_language_judged} if self.cross_language_judged else {}),
                          **({"sources": shown_sources} if uncited else {})},
                "judge": {"called": self.judge_called, "responded": self.judge_responded, "judged": len(judged),
                          "followed": sum(sentence.kept for sentence in judged), "unjudged": len(unjudged),
                          "proven": sum(sentence.proven for sentence in self.sentences),
                          **_when_some("on_abstention", sum(not sentence.claim.evidence_ids for sentence in judged))},
                "advice": {"total": self.advice[0], "cited": self.advice[1]},
                "disagreements": {"disputed": len(disputed), "shown": len(self.attached),
                                  "attached": sum(found.by_verifier for found in self.attached),
                                  # the sentences removed because check 6 could not ask, which the screen says
                                  "unasked": sum(any(reason.code == DISAGREEMENTS_UNAVAILABLE for reason in sentence.reasons)
                                                 for sentence in self.sentences),
                                  # the sentences a warning card follows, which the screen announces
                                  "warned": len({found.after for found in self.attached if found.changes_answer})},
                "cited_tools": list(self.cited_tools)}


def _when_some(name: str, count: int) -> dict:
    """A count the check line needs only when it is above 0, so answers without it keep their recorded shape."""
    return {name: count} if count else {}


def _is_passage(row: Mapping | None) -> bool:
    return row is not None and "passage_id" in row and isinstance(row.get("text"), str)


def _summary(row: Mapping | None) -> bool:
    """Whether a cited row is a table's summary passage, which Prism wrote and which backs no number."""
    return _is_passage(row) and row.get("kind") == TABLE_SUMMARY


def _holds_number(row: Mapping, mention: Mention) -> bool:
    """Whether a passage's text writes the number the sentence states, read in the passage's own language."""
    return any(isinstance(found.value, Decimal) and found.value == mention.value
               for found in mentions(row["text"], _language_of(row)))


def _language_of(row: Mapping | None) -> str:
    """The language a passage is written in, as the passage record gives it; English for a record or an unknown one."""
    return str((row or {}).get("language") or ENGLISH)


def _values(row: Mapping | None) -> tuple[list, set, list]:
    """The numbers, dates and natural frequencies a cited row backs, each number with its field names. A passage
    backs its dates and no number."""
    _, days = row_values(row)
    return ([], days, []) if _is_passage(row) else (row_numbers(row), days, frequency_backs(row))


def _texts(row: Any) -> list[str]:
    """The text values a row holds at any depth, leaving out a passage's text, which is its page, and the search's
    header. A record's own text, such as the reason rebidding_risk quotes from a notice under quote.text, is one of
    its values (ticket 28's verify F1)."""
    if isinstance(row, Mapping):
        skipped = NOT_VALUES if _is_passage(row) else NOT_VALUES - {"text"}
        return [text for key, value in row.items() if key not in skipped for text in _texts(value)]
    if isinstance(row, list | tuple):
        return [text for value in row for text in _texts(value)]
    return [row] if isinstance(row, str) else []


IDENTIFIER_FIELD = re.compile(r"(?:^|_)(?:id|reference|reference_no|no|number)$")


def _identifiers(row: Any) -> set[str]:
    """The identifiers a cited row holds at any depth, such as a step_reference, a notice_id or a contract id."""
    if isinstance(row, list | tuple):
        return {name for value in row for name in _identifiers(value)}
    if not isinstance(row, Mapping):
        return set()
    found = {value.strip() for key, value in row.items() if isinstance(value, str) and IDENTIFIER_FIELD.search(str(key))}
    return found | {name for key, value in row.items() if key not in NOT_VALUES for name in _identifiers(value)}


def _names_only(run: str, identifiers: set[str]) -> bool:
    """Whether quoted words are only an identifier: a whole identifier of a cited row, or a token that reads as an id.
    Like a quote of only a number, it is on its record whatever the sentence around it says, so it proves nothing
    and the sentence goes to the judge (ticket 24's review round 3, follow-up 9)."""
    text = " ".join(run.split())
    return text in identifiers or ID.fullmatch(text) is not None


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


def check(index: int, claim: Claim, facts: Facts, language: str = ENGLISH) -> Checked:
    """Checks 1 to 3 on one claim, whose sentence is written in language (config/languages.toml): its numbers and
    dates are read in that language, and each quote is found in its passage's own words and language."""
    reasons: list[Reason] = []
    # Check 2: every cited id came back this turn.
    returned = [evidence for evidence in claim.evidence_ids if facts.came_back(evidence)]
    reasons += [Reason(2, NOT_RETURNED, evidence) for evidence in claim.evidence_ids if evidence not in returned]
    # A summary that cites nothing may only say what a tool could not answer this turn, so it stands for check 4
    # only when a tool abstained; any other sentence that cites nothing has nothing to be checked against.
    if not claim.evidence_ids and (claim.kind in MUST_CITE or not facts.abstentions()):
        reasons.append(Reason(2, NO_SOURCE))
    records = [(evidence, facts.get(evidence)) for evidence in returned if not _is_passage(facts.get(evidence))]
    # Check 3: the words in the sentence's quote marks are its quote, and its quote is on its page. Words
    # quoted from a cited record's text value, such as a STEP description, are on that record.
    quote, span, backs, found_quote = claim.quote, None, False, False
    if quote is not None:
        passage = facts.get(quote.evidence_id)
        if _is_passage(passage):
            span = find_quote(quote.text, passage["text"], _language_of(passage))
            found_quote = span is not None
            if found_quote:  # where the person reads it: the match the sentence means, when there are several
                span = highlight_of(quote.text, passage["text"], claim.sentence, _language_of(passage))
            backs = found_quote and not _summary(passage)
        elif passage is not None:  # a quote from a record's own text, which has no page to highlight
            backs = found_quote = any(find_quote(quote.text, text) for text in _texts(passage))
        if not found_quote and facts.came_back(quote.evidence_id):
            reasons.append(Reason(3, NOT_ON_PAGE, quote.evidence_id))
    spans = []  # each run of quoted words: where it is in the sentence, and the evidence id that holds it
    for start, end in quoted_spans(claim.sentence):
        words = claim.sentence[start:end]
        source = quote.evidence_id if quote is not None and found_quote and find_quote(
            words, quote.text, _language_of(facts.get(quote.evidence_id))) \
            else next((evidence for evidence, row in records if any(find_quote(words, text) for text in _texts(row))),
                      None)
        spans.append((start, end, source))
    if quote is None or found_quote:
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
    stated = [mention for mention in mentions(claim.sentence, language)
              if not _in_a_value(mention, claim.sentence, texts)]
    checked: dict[str, list] = {"number": [], "date": []}
    for mention in stated + _declared(claim, stated, language):
        unit = unit_of(claim.sentence, mention) if languages.language(language).code == ENGLISH else UNREAD
        found = next((evidence for evidence, (numbers, days, frequencies) in rows
                      if _supports(mention, numbers, days, unit, frequencies)), None)
        inside = next((source for start, end, source in spans
                       if mention.start is not None and start <= mention.start and mention.end <= end), False)
        if found is None and inside and (inside != getattr(quote, "evidence_id", None) or backs):
            found = inside
        checked[mention.kind].append((mention, found))
        # A number inside quoted words that are not on the page, or whose page did not come back, gets no
        # reason of its own: the quote's or the id's reason explains it. A number only a cited table
        # summary holds says so, since the summary is Prism's words, not the table's rows.
        if found is None and not (inside is None and explained):
            only_summary = mention.kind == "number" and any(
                _summary(facts.get(evidence)) and _holds_number(facts.get(evidence), mention)
                for evidence in returned)
            reasons.append(Reason(1, ONLY_IN_SUMMARY if only_summary else NUMBER if mention.kind == "number" else DATE,
                                  mention.text))
    quoted = bool(spans) or quote is not None
    # A quote counts as on its page only when its page was checked: a quote whose passage did not come
    # back this turn was compared with nothing, so the check line may not count it.
    on_page = quoted and not quote_reasons and (quote is None or found_quote)
    runs = [claim.sentence[start:end] for start, end, _ in spans] + ([quote.text] if quote is not None else [])
    names = {name for evidence in returned for name in _identifiers(facts.get(evidence))}
    words = bool(runs) and all(re.search(r"[^\W\d_]", run) and not _names_only(run, names) for run in runs)
    return Checked(index, claim, tuple(reasons), tuple(checked["number"]), tuple(checked["date"]), span,
                   quoted=quoted, quote_found=on_page, quoted_words=words)


def verify(claims: Iterable[Claim], facts: Facts, language: str = ENGLISH) -> Verdict:
    """Checks 1 to 3 on each claim, in the order the agent wrote them, in the language the answer was written in."""
    return Verdict(tuple(check(index, claim, facts, language) for index, claim in enumerate(claims)))


# ── Checks 4 to 6, on an answer ──────────────────────────────────────────

PROJECT = re.compile(r"^P\d{6}$")
DISAGREEMENTS_TOOL = "get_disagreements"


def proven(sentence: Checked) -> bool:
    """Whether checks 1 to 3 prove a kept sentence, so check 4 needs no judge: a record or quote sentence that
    states at least one number, date or quote, all of which matched, and whose quoted words are words."""
    return sentence.kept and _proves(sentence.claim.kind, bool(sentence.numbers or sentence.dates), sentence.quoted,
                                     sentence.quote_found, sentence.quoted_words)


def _proves(kind: str, states_a_value: bool, quoted: bool, quote_found: bool, quoted_words: bool) -> bool:
    if kind not in ("record", "quote"):
        return False
    return (states_a_value or quoted) and (not quoted or (quote_found and quoted_words))


def kept_counts(kept: Iterable[Mapping], removed: int, checks_run: Iterable[int],
                evidence: Mapping[str, Mapping] | None = None, language: str = ENGLISH) -> dict:
    """What some sentences of a saved draft add to the counts the screens show (Verdict.counts' sentences and shown),
    read back from the kept sentences' events, with how many of theirs were removed. A draft takes a row's counts away
    when its author updates or removes the row, and adds the rewrite's own in their place (ticket 39).

    Each kept sentence is read as counts() reads it: every number and date it states matched and its quote was found,
    or it would have been removed; proven by checks 1 to 3 as proven() says; otherwise judged, when check 4 ran; and
    judged across two languages when a source it cites (evidence, the draft's evidence by id) is written in another
    language than the draft."""
    kept = list(kept)
    run = set(checks_run)
    counts = {"sentences": {"written": len(kept) + removed, "kept": len(kept), "removed": removed}}
    if 4 not in run:
        return counts
    numbers = [mention for sentence in kept for mention in sentence.get("numbers") or ()]
    dates = [mention for sentence in kept for mention in sentence.get("dates") or ()]
    quoted = proven_count = judged = crossed = 0
    for sentence in kept:
        text, quote = sentence.get("text") or "", sentence.get("quote")
        runs = [text[start:end] for start, end in quoted_spans(text)] + ([quote["text"]] if quote else [])
        says_quote = bool(runs)
        quoted += says_quote
        names = {name for cited in sentence.get("evidence_ids") or ()
                 for name in _identifiers(((evidence or {}).get(cited) or {}).get("row"))}
        words = says_quote and all(re.search(r"[^\W\d_]", run) and not _names_only(run, names) for run in runs)
        if _proves(sentence.get("kind") or "", bool(sentence.get("numbers") or sentence.get("dates")), says_quote,
                   says_quote, words):
            proven_count += 1
            continue
        judged += 1
        crossed += any(_language_of(((evidence or {}).get(cited) or {}).get("row")) != language
                       for cited in sentence.get("evidence_ids") or ())
    shown = {"numbers": {"total": len(numbers), "matched": sum(m.get("evidence_id") is not None for m in numbers)},
             "dates": {"total": len(dates), "matched": sum(m.get("evidence_id") is not None for m in dates)},
             "quotes": {"total": quoted, "found": quoted}, "judged": judged, "proven": proven_count}
    if crossed:
        shown["cross_language"] = crossed
    return {**counts, "shown": shown}


def _sides(row: Mapping) -> list[str]:
    return [side["evidence_id"] for side in row.get("sides") or ()]


def _states(sentence: Checked, side: Mapping) -> bool:
    """Whether a sentence states a side's assertion, not only another value from the same passage or record: it
    cites the side's evidence, and it states the side's date or amount, writes its rating or judgment, or quotes
    words of the side's quote. So a sentence quoting ISR 7's overall risk rating does not rest on a disagreement
    about its rating of progress towards the PDO, though both cite the same section."""
    claim = sentence.claim
    if side.get("evidence_id") not in claim.evidence_ids:
        return False
    value, form = side.get("value"), side.get("value_form")
    if value is not None and form == "date":
        day = ISO_DAY.match(str(value))
        if day and any(isinstance(mention.value, When) and mention.value.covers(
                dt.date(int(day[1]), int(day[2]), int(day[3]))) for mention, _ in sentence.dates):
            return True
    elif value is not None and form == "amount":
        try:
            amount = Decimal(str(value))
        except decimal.InvalidOperation:
            amount = None
        if amount is not None and any(mention.value == amount for mention, _ in sentence.numbers):
            return True
    elif value and re.search(rf"(?<![\w-]){re.escape(str(value))}(?![\w-])", claim.sentence, re.I):
        return True
    quote = side.get("quote")
    said = [claim.quote.text] if claim.quote is not None else []
    said += [claim.sentence[start:end] for start, end in quoted_spans(claim.sentence)]
    return bool(quote) and any(find_quote(words, quote) or find_quote(quote, words) for words in said)


def _rests_on(sentence: Checked, row: Mapping) -> bool:
    """A sentence rests on a disagreement when it states one of its sides' assertions, or cites the disagreement
    itself."""
    return any(_states(sentence, side) for side in row.get("sides") or ()) or \
        row.get("evidence_id") in sentence.claim.evidence_ids


def _project(row: Mapping | None) -> str | None:
    if row is None:
        return None
    for value in (row.get("project_id"), (row.get("source") or {}).get("project_id")):
        if isinstance(value, str) and PROJECT.match(value):
            return value
    return None


def _abstention_text(tool: str, abstention: Mapping, limit: int) -> str:
    """What the judge reads of one abstention: the tool and what it said it could not answer."""
    return json.dumps(_plain({"tool": tool, "abstention": abstention}), ensure_ascii=False)[:limit]


def _source_text(row: Mapping | None, limit: int) -> str:
    """What the judge reads of one source, at most limit characters (config/thresholds.toml,
    verifier.judge_source_chars)."""
    if _is_passage(row):
        text = f"{row.get('header') or ''}\n{row['text']}".strip()
    else:
        text = json.dumps(_plain({key: value for key, value in (row or {}).items() if key != "also"}),
                          ensure_ascii=False)
    return text[:limit]


class AnswerCheck:
    """The six checks on one answer, in the order the stream runs them: checks 1 to 3 and 5 at once; then
    check 6, once the stream has asked get_disagreements about the projects() the standing sentences cite;
    then check 4, once the judge has answered the questions(). verdict() gives the result."""

    def __init__(self, claims: Iterable[Claim], facts: Facts, backs_advice: Iterable[str], *, source_chars: int,
                 checked: Iterable[Checked] | None = None, language: str = ENGLISH, facts_only: Iterable[int] = ()):
        """facts_only names the sentences, by index, whose question or recommendation is Prism's own, such as a
        research brief's bottom line and questions: check 4 judges only the facts inside them (ticket 155)."""
        self.facts, self.source_chars = facts, source_chars
        self.facts_only = frozenset(facts_only)
        # What the agent's tools could not answer, as checks 1 to 3 saw it: check 6's own question adds nothing here.
        self.abstentions = facts.abstentions()
        sentences = verify(claims, facts, language).sentences if checked is None else tuple(checked)
        self.language = language
        self.sentences = {sentence.index: sentence for sentence in sentences}
        # Every disagreement get_disagreements returned, by id: those the agent asked for, and those check 6 asks.
        self.disagreements: dict[str, Mapping] = {
            evidence: row for evidence, row in facts.returned_by(DISAGREEMENTS_TOOL) if row.get("sides")}
        self.fetched: set[str] = set()  # the ones only check 6's own question found
        self.judge_called, self.judge_responded = False, None
        self.backing = set(backs_advice)
        advice = [sentence for sentence in self.sentences.values() if sentence.claim.kind == "advice"]
        cited = [sentence for sentence in advice if self._backs_advice(sentence)]
        self.advice = (len(advice), len(cited))
        for sentence in advice:
            if sentence not in cited:
                self._fail(sentence.index, Reason(5, ADVICE_UNBACKED))

    def _backs_advice(self, sentence: Checked) -> bool:
        """Check 5: the sentence cites a lesson or a comparable, evidence from a tool whose rows back advice. Any tool
        that returned the id this turn counts, whichever came first (ticket 61's review, F4)."""
        return any(self.facts.came_back(evidence) and not self.backing.isdisjoint(self.facts.tools(evidence))
                   for evidence in sentence.claim.evidence_ids)

    @classmethod
    def from_checked(cls, checked: Iterable[Checked], facts: Facts, backs_advice: Iterable[str], *,
                     source_chars: int, facts_only: Iterable[int] = ()) -> AnswerCheck:
        """The six checks on sentences that checks 1 to 3 already saw, each against its own evidence, as a draft's
        notes are (src/strata/drafts/runtime.py): facts holds every row any of them may cite."""
        return cls((), facts, backs_advice, source_chars=source_chars, checked=checked, facts_only=facts_only)

    def _fail(self, index: int, reason: Reason) -> None:
        sentence = self.sentences[index]
        self.sentences[index] = dataclasses.replace(sentence, reasons=(*sentence.reasons, reason))

    def standing(self) -> list[Checked]:
        return [sentence for sentence in self.sentences.values() if sentence.kept]

    def projects(self) -> list[str]:
        """The projects whose disagreements check 6 needs: those of the evidence the standing sentences cite."""
        found = (_project(self.facts.get(evidence)) for sentence in self.standing()
                 for evidence in sentence.claim.evidence_ids)
        return list(dict.fromkeys(project for project in found if project))

    def disagreements_for(self, project: str, rows: list[Mapping] | None) -> None:
        """What get_disagreements returned about the project, or None when the stream could not ask: then every
        standing sentence citing the project's evidence fails check 6."""
        if rows is None:
            for sentence in self.standing():
                if any(_project(self.facts.get(evidence)) == project for evidence in sentence.claim.evidence_ids):
                    self._fail(sentence.index, Reason(6, DISAGREEMENTS_UNAVAILABLE, project))
            return
        for row in rows:
            if row["evidence_id"] not in self.disagreements:
                self.fetched.add(row["evidence_id"])
            self.disagreements[row["evidence_id"]] = row

    def resting(self) -> list[Mapping]:
        """The disagreements a standing sentence rests on, whose sides the answer's evidence must hold."""
        return [row for row in self.disagreements.values()
                if any(_rests_on(sentence, row) for sentence in self.standing())]

    def questions(self) -> list[Question]:
        """Check 4's questions: every standing sentence that checks 1 to 3 did not prove, each with the sources it
        cites, or, for a summary that cites nothing (which check 2 lets stand only when a tool abstained), with the
        turn's abstentions alone, so it follows only when it says no more than what a tool could not answer."""
        asked = []
        for sentence in self.standing():
            if proven(sentence):
                self.sentences[sentence.index] = dataclasses.replace(sentence, proven=True)
            elif sentence.claim.evidence_ids:
                asked.append(Question(sentence.index, sentence.claim.sentence, tuple(
                    Source(evidence, _source_text(self.facts.get(evidence), self.source_chars))
                    for evidence in sentence.claim.evidence_ids), facts_only=sentence.index in self.facts_only))
            else:
                asked.append(Question(sentence.index, sentence.claim.sentence, tuple(
                    Source(f"{tool}:{ABSTENTION}", _abstention_text(tool, abstention, self.source_chars))
                    for tool, abstention in self.abstentions)))
        return asked

    def judged(self, questions: list[Question], judgements: list[Judgement] | None) -> None:
        """The judge's answers to the questions, or None when it did not respond. A sentence that cites nothing
        and does not follow from what the tools could not answer is removed because it cited no source and said
        more than that (beyond_abstention); the
        judge's reason is kept with it for the run log. A sentence the judge says advises, though the agent gave it
        another kind, is held to check 5 as advice is (ticket 24's verify round 3, O1)."""
        self.judge_called, self.judge_responded = True, judgements is not None
        said = {judgement.index: judgement for judgement in judgements or []}
        total, cited = self.advice
        for question in questions:
            self.sentences[question.index] = dataclasses.replace(self.sentences[question.index], judged=True)
            sentence = self.sentences[question.index]
            if judgements is None:
                self._fail(question.index, Reason(4, JUDGE_UNAVAILABLE))
                continue
            judgement = said[question.index]
            if judgement.advises and sentence.claim.kind != "advice":
                total += 1
                if self._backs_advice(sentence):
                    cited += 1
                else:
                    self._fail(question.index, Reason(5, ADVICE_UNBACKED))
            if not judgement.follows:
                uncited = not sentence.claim.evidence_ids
                self._fail(question.index, Reason(4, BEYOND_ABSTENTION if uncited else NOT_SUPPORTED, judgement.reason))
        self.advice = (total, cited)

    def verdict(self) -> Verdict:
        sentences = tuple(self.sentences[index] for index in sorted(self.sentences))
        kept = [sentence for sentence in sentences if sentence.kept]
        attached = []
        earliest = sorted(self.disagreements.values(), key=lambda row: min(
            str(side.get("made_at") or "") for side in row.get("sides") or [{}]))
        for row in earliest:
            resting = [sentence for sentence in kept if _rests_on(sentence, row)]
            if not resting:
                continue
            sides = set(_sides(row))
            cited = {evidence for sentence in kept for evidence in sentence.claim.evidence_ids}
            both = sides <= cited or row["evidence_id"] in cited
            changed = tuple(sentence.index for sentence in resting if len(sides & set(sentence.claim.evidence_ids)) == 1)
            attached.append(Attached(resting[0].index, row, bool(changed), not both, changed))
        attached.sort(key=lambda found: found.after)  # stable, so a sentence's cards keep their date order
        tools = [self.facts.tool(evidence) for sentence in kept for evidence in sentence.claim.evidence_ids]
        cross = sum(1 for sentence in kept if sentence.judged and any(
            _language_of(self.facts.get(evidence)) != self.language for evidence in sentence.claim.evidence_ids))
        return Verdict(sentences, ALL_CHECKS, tuple(attached), self.judge_called, self.judge_responded, self.advice,
                       cited_tools=tuple(sorted({tool for tool in tools if tool})), cross_language_judged=cross)


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


def sentence_of(text: str | None, quote: str | None) -> str | None:
    """The whole sentence of a passage that holds a side's quote, without the paragraph's own number, so the card
    shows what the report said in full: the ICR's paragraph 78 says more than the words the reader quoted. None when
    the passage has no such sentence. The answer's card (disagreement_event) and the timeline's drawer (ticket 23)
    both show it."""
    if not text or not quote:
        return None
    wanted = " ".join(quote.split())
    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", " ".join(text.split())):
        if wanted in sentence:
            return re.sub(r"^\d+\.\s+", "", sentence)
    return None


# The kind of report each documents API type is (config/project_page.toml's groups), read once.
DOCUMENT_GROUPS = load_project_page().document_groups


def _side(side: Mapping, leaned: str | None) -> dict:
    document_type = side.get("document_type")
    kind = DOCUMENT_GROUPS.get(document_type, "other") if document_type else "record"
    return {"evidence_id": side["evidence_id"], "assertion_id": side.get("assertion_id"), "type": kind,
            "document_type": document_type, "report_number": side.get("report_number"),
            "sequence": side.get("sequence"), "paragraph": side.get("paragraph"),
            "paragraph_numbered": side.get("paragraph_numbered"), "evidence_tier": side.get("evidence_tier"),
            "made_at": side.get("made_at"), "field_name": side.get("field_name"), "value": side.get("value"),
            "value_form": side.get("value_form"), "quote": side.get("quote"),
            "months_after_event": side.get("months_after_event"), "doc_key": side.get("doc_key"),
            "sentence": sentence_of(side.get("text"), side.get("quote")),
            "leaned": side.get("assertion_id") == leaned}


def disagreement_event(found: Attached) -> Event:
    """A disagreement check 6 shows under the sentence it concerns, with both sides in the order they were
    written, the side Prism leans on, the evidence ladder's rule and what you would treat as true if you kept
    the other side. The screen writes every sentence of it from these values and the copy file.

    One shape carries what both cards read (tickets 23 and 24): after, the sentence the card follows;
    changes_answer, whether keeping the other side would change a sentence (the warning state); and
    changes_sentence_ids, which sentences those are, and changes_count, how many, which the card says as it comes
    (CLAUDE.md rule 1: the browser counts nothing). disagreement_id is the id
    keeping a side posts to (POST /api/disagreements/ID/choices), with each side's assertion_id."""
    row = found.row
    leaned = row.get("lean_assertion_id")
    return Event("disagreement", {
        "id": row["evidence_id"], "disagreement_id": row.get("disagreement_id"), "after": found.after,
        "changes_answer": found.changes_answer, "changes_sentence_ids": list(found.changes),
        "changes_count": len(found.changes),
        "attached_by_verifier": found.by_verifier, "attribute": row.get("attribute"), "rule_id": row.get("rule_id"),
        "period_event": (row.get("period") or {}).get("event"),
        "sides": [_side(side, leaned) for side in row.get("sides") or ()],
        "if_you_keep": _plain(row.get("if_you_keep"))})


def answer_events(verdict: Verdict, facts: Facts, tools: Iterable[str] = (), cited_only: Iterable[str] = ()) -> list[Event]:
    """The answer contract's events, in the spec's order: the kept sentences with their evidence ids,
    the evidence they cite, the disagreements check 6 shows, the check counts, then each removed sentence
    with its reasons. tools are the tools that ran, and cited_only those whose "Not checked" clause applies only
    once a sentence on screen cites them (config/tools.toml, not_checked_when), for the check line."""
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
    for found in verdict.attached:  # each side of a disagreement opens like any source
        for side in found.row.get("sides") or ():
            evidence = side["evidence_id"]
            if not facts.came_back(evidence):
                continue
            highlights = cited.setdefault(evidence, [])
            # The side's quote, or the rating a side gives with no quote, highlighted for the marker under the
            # sentence the card follows, so its evidence card and the drawer open on the words the card shows,
            # whether or not a sentence quoted them: in a ratings table, the rating on its row (highlight_of).
            row = facts.get(evidence)
            words = side.get("quote") or (str(side["value"]) if side.get("value_form") == "rating" and side.get("value")
                                          else None)
            span = highlight_of(words, row["text"], side.get("field_name") or "", _language_of(row)) \
                if words and _is_passage(row) else None
            mark = None if span is None else {"sentence": found.after, "start": span[0], "end": span[1]}
            if mark is not None and mark not in highlights:
                highlights.append(mark)
    for evidence, highlights in cited.items():
        row = facts.get(evidence)
        events.append(Event("evidence", {"id": evidence, "kind": "passage" if _is_passage(row) else "record",
                                         "tool": facts.tool(evidence), **labels(row), "row": _plain(row),
                                         "highlights": highlights}))
    events += [disagreement_event(found) for found in verdict.attached]
    checks = {**verdict.counts(), "tools": sorted(set(tools))}
    if 4 in verdict.checks_run:
        checks["cited_only"] = sorted(set(cited_only))
    events.append(Event("checks", checks))
    for sentence in verdict.removed:
        events.append(Event("removed", {
            "index": sentence.index, "sentence": sentence.claim.sentence, "kind": sentence.claim.kind,
            "reason": sentence.reasons[0].code,
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
