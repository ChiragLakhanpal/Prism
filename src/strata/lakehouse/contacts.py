"""Contact names, emails and phone numbers come out of every page before it is kept (CLAUDE.md rule 8).

Procurement notices name a contact person with their email and phone number, and their text often
repeats them, along with bidders' emails and phone numbers. strip() takes them out of a page before
bronze keeps it, so no layer of the lakehouse ever holds them, and counts what it took out:

- each contact field a record fills (contact_name, contact_email, contact_phone_no,
  contact_address and contact_web_url) is dropped;
- each name, email and phone number from those fields is replaced wherever it appears in the page,
  whatever its spacing or capitals;
- every other email address, and every phone number written with a country code (+254 20 2724292)
  or a trunk zero (046-2103598, 0722437748), is replaced too.

The organization's name and country stay: they say who runs the procurement, not how to reach a
person. Dates, amounts, postal codes and reference numbers are not phone numbers, and stay.
"""

from __future__ import annotations

import re

CONTACT_FIELDS = ("contact_name", "contact_email", "contact_phone_no", "contact_address", "contact_web_url")
SEARCHED = ("contact_name", "contact_email", "contact_phone_no")  # also taken out of the page's text
REMOVED = "[contact removed]"

EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+")
# A number with a country code or a trunk zero, then any alternates written after it with a slash
# (0722473496 / 0724841525). A letter may come right before it, as scraped text runs words together.
PHONE = re.compile(r"(?<![\d+])(?:\(\s*\+?\s*\d{1,4}\s*\)|\+\s?\d{1,4}|\(?0\d{1,4}\)?)(?:[ \t.–-]{0,3}\(?\d{1,5}\)?){1,6}"
                   r"(?:\s*/\s*\+?\d[\d \t–-]{4,}\d)*")
DATE_LIKE = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}")
AMOUNT_LIKE = re.compile(r"\d[\d,]*\.\d{1,2}")


def _phone(candidate: str) -> bool:
    first = candidate.split("/")[0].strip()
    digits = re.sub(r"\D", "", first)
    if not 9 <= len(digits) <= 15 or digits.startswith("000"):
        return False
    return not (DATE_LIKE.fullmatch(first) or AMOUNT_LIKE.fullmatch(first))


DIGIT_RUN = re.compile(r"\+?\(?\d[\d \t().–-]{5,}\d")  # digits and the separators a phone number uses


def _digits(value: str) -> str | None:
    """A recorded value's digits, when the value is a phone number."""
    digits = re.sub(r"\D", "", value)
    return digits if len(digits) >= 7 and len(digits) >= len(re.sub(r"[\s+()./–-]", "", value)) else None


class Stripper:
    """Strips one page, counting what it removed. The page's own contact names are one pattern,
    longest first, matched whatever their spacing or capitals. Its phone numbers are matched by
    their digits, whatever their separators."""

    def __init__(self, values: list[str]):
        self.phones = {digits for digits in (_digits(value) for value in values) if digits}
        names = sorted((value.strip() for value in values if not _digits(value) and len(value.strip()) >= 4),
                       key=len, reverse=True)
        words = [r"\s+".join(re.escape(word) for word in name.split()) for name in names]
        self.patterns = [re.compile(r"\b(?:" + "|".join(words) + r")\b", re.I)] if words else []
        self.removed = 0

    def _known_phone(self, run: str) -> bool:
        digits = re.sub(r"\D", "", run)
        return any(phone in digits for phone in self.phones)

    def _sub(self, pattern: re.Pattern, text: str, check=None) -> str:
        def replace(match):
            if check and not check(match.group(0)):
                return match.group(0)
            self.removed += 1
            return REMOVED
        return pattern.sub(replace, text)

    def text(self, text: str) -> str:
        for pattern in self.patterns:
            text = self._sub(pattern, text)
        if self.phones:
            text = self._sub(DIGIT_RUN, text, self._known_phone)
        text = self._sub(EMAIL, text)
        return self._sub(PHONE, text, _phone)

    def value(self, value):
        if isinstance(value, str):
            return self.text(value)
        if isinstance(value, list):
            return [self.value(item) for item in value]
        if isinstance(value, dict):
            return {key: self.value(item) for key, item in value.items()}
        return value


def _records(value):
    """Every dict in a page that has a contact field."""
    if isinstance(value, dict):
        if any(field in value for field in CONTACT_FIELDS):
            yield value
        for item in value.values():
            yield from _records(item)
    elif isinstance(value, list):
        for item in value:
            yield from _records(item)


def strip(body: dict) -> tuple[dict, int]:
    """The page without contact details, and how many it removed."""
    found, dropped = set(), 0
    for record in _records(body):
        for field in CONTACT_FIELDS:
            if str(record.get(field) or "").strip():
                dropped += 1
                if field in SEARCHED:
                    found.add(str(record[field]))
    stripper = Stripper(sorted(found))

    def without_fields(value):
        if isinstance(value, dict):
            return {key: without_fields(item) for key, item in value.items() if key not in CONTACT_FIELDS}
        if isinstance(value, list):
            return [without_fields(item) for item in value]
        return value

    return stripper.value(without_fields(body)), dropped + stripper.removed
