"""The dashboard's words, from the copy file, and the one sentence builder that fills them (ticket 45).

copy.dash and copy.kpi in web/src/copy.ts are the dashboard's words; web/lint/server-copy.ts copies them into
copy.json beside this file, and the lint lane fails when that file is out of date, so the words have one home and
the copy lint checks every one. Three readers use them: the dashboard generator (titles, descriptions, text tiles),
the dashboard's queries (words a column shows, written into the query as text when the dashboard file is written),
and the nightly job, which fills the templates of "What the measures say" (strata.dashboard.findings).

The builder applies DESIGN.md section 7: one to nine in words and numerals from 10, with commas (rule 12), to every
count it fills, whatever its slot is called; a template with a count has a form for one and a form for more than one,
and say() picks it by the count it names; and a sentence never starts with a numeral or a lower-case word.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from importlib import resources

SLOT = re.compile(r"\{(\w+)\}")


@cache
def words() -> dict:
    """copy.dash and copy.kpi, with the words for one to nine, the months and the footer."""
    return json.loads((resources.files("strata.dashboard") / "copy.json").read_text())


def at(key: str):
    """A copy value by its dotted key, such as "dash.gov.page" or "kpi.weekly_users.name"."""
    value = words()
    for part in key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(f"The copy file has no dashboard words at {key}. Add them to web/src/copy.ts and run "
                           "node web/lint/server-copy.ts --write.")
        value = value[part]
    return value


class Unit(str):
    """A number with a unit or a fixed form, written as given: "12.5", "1,230.40", "October 22"."""


def count(number: int) -> str:
    """DESIGN.md section 7, rule 12: one to nine in words, numerals for 0 and from 10, with commas."""
    return words()["words"][number - 1] if 1 <= number <= 9 else f"{number:,}"


def numeral(number: int) -> str:
    """A count in a table or a counter: numerals with commas, always."""
    return f"{number:,}"


def money(amount) -> Unit:
    """US dollars in a sentence or a table: two decimals, with commas (the 45 brief, section 8.3)."""
    return Unit(f"{Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}")


def day(value: dt.date, today: dt.date) -> Unit:
    """A date in a sentence: "October 22" within the year of today, "October 22, 2025" otherwise (rule 13)."""
    month = words()["months"][value.month - 1]
    return Unit(f"{month} {value.day}" if value.year == today.year else f"{month} {value.day}, {value.year}")


def long_day(value: dt.date) -> Unit:
    """A date in a sentence with its year always: "November 10, 2026"."""
    return Unit(f"{words()['months'][value.month - 1]} {value.day}, {value.year}")


def table_day(value: dt.date) -> Unit:
    """A date in a table: "Oct 22, 2026" (rule 13)."""
    return Unit(f"{words()['months'][value.month - 1][:3]} {value.day}, {value.year}")


def month_name(value: dt.date) -> Unit:
    """A month in a sentence: "November 2026"."""
    return Unit(f"{words()['months'][value.month - 1]} {value.year}")


def short_month(value: dt.date) -> Unit:
    """A month in a table or a label: "Nov 2026"."""
    return Unit(f"{words()['months'][value.month - 1][:3]} {value.year}")


def _text(value, table: bool) -> str:
    if isinstance(value, bool):
        raise TypeError("A sentence slot takes a count, a Unit or text, not true or false.")
    if isinstance(value, int):
        return numeral(value) if table else count(value)
    return str(value)


def _capitalized(text: str) -> str:
    """Each sentence starts with a capital: "One is waiting" rather than "one is waiting"."""
    return re.sub(r"(^|[.:]\s+)([a-z])", lambda match: match.group(1) + match.group(2).upper(), text)


def fill(template: str, table: bool = False, **slots) -> str:
    """A template with each {slot} filled. A count is written by rule 12, or as a numeral in a table."""
    missing = [name for name in SLOT.findall(template) if name not in slots]
    if missing:
        raise KeyError(f"The template {template!r} needs {', '.join(missing)}.")
    text = SLOT.sub(lambda match: _text(slots[match.group(1)], table), template)
    return text if table else _capitalized(text)


def form(template, number: int):
    """The form of a template for one or for more than one, or the template itself when it has one form."""
    if isinstance(template, dict):
        return template["one" if number == 1 else "other"]
    return template


def say(key: str, by: str | None = None, table: bool = False, **slots) -> str:
    """The copy at key, in the form its count slot `by` needs, filled."""
    template = at(key)
    if isinstance(template, dict):
        if by is None:
            raise KeyError(f"{key} has a form for one and for more than one, so say which slot counts.")
        template = form(template, int(slots[by]))
    return fill(template, table, **slots)
