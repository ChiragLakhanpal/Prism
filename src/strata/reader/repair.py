"""Plan text read from a PDF, repaired where the project's own records show what the plan says (ticket 131).

A Procurement Plan's table is read from a PDF, and the PDF's text carries two kinds of damage into its rows. A cell
wraps its text at its edge, sometimes inside a word, and the reader keeps a space at each wrap, so a description reads
"Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply". And the layout parser can read
one character for another that looks like it: on the workspace on October 29, 2026, a row of P156634's plan of
October 9, 2026 read KE-NWWDA-193461-90-RF8. This module is the one place the plan reader repairs both, after a
row is read and before it is written (strata.lakehouse.plans.write_rows), and it never guesses:

- A reference in STEP's form that breaks STEP's grammar (strata.lakehouse.clean.follows_step_grammar: the kinds and
  method codes of config/references.toml) is repaired when exactly one swap of a look-alike pair (the same file's
  look_alikes) makes it whole and a notice of the project or one of its plan versions carries the repaired
  reference. The row keeps the reference as read beside it, with the record that carries the repair. Any other
  reference that breaks the grammar stays as read and is flagged reference_as_read, and the page shows it as the
  plan gives it: one that a record carries as read too, which STEP holds that way, and one no record settles.
- A word split by a space inside a description is joined when the joined word is in the titles of the project's
  notices or among the words of the plan version's other rows, unless both halves are words of two letters or more
  that the notices' titles use on their own ("Motor Cycles" stays two words). Each join is recorded with the words
  as read and where the joined word was found.

Each row keeps its reference and description as read in their own columns, which the source view shows: the
repaired values are derived from them, each with its reason (CLAUDE.md rule 2).
"""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Container, Iterable, Mapping, Sequence
from dataclasses import dataclass

from strata.lakehouse import clean

NOTICE_EVIDENCE = "strata.silver.notices"
PLAN_ROW_EVIDENCE = "strata.silver.plan_rows"
PLAN_TEXT_EVIDENCE = "strata.silver.plan_versions"

LOOK_ALIKE = "look_alike"  # one look-alike swap made the reference whole, and a record carries it
AS_READ = "reference_as_read"  # the reference breaks STEP's grammar and no record settles it
PLAN_TEXT = "plan_text"  # the plan's own text gives the reference the layout parser misread (ticket 78)


@dataclass(frozen=True)
class Notice:
    """One notice of the project, as strata.silver.notices holds it: its id, its reference and its title."""

    notice_id: str
    reference: str | None
    title: str | None


# ── References ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ReferenceRead:
    """A plan row's Activity Reference No.: as the row keeps it, as it was read, why they differ or why it is
    flagged (LOOK_ALIKE, AS_READ, PLAN_TEXT or None), and the record that carries the reference the row keeps."""

    written: str
    as_read: str
    repair: str | None
    carried_by: str | None


def _key(reference: str) -> str:
    return re.sub(r"\s+", "", reference).upper()


def carried(notices: Iterable[Notice]) -> dict[str, str]:
    """Each reference the notices carry, written without spaces, with the evidence id of the first notice that
    carries it."""
    found: dict[str, str] = {}
    for notice in notices:
        if notice.reference and notice.reference.strip():
            found.setdefault(_key(notice.reference), f"{NOTICE_EVIDENCE}:{notice.notice_id}")
    return found


def _swaps(reference: str) -> set[str]:
    """Every reference one look-alike swap away: one character changed for its pair, the rest as read."""
    pairs = {a: b for a, b in clean.REFERENCES.look_alikes} | {b: a for a, b in clean.REFERENCES.look_alikes}
    return {reference[:i] + pairs[c] + reference[i + 1:] for i, c in enumerate(reference) if c in pairs}


def reference(read: str, records: Mapping[str, str]) -> ReferenceRead:
    """A reference as the row should keep it, given the references the project's records carry (records: each
    reference with the evidence id of a record that carries it)."""
    if not clean.in_step_form(read) or clean.follows_step_grammar(read):
        return ReferenceRead(read, read, None, None)
    if read in records:  # STEP holds it as read, so the plan prints it so: kept, and flagged as the plan gives it
        return ReferenceRead(read, read, AS_READ, records[read])
    whole = sorted(swap for swap in _swaps(read) if clean.follows_step_grammar(swap) and swap in records)
    if len(whole) == 1:
        return ReferenceRead(whole[0], read, LOOK_ALIKE, records[whole[0]])
    return ReferenceRead(read, read, AS_READ, None)


# ── Descriptions ─────────────────────────────────────────────────────────

LETTERS = r"[^\W\d_]+"  # a run of letters, in any alphabet
_LAST_LETTERS = re.compile(rf"{LETTERS}$")
_FIRST_LETTERS = re.compile(LETTERS)


@dataclass(frozen=True)
class Join:
    """One split word joined: the two halves as read ("Bo reholes"), the word written ("Boreholes"), and where the
    joined word was found: "notices" (a notice's title) or "plan" (another row of the plan version)."""

    read: str
    joined: str
    found_in: str

    def as_dict(self) -> dict:
        return {"read": self.read, "joined": self.joined, "found_in": self.found_in}


@dataclass(frozen=True)
class DescriptionRead:
    """A plan row's Description as the row keeps it, as it was read, and each join that made the difference."""

    written: str
    as_read: str
    joins: tuple[Join, ...]


def words(texts: Iterable[str | None]) -> frozenset[str]:
    """Every word the texts use, in lower case: the runs of letters between spaces, digits and punctuation."""
    return frozenset(word.lower() for text in texts if text for word in re.findall(LETTERS, text))


def description(read: str, notice_words: Container[str], plan_words: Container[str]) -> DescriptionRead:
    """A description with each word the PDF split joined again, given the words of the project's notices' titles
    and the words of the plan version's other rows (words). Two halves join when the joined word is in either list,
    unless both are words of two letters or more that the notices' titles use on their own."""
    tokens: list[str] = []
    joins: list[Join] = []
    for token in read.split(" "):
        left = _LAST_LETTERS.search(tokens[-1]) if tokens else None
        right = _FIRST_LETTERS.match(token)
        if left and right:
            a, b = left.group(0), right.group(0)
            joined = (a + b).lower()
            found_in = "notices" if joined in notice_words else "plan" if joined in plan_words else None
            both_words = min(len(a), len(b)) >= 2 and a.lower() in notice_words and b.lower() in notice_words
            if found_in and not both_words:
                tokens[-1] += token
                joins.append(Join(f"{a} {b}", a + b, found_in))
                continue
        tokens.append(token)
    return DescriptionRead(" ".join(tokens), read, tuple(joins))


# ── A project's plan rows ────────────────────────────────────────────────

@dataclass(frozen=True)
class VersionRows:
    """One plan version's rows as the STEP reader read them (strata.reader.step.PlanRow), with the references its
    published text lists (Route A)."""

    document_id: str
    listed: Sequence[str]
    rows: Sequence  # of strata.reader.step.PlanRow


def plan(versions: Sequence[VersionRows], notices: Iterable[Notice]) -> None:
    """Every row of a project's plan versions repaired in place, after it is read and before it is written.

    A row's reference is checked against the references the project's notices carry, then those the other versions'
    rows read, then those every version's text lists; a row whose reference the plan's text gave over the layout
    parser's reading (ticket 78) keeps that, with the reason plan_text. A row's description is joined with the words
    of the notices' titles and of its version's other rows. Each row keeps what was read beside what is written."""
    notices = list(notices)
    notice_words = words(notice.title for notice in notices)
    # Every version's references as read, before any row is repaired, so no repair rests on another.
    in_rows: dict[str, list[str]] = {}
    in_texts: dict[str, str] = {}
    for version in versions:
        for row in version.rows:
            in_rows.setdefault(row.activity_reference_no, []).append(version.document_id)
        for listed in version.listed:
            in_texts.setdefault(listed, version.document_id)
    from_notices = carried(notices)
    for version in versions:
        records = _Records(from_notices, in_rows, in_texts, version.document_id)
        for row in version.rows:
            if row.activity_reference_no != row.reference_as_read:  # the plan's text gave it (ticket 78)
                row.reference_repair = PLAN_TEXT
                row.reference_carried_by = f"{PLAN_TEXT_EVIDENCE}:{version.document_id}"
            else:
                found = reference(row.activity_reference_no, records)
                row.activity_reference_no, row.reference_repair, row.reference_carried_by = (
                    found.written, found.repair, found.carried_by)
        each = [Counter(words([row.description_as_read])) for row in version.rows]
        every: Counter = Counter()
        for counted in each:
            every.update(counted)
        for row, own in zip(version.rows, each):
            if row.description_as_read:
                found = description(row.description_as_read, notice_words, _OtherRows(every, own))
                row.description, row.description_joins = found.written, found.joins


@dataclass(frozen=True)
class _Records(Mapping):
    """The references that settle one version's rows, each with the evidence id of a record that carries it: the
    project's notices, then the other versions' rows, then any version's text."""

    notices: Mapping[str, str]
    in_rows: Mapping[str, list[str]]  # each reference, with the versions whose rows read it
    in_texts: Mapping[str, str]  # each reference, with the first version whose text lists it
    own: str  # the version being repaired, whose own rows do not count

    def __getitem__(self, reference: str) -> str:
        if reference in self.notices:
            return self.notices[reference]
        other = next((document_id for document_id in self.in_rows.get(reference, ()) if document_id != self.own), None)
        if other is not None:
            return f"{PLAN_ROW_EVIDENCE}:{other}/{reference}"
        if reference in self.in_texts:
            return f"{PLAN_TEXT_EVIDENCE}:{self.in_texts[reference]}"
        raise KeyError(reference)

    def __iter__(self):
        return iter({*self.notices, *self.in_rows, *self.in_texts})

    def __len__(self) -> int:
        return len({*self.notices, *self.in_rows, *self.in_texts})


@dataclass(frozen=True)
class _OtherRows:
    """The words of a version's other rows: those some row other than this one uses."""

    every: Counter
    own: Counter

    def __contains__(self, word: object) -> bool:
        return self.every[word] > self.own[word]
