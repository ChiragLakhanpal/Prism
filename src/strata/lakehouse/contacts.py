"""Contact details come out of every page before it is kept (CLAUDE.md rule 8).

Procurement notices name a contact person with their address, email, phone number and web
address, and their text often repeats them, along with bidders' emails and phone numbers. strip()
takes them out of a page before bronze keeps it, so no layer of the lakehouse ever holds them, and
counts what it took out:

- each contact field a record fills (contact_name, contact_email, contact_phone_no,
  contact_address and contact_web_url) is replaced by [contact removed];
- in a record's free text (notice_text and bid_description), each name, email and phone number
  from those fields is replaced wherever it appears, whatever its spacing or capitals;
- in the same free text, every other email address, also one typed with a stray space or a comma
  for a dot, and every phone number written with a country code (+254 20 1234567) or a trunk zero
  (046-1234567, 0722123456, 0 722-123456), is replaced too;
- every number written after a Tel, Phone, Mobile, Cell or Fax label, also one with a country code
  and no plus (Tel 254 20 1234567) or a second number after a slash, is replaced too.

Every other field stays as received. bid_reference_no is STEP's field and, when it holds a STEP
reference, the join from a notice to its package. A reference such as NWWDA-WSDP-03-2019-2020
stays as written. In the free text, fiscal years at the end of a reference (03-2019-2020) and a
P.O. Box with its postal code (05586-00100) are not phone numbers, and stay. The organization's
name and country stay too: they say who runs the procurement, not how to reach a person.
"""

from __future__ import annotations

import re

CONTACT_FIELDS = ("contact_name", "contact_email", "contact_phone_no", "contact_address", "contact_web_url")
SEARCHED = ("contact_name", "contact_email", "contact_phone_no")  # also taken out of the free text
FREE_TEXT = ("notice_text", "bid_description")  # the only fields searched; every other field stays as received
REMOVED = "[contact removed]"

# An email address, also when it is written untidily: one stray space after the "@" or inside the
# domain (name@ gmail.com, name@g mail.com), or a comma for a dot (name@gmail,com).
EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+@ ?[A-Za-z0-9-]+(?: [A-Za-z0-9-]+)?(?:[.,][A-Za-z0-9-]+)+")
# A number with a country code or a trunk zero, also with a space after the zero (0 722-123456),
# then any alternates written after it with a slash (0722123456 / 0733123456). A letter may come
# right before it, as scraped text runs words together.
PHONE = re.compile(r"(?<![\d+])(?:\(\s*\+?\s*\d{1,4}\s*\)|\+\s?\d{1,4}|\(?0 ?\d{1,4}\)?)(?:[ \t.–-]{0,3}\(?\d{1,5}\)?){1,6}"
                   r"(?:\s*/\s*\+?\d[\d \t–-]{4,}\d)*")
DATE_LIKE = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}")
AMOUNT_LIKE = re.compile(r"\d[\d,]*\.\d{1,2}")
FISCAL_YEARS = re.compile(r"\d{1,2}-(?:19|20)\d{2}-(?:19|20)\d{2}")  # a reference's end: 03-2019-2020
POSTAL_CODE = re.compile(r"\d{3,5}-\d{5}")  # a P.O. Box and its postal code: 05586-00100
# A number written after a phone label (Tel, Phone, Mobile, Cell, Fax, TEL/FAX), whatever its shape:
# a country code with no plus (Tel 254 20 1234567), or a second number after a slash
# (Tel: [contact removed]/722123456). Award notices write firms' and contacts' numbers this way.
NUMBER = r"(?:" + re.escape(REMOVED) + r"|[+(]?\d(?:[\d \t()–-]|\.(?=\d))*)"
LABELLED = re.compile(
    r"(?P<label>\b(?:tel(?:ephone)?|phone|mobile|cell|fax)\b(?:\s*/\s*fax\b)?\.?\s*(?:no\.?)?\s*[:.]?[ \t]*)"
    r"(?P<numbers>" + NUMBER + r"(?:[ \t]*[/,][ \t]*" + NUMBER + r")*)", re.I)
TRAILING = re.compile(r"[ \t()–-]*$")  # what a number's pattern takes after its last digit, kept as written


def _phone(candidate: str) -> bool:
    first = candidate.split("/")[0].strip()
    digits = re.sub(r"\D", "", first)
    if not 9 <= len(digits) <= 15 or digits.startswith("000"):
        return False
    return not any(pattern.fullmatch(first) for pattern in (DATE_LIKE, AMOUNT_LIKE, FISCAL_YEARS, POSTAL_CODE))


def _labelled_number(numbers: str) -> bool:
    """Seven digits or more, or any alternate left after a removed number (Tel: [contact removed] / 8,
    the last digit of a second line)."""
    digits = len(re.sub(r"\D", "", numbers.replace(REMOVED, "")))
    return digits >= 7 or (REMOVED in numbers and digits >= 1)


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
        text = self._sub(PHONE, text, _phone)
        return LABELLED.sub(self._labelled, text)

    def _labelled(self, match: re.Match) -> str:
        numbers = match.group("numbers")
        if not _labelled_number(numbers):
            return match.group(0)
        self.removed += 1
        return match.group("label") + REMOVED + TRAILING.search(numbers).group(0)


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
    """The page with its contact details replaced, and how many it replaced."""
    found, dropped = set(), 0
    for record in _records(body):
        for field in CONTACT_FIELDS:
            if _filled(record.get(field)):
                dropped += 1
                if field in SEARCHED:
                    found.add(str(record[field]))
    stripper = Stripper(sorted(found))

    def stripped(key, value):
        if key in CONTACT_FIELDS:
            return REMOVED if _filled(value) else value
        if key in FREE_TEXT and isinstance(value, str):
            return stripper.text(value)
        if isinstance(value, dict):
            return {name: stripped(name, item) for name, item in value.items()}
        if isinstance(value, list):
            return [stripped(None, item) for item in value]
        return value

    return stripped(None, body), dropped + stripper.removed


def _filled(value) -> bool:
    return bool(str(value or "").strip())


def removed_from(record: dict) -> bool:
    """Whether strip() replaced any contact detail in this record, in a contact field or its free text."""
    return (any(record.get(field) == REMOVED for field in CONTACT_FIELDS)
            or any(REMOVED in str(record.get(field) or "") for field in FREE_TEXT))
