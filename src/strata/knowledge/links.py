"""Links between strata: the edge table and the link scorer (ticket 22; docs/PLAN.md section 5; ADR 0004).

The edge table, strata.gold.edge, holds every link between strata, one row per link, each end named by its
evidence id. KINDS is the one list of what a link can say. Most links are keys the records share (a project
plans a package, a package was awarded as a contract, a contract was signed by a supplier, a document has a
passage), which gold/edge.sql reads from the tables. One kind is scored: a contract and a paragraph of its own
project's reports that appeared together. The screens write that link as "appeared together", never as a cause,
and never show a kind's name (the copy file has the words).

The scorer needs no model, so the offline gate and the nightly job run it alike. It pairs each contract with
each numbered paragraph of its project's reports and scores five parts, each worth at most the points
config/thresholds.toml's [links] gives it, rounded to two decimals:

- project: the two come from the same project, as every pair does;
- sector: the paragraph's project sector in Strata's taxonomy is the contract's project's;
- time: the document's date is close to the signing, falling in a straight line to nothing at
  time_window_months apart. A month is 365.25 / 12 days, and months_apart is rounded to the nearest month;
- text: the share of the words of the contract's description the paragraph holds (stemmed as search stems them,
  leaving out short and common words), counting a description of fewer than text_min_words words as that many;
- mentions: what the paragraph mentions of the contract, each kind once: its STEP reference or another
  reference, a place its description names ("in Bundi District"), its description, or its procurement
  category ("works contracts"), with where the words sit in the paragraph, so a screen can highlight them.

The total is the sum of the rounded parts. A pair is kept when its total reaches links.threshold. relink() scores
every pair into strata.silver.contract_passage_links, keeps only its latest run, then syncs strata.gold.edge
from gold/edge.sql. It is the nightly job's relink task (strata.lakehouse.nightly), and the fixture build runs it
again once the passage reader has read the documents.
"""

from __future__ import annotations

import datetime as dt
import functools
import json
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from importlib import resources

from strata.config import Thresholds, load_thresholds
from strata.knowledge.embed import WORD, stem
from strata.lakehouse import gold
from strata.lakehouse.engine import Engine

# What a link can say, the one list. appeared_together is the only scored kind.
APPEARED_TOGETHER = "appeared_together"
KINDS = ("borrows", "plans", "has", "advertised_in", "awarded_as", "signed_by", "lists_bidders", "described_in",
         APPEARED_TOGETHER)
PARTS = ("project", "sector", "time", "text", "mentions")
DAYS_A_MONTH = 365.25 / 12
CENT = Decimal("0.01")

# How a paragraph writes each procurement category, as gold.contract names it: "works contracts" or
# "civil works" for Works. A category a paragraph mentions is a shared mention of the kind category.
CATEGORY_WORDS = {
    "Works": (r"works?\s+contracts?", r"civil\s+works"),
    "Goods": (r"goods\s+contracts?", r"supply\s+contracts?"),
    "Consultant Services": (r"consultancy\s+(?:contracts?|services)", r"consult(?:ant|ing)\s+(?:contracts?|services)"),
    "Non-consulting Services": (r"non-consulting\s+services",),
}
# A place a description names: the capitalized words after "in" or "at", without a word that only says what
# kind of place it is ("in Bundi District" names Bundi).
PLACE = re.compile(r"\b(?:in|at)\s+((?:[A-Z][a-z]+\.?)(?:\s+[A-Z][a-z]+\.?)*)")
PLACE_KINDS = {"County", "District", "Dist", "Dist.", "Town", "City", "Region", "Province", "State", "Sub",
               "Municipality", "Village", "Division", "Office", "Offices"}
REFERENCE = re.compile(r"\bPackage\s+No\.?\s*([A-Z0-9][A-Z0-9/-]{3,})", re.IGNORECASE)
STOP_WORDS = frozenset(
    "the and for with from that this which have has had were was are been into under over upon their its our "
    "not all any per one two three four five six seven eight nine ten other each such than then also".split())
TAXONOMY_YEAR = re.compile(r"^FY\d{2}\s+-\s+")


@dataclass(frozen=True)
class Contract:
    contract_id: str
    project_id: str
    step_reference: str | None
    references: tuple[str, ...]
    description: str | None
    category: str | None
    signed_on: dt.date | None
    public_from: dt.date
    sector: str | None
    sector_code: str | None
    sector_name: str | None


@dataclass(frozen=True)
class Paragraph:
    passage_id: str
    project_id: str
    sector: str | None
    dated: dt.date | None
    text: str
    public_from: dt.date


@dataclass(frozen=True)
class Link:
    contract: Contract
    paragraph: Paragraph
    points: dict[str, Decimal]
    score: Decimal
    months_apart: int | None
    time_direction: str | None
    matched_terms: list[str]
    mentions: list[dict]


def _points(value: float) -> Decimal:
    return Decimal(str(value)).quantize(CENT, rounding=ROUND_HALF_UP)


def _words(text: str | None) -> dict[str, str]:
    """A text's words that carry meaning, by their stem, each with the first way the text writes it."""
    found: dict[str, str] = {}
    for written in WORD.finditer((text or "").lower()):
        word = written.group(0)
        if len(word) < 3 or word.isdigit() or word in STOP_WORDS:
            continue
        found.setdefault(stem(word), word)
    return found


def months_apart(signed_on: dt.date | None, dated: dt.date | None) -> tuple[int | None, str | None]:
    """Months between the signing and a document's date, rounded to the nearest month, and whether the document
    came after, before or in the same month as the signing."""
    if signed_on is None or dated is None:
        return None, None
    days = (dated - signed_on).days
    months = round(abs(days) / DAYS_A_MONTH)
    return months, "same" if months == 0 else ("after" if days > 0 else "before")


def places(description: str | None) -> list[str]:
    """The places a contract's description names, as it writes them."""
    found = []
    for named in PLACE.finditer(description or ""):
        words = [word for word in named.group(1).split() if word not in PLACE_KINDS]
        if words and " ".join(words) not in found:
            found.append(" ".join(words))
    return found


@dataclass(frozen=True)
class Weights:
    """The [links] values of the thresholds file, read once for a run."""

    threshold: Decimal
    project: float
    sector: float
    time: float
    window: float
    text: float
    min_words: int
    mention: dict
    mentions_max: float

    @classmethod
    def read(cls, limits: Thresholds) -> Weights:
        value = limits.value
        return cls(_points(float(value("links.threshold"))), float(value("links.project_points")),
                   float(value("links.sector_points")), float(value("links.time_points")),
                   float(value("links.time_window_months")), float(value("links.text_points")),
                   int(value("links.text_min_words")),
                   {kind: float(value(f"links.mention_{kind}_points")) for kind in ("reference", "place", "name", "category")},
                   float(value("links.mentions_max")))


@functools.lru_cache(maxsize=4096)
def _patterns(contract: Contract) -> tuple[tuple[str, str | None, str, re.Pattern], ...]:
    """What a paragraph may mention of the contract, as (kind, code, words it must hold, pattern), in the order
    each kind is tried. A pattern is searched only in a paragraph that holds its words, in lower case."""
    found: list[tuple[str, str | None, str, re.Pattern]] = [
        ("reference", reference, reference.lower(), re.compile(rf"(?<![\w-]){re.escape(reference)}(?![\w-])"))
        for reference in contract.references]
    found += [("place", place, place.lower(), re.compile(rf"\b{re.escape(place)}\b"))
              for place in places(contract.description)]
    description = " ".join((contract.description or "").split())
    if len(description) >= 20:
        found.append(("name", None, description.lower(), re.compile(re.escape(description), re.IGNORECASE)))
    return tuple(found)


@functools.lru_cache(maxsize=16384)
def _category(category: str | None, text: str) -> dict | None:
    """Where a paragraph first mentions a procurement category, such as "works contract" for Works."""
    for pattern in CATEGORY_WORDS.get(category or "", ()):
        match = re.search(rf"\b{pattern}\b", text, re.IGNORECASE)
        if match is not None:
            return {"kind": "category", "code": category, "text": match.group(0), "start": match.start(),
                    "end": match.end()}
    return None


@functools.lru_cache(maxsize=8192)
def _lower(text: str) -> str:
    return text.lower()


def mentions(contract: Contract, text: str) -> list[dict]:
    """What the paragraph mentions of the contract, each kind once, with where its words sit in the text."""
    found: list[dict] = []
    lower = _lower(text)
    for kind, code, words, pattern in _patterns(contract):
        if words not in lower or any(mention["kind"] == kind for mention in found):
            continue
        match = pattern.search(text)
        if match is not None:
            found.append({"kind": kind, "code": code, "text": match.group(0), "start": match.start(), "end": match.end()})
    category = _category(contract.category, text)
    if category is not None:
        found.append(dict(category))
    return sorted(found, key=lambda mention: mention["start"])


@functools.lru_cache(maxsize=8192)
def _cached_words(text: str) -> dict[str, str]:
    return _words(text)


def score(contract: Contract, paragraph: Paragraph, limits: Thresholds | Weights) -> Link:
    """The link between a contract and a paragraph: each part's points, the total and what matched."""
    weights = limits if isinstance(limits, Weights) else Weights.read(limits)
    months, direction = months_apart(contract.signed_on, paragraph.dated)
    described = _cached_words(contract.description or "")
    written = _cached_words(paragraph.text)
    shared = [written[word] for word in described if word in written]
    found = mentions(contract, paragraph.text)
    mentioned = min(sum(weights.mention[mention["kind"]] for mention in found), weights.mentions_max)
    points = {
        "project": _points(weights.project if paragraph.project_id == contract.project_id else 0),
        "sector": _points(weights.sector if contract.sector and paragraph.sector == contract.sector else 0),
        "time": _points(weights.time * max(0.0, 1 - months / weights.window) if months is not None else 0),
        "text": _points(weights.text * len(shared) / max(len(described), weights.min_words)),
        "mentions": _points(mentioned),
    }
    return Link(contract, paragraph, points, sum(points.values(), Decimal("0.00")), months, direction, shared[:5], found)


# ── The relink task ──────────────────────────────────────────────────────

LINK_COLUMNS = ("run_id", "contract_id", "passage_id", "project_id", "score", "score_project", "score_sector",
                "score_time", "score_text", "score_mentions", "months_apart", "time_direction", "sector_code",
                "sector_name", "category", "matched_terms", "mentions", "scored_on", "public_from")


def _sql(name: str) -> str:
    return (resources.files("strata.knowledge") / "sql" / "links" / name).read_text()


def _contract(row: dict) -> Contract:
    references = [row["step_reference"], row["borrower_contract_reference_number"], row["wb_contract_number"],
                  *(found.group(1) for found in REFERENCE.finditer(row["contract_description"] or ""))]
    sector_name = TAXONOMY_YEAR.sub("", row["sector_name"]) if row["sector_name"] else None
    return Contract(row["contract_id"], row["project_id"], row["step_reference"],
                    tuple(dict.fromkeys(ref for ref in references if ref and len(ref) >= 5)), row["contract_description"],
                    row["procurement_category"], row["contract_signing_date"], row["public_from"], row["sector"],
                    row["sector_code"], sector_name)


def scored_links(engine: Engine, limits: Thresholds) -> list[Link]:
    """Every pair of a contract and a paragraph of its own project's reports that reaches links.threshold."""
    weights = Weights.read(limits)
    result = engine.run(_sql("contracts.sql"))
    contracts = [_contract(dict(zip(result.columns, row))) for row in result.rows]
    result = engine.run(_sql("passages.sql"))
    paragraphs: dict[str, list[Paragraph]] = defaultdict(list)
    for row in (dict(zip(result.columns, row)) for row in result.rows):
        paragraphs[row["project_id"]].append(Paragraph(row["passage_id"], row["project_id"], row["sector"],
                                                       row["document_date"], row["text"], row["public_from"]))
    kept = []
    for contract in contracts:
        for paragraph in paragraphs.get(contract.project_id, ()):
            link = score(contract, paragraph, weights)
            if link.score >= weights.threshold:
                kept.append(link)
    return kept


def relink(engine: Engine, run_id: str, clock: Callable[[], dt.datetime], limits: Thresholds | None = None) -> int:
    """Score every contract against the paragraphs of its project's reports, keep the links that reach the
    threshold as this run's, and sync the edge table. Returns the rows it changed."""
    limits = limits or load_thresholds()
    today = clock().astimezone(dt.UTC).date()
    rows = [(run_id, link.contract.contract_id, link.paragraph.passage_id, link.contract.project_id, link.score,
             *(link.points[part] for part in PARTS), link.months_apart, link.time_direction, link.contract.sector_code,
             link.contract.sector_name, link.contract.category, json.dumps(link.matched_terms),
             json.dumps(link.mentions), today, max(link.contract.public_from, link.paragraph.public_from))
            for link in scored_links(engine, limits)]
    engine.run(_sql("forget_run.sql"), {"run_id": run_id})
    added = engine.insert_rows("strata.silver.contract_passage_links", LINK_COLUMNS, rows)
    engine.run(_sql("keep_run.sql"), {"run_id": run_id})
    return added + gold.sync(engine, "edge")
