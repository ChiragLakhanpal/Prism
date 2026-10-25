"""Numbers, dates and number words in each working language, read and written from one registry entry
(config/languages.toml; CLAUDE.md rule 4; ticket 42).

The verifier reads a sentence's numbers and dates in the language the sentence was written in, and the server
writes values for a writer in the same form, so what the writer was given and what the verifier reads back can
never drift apart. English stays as the verifier has always read it (src/strata/agent/verifier.py); this module
serves French, Spanish and Portuguese:

- digits(code): the pattern of a number as the language writes it: "1 287 515,60" in French (a narrow no-break
  space, a no-break space or a space between groups, and a decimal comma), "1.287.515,60" in Spanish and
  Portuguese. parse_number() gives its value, and format_number() writes a value that way.
- dates(code): the long date forms, "22 juin 2026", "1er juin 2026", "juin 2026", "22 de junio de 2026", each as a
  pattern and a function from its match to (year, month, day). format_date() writes the day form.
- number_words(text, code): each number written in words, where it is and its value: "trois", "vingt et un",
  "quatre-vingt-dix", "cuarenta y cinco", "dois mil". The words for one are left out, since they are also the
  language's article ("un marché", "una obra", "um contrato").

No translation happens here: a value keeps the tool's digits and rounding; only its marks change.
"""

from __future__ import annotations

import datetime as dt
import re
from collections.abc import Callable
from decimal import Decimal
from functools import cache

from strata.config import ENGLISH, Language, load_languages


@cache
def registry():
    return load_languages()


def language(code: str | None) -> Language:
    """The registry's entry for a working language; English for None or a language Strata does not write in."""
    found = registry().get(code or ENGLISH)
    return found if found is not None and found.working else registry().get(ENGLISH)


def _class(marks) -> str:
    return "[" + "".join(re.escape(mark) for mark in marks) + "]"


@cache
def digits(code: str) -> re.Pattern:
    """A number as the language writes it: grouped digits with an optional decimal part, or plain digits."""
    entry = language(code)
    group, decimal = _class((entry.group, *entry.group_also)), re.escape(entry.decimal)
    return re.compile(rf"\d{{1,3}}(?:{group}\d{{3}})+(?:{decimal}\d+)?(?!\d)|\d+(?:{decimal}\d+)?")


def parse_number(text: str, code: str) -> Decimal:
    """The value of a number written as the language writes it: "1 287 515,60" is 1287515.60 in French."""
    entry = language(code)
    plain = text
    for mark in (entry.group, *entry.group_also):
        plain = plain.replace(mark, "")
    return Decimal(plain.replace(entry.decimal, "."))


def format_number(value: Decimal | int | float, code: str, places: int | None = None) -> str:
    """A value written as the language writes it, at the given decimal places or as the value has them."""
    entry = language(code)
    number = Decimal(str(value))
    if places is not None:
        number = number.quantize(Decimal(1).scaleb(-places))
    sign, whole, _, fraction = re.match(r"(-?)(\d+)(\.(\d+))?$", format(number, "f")).groups()
    grouped = f"{int(whole):,}".replace(",", entry.group)
    return f"{sign}{grouped}{entry.decimal + fraction if fraction else ''}"


def _month_pattern(entry: Language) -> str:
    return "|".join(re.escape(month) for month in entry.months)


@cache
def dates(code: str) -> tuple[tuple[re.Pattern, Callable[[re.Match], tuple[int, int, int | None]]], ...]:
    """The long date forms of a language, each with how to read its match as (year, month, day or None)."""
    entry = language(code)
    months = {month.lower(): number for number, month in enumerate(entry.months, 1)}
    joiner = rf"\s+{re.escape(entry.date_joiner)}" if entry.date_joiner else ""
    month = _month_pattern(entry)
    day_form = re.compile(rf"\b(\d{{1,2}})(?:er|º|°|o)?{joiner}\s+({month}){joiner}\s+(\d{{4}})\b", re.IGNORECASE)
    month_form = re.compile(rf"\b({month}){joiner}\s+(\d{{4}})\b", re.IGNORECASE)
    return ((day_form, lambda m: (int(m[3]), months[m[2].lower()], int(m[1]))),
            (month_form, lambda m: (int(m[2]), months[m[1].lower()], None)))


def format_date(day: dt.date, code: str) -> str:
    """A day in the language's long form: "22 juin 2026", "22 de junio de 2026"."""
    entry = language(code)
    joiner = f" {entry.date_joiner}" if entry.date_joiner else ""
    if code == ENGLISH or entry.code == ENGLISH:
        return f"{entry.months[day.month - 1]} {day.day}, {day.year}"
    return f"{day.day}{joiner} {entry.months[day.month - 1]}{joiner} {day.year}"


WORD = re.compile(r"[^\W\d_]+")


def number_words(text: str, code: str) -> list[tuple[int, int, Decimal]]:
    """Each number written in words, with where it starts and ends and its value. Words joined by a space, a
    hyphen or the language's joiner make one number: "vingt et un" (21), "quatre-vingt-dix" (90)."""
    entry = language(code)
    small, scales, times = dict(entry.number_words), dict(entry.scale_words), dict(entry.times_words)
    ones, joiners = dict(entry.joined_ones), set(entry.joiners)
    tokens = list(WORD.finditer(text))
    lower = [token.group(0).lower() for token in tokens]

    def gap(i: int) -> str:
        return text[tokens[i].end():tokens[i + 1].start()]

    def numeric(word: str) -> bool:
        return word in small or word in scales

    def worth(word: str) -> int:
        return small.get(word) or scales.get(word) or ones.get(word) or 0

    def joins(before: str, after: str) -> bool:
        """A joiner joins a tens word or a larger one to a smaller number, as in "vingt et un" or "dois mil e
        vinte", and never two counts, as in "trois et quatre marchés"."""
        return worth(before) >= 20 and worth(after) < worth(before)

    found, i = [], 0
    while i < len(tokens):
        if not numeric(lower[i]):
            i += 1
            continue
        j = i
        while j + 1 < len(tokens):
            if gap(j) in (" ", "-") and numeric(lower[j + 1]):
                j += 1
            elif (gap(j) in (" ", "-") and lower[j + 1] in joiners and j + 2 < len(tokens)
                  and gap(j + 1) in (" ", "-") and (numeric(lower[j + 2]) or lower[j + 2] in ones)
                  and joins(lower[j], lower[j + 2])):
                j += 2
            else:
                break
        found.append((tokens[i].start(), tokens[j].end(), _value(lower[i:j + 1], {**ones, **small}, scales, times)))
        i = j + 1
    return found


def _value(words: list[str], small: dict, scales: dict, times: dict) -> Decimal:
    total = current = 0
    for word in words:
        if word in times and 0 < current < times[word]:
            current *= times[word]
        elif word in small:
            current += small[word]
        elif word in scales:
            if scales[word] >= 1000:
                total, current = total + (current or 1) * scales[word], 0
            else:
                current = (current or 1) * scales[word]
    return Decimal(total + current)
