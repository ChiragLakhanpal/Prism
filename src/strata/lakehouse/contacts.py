"""Contact details come out of every page before it is kept (CLAUDE.md rule 8).

A document's text and its pages go through strip_text() before bronze keeps them, which takes out
its email addresses and the numbers written after a phone label. The rest of this docstring is about
notices.

Procurement notices name a contact person with their address, email, phone number and web
address, and their text often repeats them, along with bidders' emails and phone numbers. strip()
takes them out of a page before bronze keeps it, so no layer of the lakehouse ever holds them, and
counts what it took out:

- each contact field a record fills (contact_name, contact_email, contact_phone_no,
  contact_address and contact_web_url) is replaced by [contact removed];
- in a record's free text (notice_text and bid_description), each name, email and phone number
  from those fields is replaced wherever it appears, whatever its spacing or capitals;
- in the same free text, every other email address, also one typed with stray spaces (JDOE @
  EXAMPLE.COM) or a comma for a dot, run into the next with no space, or spelled out (jdoe [at]
  example [dot] com, jdoe(at)example.com), and every phone number written with a country code
  (+254 20 1234567) or a trunk zero (046-1234567, 0722123456, 0 722-123456), with the last digit
  of a second line written after it (0722 123 456/7), is replaced too;
- every number written after a phone label (Tel, Telephone, Telefax, Phone, Cellphone, Mobile, Mob,
  Cell, Fax, also followed by No., Number or #, or by /Fax or /WhatsApp), also one with a country
  code and no plus (Tel 254 20 1234567) or a second number after a slash, a comma or "or", is
  replaced too, and so is a number of nine digits or more after Ph, M, Contact or WhatsApp
  (Ph: 98123 45678, Contact: 254 722 123456);
- a person's name after "Attention" and a title (ATTENTION: Mr. Francis Kombe) is replaced, with
  the label kept; a job title after Attention (Attention: Chief Executive Officer) stays;
- last, whatever the nightly job's check would still find (LEFTOVERS below: an email address, a
  labelled phone number, a name after "Attention" and a title) is replaced, with the label kept
  (Fax:: [contact removed]), so the check never finds what this leaves.

Silver runs the same removal again on each notices page it reads (strip_again), and the last pass
once more on the plain text it keeps (strip_left), so a fix here reaches the pages bronze already
holds when silver reads them again (ticket 76). Silver reads a page again when the nightly check
finds one of LEFTOVERS in its notices (ticket 121), so a rule added there reaches every page that
needs it on the next run. Each of the removal's other rules is named in NOT_CHECKED, with the
reason the check does not look for it.

Every other field stays as received. bid_reference_no is STEP's field and, when it holds a STEP
reference, the join from a notice to its package. A reference such as NWWDA-WSDP-03-2019-2020
stays as written. In the free text, fiscal years at the end of a reference (03-2019-2020) and a
P.O. Box with its postal code (05586-00100) are not phone numbers, and stay. The organization's
name and country stay too: they say who runs the procurement, not how to reach a person.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

CONTACT_FIELDS = ("contact_name", "contact_email", "contact_phone_no", "contact_address", "contact_web_url")
# What strip() counts, by kind (ticket 45): the dashboard's Governance page shows names, emails and phones. Addresses
# and web addresses come out of their contact fields only, and are counted under their own kinds.
KINDS = ("names", "emails", "phones", "addresses", "web_addresses")
FIELD_KINDS = dict(zip(CONTACT_FIELDS, ("names", "emails", "phones", "addresses", "web_addresses")))
ANY = "any"  # every kind together: how many details a page lost, and from how many of its records
SEARCHED = ("contact_name", "contact_email", "contact_phone_no")  # also taken out of the free text
FREE_TEXT = ("notice_text", "bid_description")  # the only fields searched; every other field stays as received
REMOVED = "[contact removed]"

# An email address, also when it is written untidily: one stray space after the "@" or inside the
# domain (name@ gmail.com, name@g mail.com), or a comma for a dot (name@gmail,com).
# A space may come before the "@" too (JDOE @ EXAMPLE.COM), but then the address must end in a dot
# and two letters or more, so a rate written with "@" (Interest @ 12.5% per year, rate @ KES 1,000,000)
# stays. A firm's name that writes "@" for "&" (ECONOMIC @ TECHNICAL COOPERATIVE CO.) has no dot inside
# a word, so it stays too.
EMAIL = re.compile(r"[A-Za-z0-9._%+'-]+(?:@ ?[A-Za-z0-9-]+(?: [A-Za-z0-9-]+)?(?:[.,][A-Za-z0-9-]+)+"
                   r"| @ ?[A-Za-z0-9-]+(?:[.,][A-Za-z0-9-]+)*[.][A-Za-z]{2,}(?![A-Za-z0-9]))")
# An address spelled out to get past a scan: jdoe [at] example [dot] com, jdoe(at)example.com.
EMAIL_SPELLED_OUT = re.compile(
    r"[A-Za-z0-9._%+'-]+\s*[\[(]\s*at\s*[\])]\s*[A-Za-z0-9-]+(?:(?:\s*[\[(]\s*dot\s*[\])]\s*|\.)[A-Za-z0-9-]+)+",
    re.I)
# What is left of a second address run into the first with no space (a@x.com.b@y.com): its domain.
AFTER_EMAIL = re.compile(re.escape(REMOVED) + r"@ ?[A-Za-z0-9-]+(?:[.,][A-Za-z0-9-]+)+")
# A number with a country code or a trunk zero, also with a space after the zero (0 722-123456),
# then any alternates written after it with a slash (0722123456 / 0733123456). A letter may come
# right before it, as scraped text runs words together, and so may another number's last digit
# when the plus starts this one (+254 712 345 678+254 20 123 4567).
PHONE = re.compile(r"(?:(?<![\d+])|(?<=\d)(?=\+))(?:\(\s*\+?\s*\d{1,4}\s*\)|\+\s?\d{1,4}|\(?0 ?\d{1,4}\)?)(?:[ \t.–-]{0,3}\(?\d{1,5}\)?){1,6}"
                   r"(?:\s*/\s*\+?\d[\d \t–-]{4,}\d)*")
# The last digit or two of another line, written after a removed number: [contact removed]/7.
LINE_ENDING = re.compile(re.escape(REMOVED) + r"(?:[ \t]*/[ \t]*\d{1,2}(?![\d/]))+")
DATE_LIKE = re.compile(r"\d{1,4}[./-]\d{1,2}[./-]\d{1,4}")
AMOUNT_LIKE = re.compile(r"\d[\d,]*\.\d{1,2}")
FISCAL_YEARS = re.compile(r"\d{1,2}-(?:19|20)\d{2}-(?:19|20)\d{2}")  # a reference's end: 03-2019-2020
POSTAL_CODE = re.compile(r"\d{3,5}-\d{5}")  # a P.O. Box and its postal code: 05586-00100
# A number written after a phone label (Tel, Telephone Number, Tel #, Telefax, TEL/FAX, Phone,
# Cellphone, Mobile/WhatsApp, Mob. No., Cell, Fax), whatever its shape: a country code with no plus
# (Tel 254 20 1234567), or a second number after a slash (Tel: [contact removed]/722123456). Award
# notices write firms' and contacts' numbers this way. A second number may also follow a comma or "or".
NUMBER = r"(?:" + re.escape(REMOVED) + r"|[+(]?\d(?:[\d \t()–-]|\.(?=\d))*)"
NUMBERS = r"(?P<numbers>" + NUMBER + r"(?:[ \t]*(?:[/,]|\bor\b)[ \t]*" + NUMBER + r")*)"
LABELLED = re.compile(
    r"(?P<label>\b(?:tel(?:ephone|efax)?|(?:cell|mobile)?\s?phone|mobile|mob|cell|fax)\b"
    r"(?:\s*/\s*(?:fax|mobile|whats\s?app)\b)?\.?\s*(?:no\.?|number|#)?\s*[:.]?[ \t]*)" + NUMBERS, re.I)
# A number after a short label: Ph, M, Contact or WhatsApp, with a colon or No. after it, and any
# second number after a slash, a comma or "or". These words may also come before other numbers
# (pH 6.5 to 8.5, M: 12 units), so the numbers need nine digits or more, as a phone number with
# its area or mobile code has: 722 123 456, 254 20 1234567, 98123 45678.
SHORT_LABELLED = re.compile(
    r"(?P<label>\b(?:ph|m|contact|whats\s?app)\b\.?(?:\s*(?:no\.?|number)\s*:?|\s*:)[ \t]*)" + NUMBERS, re.I)
SHORT_LABEL_DIGITS = 9
# A person's name after "Attention" and a title: ATTENTION: Mr. Francis Kombe, Attention: Mrs. Jane A. Roe.
# The name is up to four words that each start with a capital letter. A job title after Attention has no
# title before it (Attention: Chief Executive Officer), so it stays, and so does "Attention is drawn".
ATTENTION = re.compile(
    r"(?P<label>\b(?i:attention)\b[ \t]*:?[ \t]*)"
    r"(?P<name>(?i:mr|mrs|ms|miss|dr|eng|prof)\b\.?(?:[ \t]+[A-Z][A-Za-z'’-]*\.?){1,4})")
TRAILING = re.compile(r"[ \t()–-]*$")  # what a number's pattern takes after its last digit, kept as written
DIGIT_RUN = re.compile(r"\+?\(?\d[\d \t().–-]{5,}\d")  # digits and the separators a phone number uses


@dataclass(frozen=True)
class Leftover:
    """What one of the removal's rules takes out, as the nightly check looks for it in a notice's text.

    The check (strata.lakehouse.quality, contacts_left) counts the notices a leftover's pattern finds, silver reads
    again the pages those notices came from (strata.lakehouse.silver.notices, read_again), and the removal's last
    pass (Stripper.left) takes out all the pattern finds, so the check never finds what the removal leaves.

    key      the leftover's name; the check binds its pattern as the parameter :left_<key>
    kind     what the removal counts it under (KINDS)
    rule     the removal's own rule (a pattern in this module) whose matches the pattern finds
    pattern  the pattern, simpler than its rule, so that the SQL warehouse (Java's regular expressions), DuckDB (RE2)
             and Python read it alike: no lookaround and no named group. Its first group, when it has one, is the
             label written before the detail, which the removal keeps. The check binds it as a parameter, since
             Spark SQL mangles the backslashes of a literal.
    """

    key: str
    kind: str
    rule: re.Pattern
    pattern: str

    @property
    def parameter(self) -> str:
        return f"left_{self.key}"


# One definition of a contact detail left in a notice (CLAUDE.md rule 4; tickets 76 and 121): every rule of the
# removal's last pass. A rule the removal gains goes here with its pattern, and the nightly check counts what the
# pattern finds, silver reads those notices' pages again, and the last pass takes it out, with no other edit.
LEFTOVERS = (
    # An email address, also with a stray space after its "@" or inside its domain, or a comma for a dot (name@
    # example.org, name@g mail.com, name@gmail,com), or with a space before its "@" (JDOE @ EXAMPLE.COM). Its last
    # part has a letter, as EMAIL's domain does.
    Leftover("email", "emails", EMAIL,
             r"[A-Za-z0-9._%+'-]+(?:@ ?[A-Za-z0-9-]+(?: [A-Za-z0-9-]+)?(?:[.,][A-Za-z0-9-]+)*[.,][0-9-]*[A-Za-z]"
             r"[A-Za-z0-9-]*| @ ?[A-Za-z0-9-]+(?:[.,][A-Za-z0-9-]+)*\.[A-Za-z]{2,})"),
    # A number of seven digits or more, with spaces, dots, brackets or dashes between them, written after a phone
    # label (Tel, Telephone, Telefax, Phone, Cellphone, Mobile, Mob, Cell, Fax, Facsimile) with up to 12 other
    # characters but no digit between (Fax #: , Phone No. , Tel: (-, or a line break), or with none, the label run
    # into the digits (Phone0722...); or such a number written after one already removed, with a comma, slash,
    # semicolon, dash or "or" before it, and maybe the letter l typed for a 1 ([contact removed]l, 0722...; a page
    # stripped before ticket 63 kept the second number of "Tel: 0722... or 0733...").
    Leftover("phone", "phones", LABELLED,
             r"(?i)(\b(?:tel|telephone|telefax|phone|cellphone|mobile|mob|cell|fax|facsimile)(?:\b[^0-9]{0,12})?"
             r"|\[contact removed\][ \t]*l?[ \t]*(?:[,;/-]|or\b)[ \t]*)\+?[0-9](?:[ ().–-]*[0-9]){6,}"),
    # A number of nine digits or more after Ph, M, Contact or WhatsApp and a colon or No. (Contact: 254 722 123456).
    Leftover("short_phone", "phones", SHORT_LABELLED,
             r"(?i)(\b(?:ph|m|contact|whats\s?app)\b\.?(?:\s*(?:no\.?|number)\s*:?|\s*:)[ \t]*)[(+]{0,2}[0-9]"
             r"(?:[ ().–-]*[0-9]){8,}"),
    # A person's name after "Attention" and a title (ATTENTION: Mr. Francis Kombe), the label kept.
    Leftover("name", "names", ATTENTION,
             r"(\b(?i:attention)\b[ \t]*:?[ \t]*)(?i:mr|mrs|ms|miss|dr|eng|prof)\b\.?"
             r"(?:[ \t]+[A-Z][A-Za-z'’-]*\.?){1,4}"),
)
# The same patterns, as the removal reads them. ASCII, because RE2 and Java's \b and (?i) know only ASCII letters.
CHECKED = tuple((leftover, re.compile(leftover.pattern, re.A)) for leftover in LEFTOVERS)
# The removal's other rules, which the nightly check does not look for, each with the reason (ticket 121). A rule the
# removal gains goes in LEFTOVERS or here, and tests/test_contacts_left.py fails until it is in one of them.
NOT_CHECKED = (
    (PHONE, "A number with no label is a phone number only by _phone's test, which tells it from a date, an amount, "
            "a fiscal year or a postal code. No pattern the SQL warehouse reads can run that test."),
    (EMAIL_SPELLED_OUT, "No recorded notice spells out an address, so no test could show that a pattern finds what "
                        "this rule removes. Every page the workspace holds was stripped with it, since October 23, "
                        "2026."),
    (DIGIT_RUN, "It finds a page's own phone numbers, which only the record's contact fields name, and bronze "
                "replaced those fields before silver reads the page."),
    (AFTER_EMAIL, "What it removes is part of an address the removal counted already: the domain of a second address "
                  "run into the first."),
    (LINE_ENDING, "What it removes is part of a number the removal counted already: the last digit or two of another "
                  "line."),
)
SIGNS_BEFORE = re.compile(r"[(+][(+ \t–-]*$")  # a number's own bracket or plus, written before its first digit


def _phone(candidate: str) -> bool:
    first = candidate.split("/")[0].strip()
    digits = re.sub(r"\D", "", first)
    # with a plus, eight digits are enough: a country code and five more (+254 20 123)
    shortest = 8 if first.startswith("+") else 9
    if not shortest <= len(digits) <= 15 or digits.startswith("000"):
        return False
    return not any(pattern.fullmatch(first) for pattern in (DATE_LIKE, AMOUNT_LIKE, FISCAL_YEARS, POSTAL_CODE))


def _an_address(candidate: str) -> bool:
    """An email address's domain has a letter. A rate written after a year, as a report's table
    writes "INR - 2013 @7.4%", has none, and stays."""
    return bool(re.search(r"@\s?[^@]*[A-Za-z]", candidate))


def _labelled_number(numbers: str, shortest: int = 7) -> bool:
    """Seven digits or more (nine after a short label, as SHORT_LABELLED says), or any alternate left after a
    removed number (Tel: [contact removed] / 8, the last digit of a second line)."""
    digits = len(re.sub(r"\D", "", numbers.replace(REMOVED, "")))
    return digits >= shortest or (REMOVED in numbers and digits >= 1)


def _digits(value: str) -> str | None:
    """A recorded value's digits, when the value is a phone number."""
    digits = re.sub(r"\D", "", value)
    return digits if len(digits) >= 7 and len(digits) >= len(re.sub(r"[\s+()./–-]", "", value)) else None


def _pattern(values: list[str]) -> re.Pattern | None:
    words = [r"\s+".join(re.escape(word) for word in value.split()) for value in values]
    return re.compile(r"\b(?:" + "|".join(words) + r")\b", re.I) if words else None


class Stripper:
    """Strips one page, counting what it removed by kind. The page's own contact emails, then its
    names, are each one pattern, longest first, matched whatever their spacing or capitals. Its phone
    numbers are matched by their digits, whatever their separators."""

    def __init__(self, values: list[str]):
        self.phones = {digits for digits in (_digits(value) for value in values) if digits}
        known = sorted((value.strip() for value in values if not _digits(value) and len(value.strip()) >= 4),
                       key=len, reverse=True)
        self.patterns = [(kind, pattern) for kind, pattern in (
            ("emails", _pattern([value for value in known if "@" in value])),
            ("names", _pattern([value for value in known if "@" not in value]))) if pattern]
        self.counts: Counter = Counter()

    @property
    def removed(self) -> int:
        return sum(self.counts.values())

    def _known_phone(self, run: str) -> bool:
        digits = re.sub(r"\D", "", run)
        return any(phone in digits for phone in self.phones)

    def _sub(self, pattern: re.Pattern, text: str, kind: str, check=None) -> str:
        def replace(match):
            if check and not check(match.group(0)):
                return match.group(0)
            self.counts[kind] += 1
            return REMOVED
        return pattern.sub(replace, text)

    def text(self, text: str, labelled_only: bool = False) -> str:
        """The text with its contact details replaced. With labelled_only, a number comes out only when
        a phone label comes before it: a number with no label is left as written."""
        for kind, pattern in self.patterns:
            text = self._sub(pattern, text, kind)
        if self.phones:
            text = self._sub(DIGIT_RUN, text, "phones", self._known_phone)
        text = self._sub(EMAIL, text, "emails", _an_address)
        text = self._sub(EMAIL_SPELLED_OUT, text, "emails")
        text = AFTER_EMAIL.sub(REMOVED, text)  # part of an address already counted
        if not labelled_only:
            text = self._sub(PHONE, text, "phones", _phone)
            text = LINE_ENDING.sub(REMOVED, text)  # part of a number already counted
        text = LABELLED.sub(self._labelled, text)
        text = SHORT_LABELLED.sub(lambda match: self._labelled(match, shortest=SHORT_LABEL_DIGITS), text)
        if labelled_only:
            return text
        text = ATTENTION.sub(self._attention, text)
        return self.left(text)

    def left(self, text: str) -> str:
        """The removal's last pass: everything the nightly check looks for (LEFTOVERS), rule by rule, with the label
        and the words around it kept. A number taken out can leave another written after it ([contact removed]l,
        0722...), so it runs until it finds nothing."""
        while True:
            found = text
            for leftover, pattern in CHECKED:
                found = pattern.sub(lambda match, kind=leftover.kind: self._leftover(match, kind), found)
            if found == text:
                return text
            text = found

    def _leftover(self, match: re.Match, kind: str) -> str:
        label = SIGNS_BEFORE.sub("", match.group(1) or "") if match.re.groups else ""
        self.counts[kind] += 1
        return label + REMOVED

    def _labelled(self, match: re.Match, shortest: int = 7) -> str:
        numbers = match.group("numbers")
        if not _labelled_number(numbers, shortest):
            return match.group(0)
        self.counts["phones"] += 1
        return match.group("label") + REMOVED + TRAILING.search(numbers).group(0)

    def _attention(self, match: re.Match) -> str:
        self.counts["names"] += 1
        return match.group("label") + REMOVED


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


@dataclass(frozen=True)
class Removed:
    """One kind of contact detail strip() took out of a page: how many, and from how many of its records."""

    removed: int
    records: int


def strip_counted(body: dict) -> tuple[dict, dict[str, Removed]]:
    """The page with its contact details replaced, and, for each kind it replaced (KINDS), how many and from how
    many records: a contact field it emptied, or a name, email or phone number it took out of the free text."""
    found, fields = set(), Counter()
    for record in _records(body):
        for field in CONTACT_FIELDS:
            if _filled(record.get(field)):
                fields[FIELD_KINDS[field]] += 1
                if field in SEARCHED:
                    found.add(str(record[field]))
    stripper = Stripper(sorted(found))
    records: Counter = Counter()

    def stripped(key, value, kinds: set | None):
        if key in CONTACT_FIELDS:
            return REMOVED if _filled(value) else value
        if key in FREE_TEXT and isinstance(value, str):
            before = Counter(stripper.counts)
            text = stripper.text(value)
            if kinds is not None:
                kinds.update(kind for kind, number in (stripper.counts - before).items() if number)
            return text
        if isinstance(value, dict):
            if any(field in value for field in CONTACT_FIELDS + FREE_TEXT):
                own = {FIELD_KINDS[field] for field in CONTACT_FIELDS if _filled(value.get(field))}
                out = {name: stripped(name, item, own) for name, item in value.items()}
                records.update(own | ({ANY} if own else set()))
                return out
            return {name: stripped(name, item, kinds) for name, item in value.items()}
        if isinstance(value, list):
            return [stripped(None, item, kinds) for item in value]
        return value

    body = stripped(None, body, None)
    totals = fields + stripper.counts
    found = {kind: Removed(totals[kind], records[kind]) for kind in KINDS if totals[kind]}
    if found:  # every kind together, so a count of notices counts a notice once whatever it lost
        found[ANY] = Removed(sum(item.removed for item in found.values()), records[ANY])
    return body, found


def strip(body: dict) -> tuple[dict, int]:
    """The page with its contact details replaced, and how many it replaced."""
    body, removals = strip_counted(body)
    return body, removals[ANY].removed if removals else 0


def strip_text(text: str) -> tuple[str, int]:
    """A document's text with every email address and every number written after a phone label
    replaced, and how many it replaced.

    A report can print a person's email and phone, as a PAD's data sheet prints its contact's
    ("Telephone No.: ... Email: ..."). A document has no contact fields to say whose they are, so its
    names stay. A number with no label stays too: in a Procurement Plan's tables a date runs into the
    next column's digits (2019-11-26   2019-12-27), and a STEP reference is cut at a column's edge
    (NWWDA-WSDP-03-2019-), so the pattern for a phone number with a trunk zero would take dates and
    references out of the plan as published."""
    stripper = Stripper([])
    return stripper.text(text, labelled_only=True), stripper.removed


def strip_again(text: str | None) -> str | None:
    """A notice's free text with every contact detail the patterns find replaced, as strip() replaces them on a
    page, but without the record's contact fields to say whose they are: bronze has replaced those already. Silver
    runs it on each page it reads, so a page bronze kept before a fix to the patterns loses what the fix takes out
    when silver reads the page again (ticket 76)."""
    return Stripper([]).text(text) if isinstance(text, str) and text else text


def strip_left(text: str | None) -> str | None:
    """The removal's last pass alone (Stripper.left), for a notice's text as silver keeps it: the plain text the
    nightly check reads, where an HTML entity or tag no longer sits between a label and its number."""
    return Stripper([]).left(text) if text else text


def _filled(value) -> bool:
    return bool(str(value or "").strip())


def removed_from(record: dict) -> bool:
    """Whether strip() replaced any contact detail in this record, in a contact field or its free text."""
    return (any(record.get(field) == REMOVED for field in CONTACT_FIELDS)
            or any(REMOVED in str(record.get(field) or "") for field in FREE_TEXT))
