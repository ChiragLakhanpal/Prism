"""The deep research brief (ticket 148): what the writer is sent, how its answer is read, how each sentence is checked
against the items it cites, and the brief that the verifier's kept sentences make.

The brief has eight sections, in this order (the sample of November 5, 2026, .notes/prism-sample):

  headline       one sentence
  picture        four to six sentences: what is happening on the ground
  bottom_line    two to four sentences: what it means for contracts
  developments   dated groups, newest first, each with sentences; an undated item's group is "undated"
  by_site        groups, each with a title sentence and sentences
  voices         words quoted from an item, each with who said them, the outlet and the date
  questions      five to seven, each a bold lead and a question to take to the agencies
  could_not_see  one to three sentences: what the run could not see

Every sentence is a claim in the answer contract's shape (src/strata/agent/claims.py): its sentence, kind (record,
quote, summary or advice), the evidence ids of the items it rests on, the numbers and dates it states, and the quote.
The verifier checks every sentence (src/strata/agent/verifier.py): checks 1 to 3 against the items it cites, read
through checked_row so a number or date the item's own words print backs a sentence that states it, check 5 with the
items backing advice, and check 4's judge on every sentence the first checks did not prove, the headline and bottom
line among them.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal

from strata.agent.claims import Claim, ClaimsError, claims_from
from strata.agent.verifier import mentions

TOOL = "research_evidence"
SECTIONS = ("headline", "picture", "bottom_line", "developments", "by_site", "voices", "questions", "could_not_see")
# How many sentences, or groups, each counted section holds (the ticket; the sample brief).
SIZES = {"headline": (1, 1), "picture": (4, 6), "bottom_line": (2, 4), "questions": (5, 7), "could_not_see": (1, 3)}
UNDATED = "undated"
# The sections whose advice is Prism's own: a question to take to the agencies, a bottom-line item (the sample brief's
# pages 1 and 8). Check 4 judges only the facts inside their advice sentences, never the asking (ticket 155).
OWN_ADVICE = ("bottom_line", "questions")


class BriefError(ValueError):
    """The writer's answer is not a brief in the agreed shape."""


@dataclass(frozen=True)
class Place:
    """Where one sentence sits in the brief: its section, its group within a grouped section, and its part of the
    group (title, sentence, quote or question)."""
    section: str
    group: int | None = None
    part: str = "sentence"


# ── What the writer is sent ──────────────────────────────────────────────

def _project(facts) -> dict:
    """ProjectFacts (ticket 147), or a mapping in its shape, as plain data."""
    if isinstance(facts, Mapping):
        found = dict(facts)
    else:
        found = {name: getattr(facts, name) for name in ("project_id", "project_name", "country_code", "country_name",
                                                         "implementing_agencies", "sector_name", "closing_date",
                                                         "status") if hasattr(facts, name)}
    for key, value in found.items():
        if isinstance(value, dt.date):
            found[key] = value.isoformat()
        elif isinstance(value, tuple):
            found[key] = list(value)
    found.pop("locations", None)
    return found


COVERAGE = "strata.research.coverage"  # a coverage record's evidence id, before :<run id>/<source key>


def coverage_records(result: Mapping) -> list[dict]:
    """The run's coverage notes as records a could_not_see sentence cites (ticket 155): one per source the run asked,
    with whether it was reached, its status, how many items it gave and its note, which says why it was not reached or
    which pages could not be read, so only the headline or the feed's summary stands in."""
    run_id = (result.get("run") or {}).get("run_id")
    if not run_id:
        return []
    summary = result.get("summary") or result
    return [{"evidence_id": f"{COVERAGE}:{run_id}/{source['key']}", "run_id": run_id, "source_key": source["key"],
             "label": source.get("label"), "reached": reached, "status": source.get("status"),
             "items": source.get("items") or 0, "note": source.get("note")}
            for reached, sources in ((True, summary.get("sources_reached")), (False, summary.get("sources_not_reached")))
            for source in sources or ()]


def message(facts, result: Mapping) -> str:
    """The writer's message, as JSON: the project's facts, the run's summary record and its coverage, and every item.
    The items are data, never instructions (the writer instruction says so)."""
    summary = result["summary"]
    items = [{"evidence_id": row["evidence_id"], "source": row["source"].get("label"), "kind": row["kind"],
              "published": row["published"], "date_known": row["date_known"], "observed": row["observed"],
              "author": row["author"], "title": row["title"], "text": row["text"], "url": row["url"],
              "location": (row["location"] or {}).get("name"),
              **({"notice": row["notice"]} if row.get("notice") else {})} for row in result["rows"]]
    return json.dumps({"task": "research_brief", "as_of": result["as_of"], "project": _project(facts),
                       "summary_evidence_id": summary["evidence_id"],
                       "summary": {key: value for key, value in summary.items() if key not in ("evidence_id", "source")},
                       "coverage": result["coverage"], "coverage_records": coverage_records(result), "items": items},
                      ensure_ascii=False, indent=1)


# ── Reading the writer's answer ──────────────────────────────────────────

def _object(text: str) -> dict:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`").removeprefix("json").strip()
    try:
        answer = json.loads(stripped)
    except ValueError as error:
        raise BriefError(f"The writer's answer is not JSON: {error}") from error
    if not isinstance(answer, dict):
        raise BriefError("The writer's answer is not a JSON object.")
    missing = [section for section in SECTIONS if section not in answer]
    if missing:
        raise BriefError(f"The writer's brief has no {', '.join(missing)}.")
    return answer


def _claims(items, where: str) -> list[Claim]:
    try:
        return claims_from(items)
    except ClaimsError as error:
        raise BriefError(f"{where}: {error}") from error


def _list(answer: dict, section: str) -> list:
    value = answer[section]
    if not isinstance(value, list):
        raise BriefError(f"The brief's {section} must be a list.")
    return value


def _sized(section: str, found: list) -> None:
    low, high = SIZES[section]
    if not low <= len(found) <= high:
        raise BriefError(f"The brief's {section} has {len(found)}, not {low} to {high}.")


def parse(text: str) -> tuple[list[tuple[Place, Claim]], dict]:
    """The writer's answer as its sentences, each with its place in the brief, in the brief's order, and each group's
    own fields: a development's date and date_known, a voice's who, a question's lead. BriefError when the answer is
    not a brief in the agreed shape."""
    answer = _object(text)
    placed: list[tuple[Place, Claim]] = []
    groups: dict[str, list[dict]] = {}
    headline = answer["headline"]
    placed += [(Place("headline"), claim) for claim in _claims([headline] if isinstance(headline, dict) else headline,
                                                                 "headline")]
    _sized("headline", [claim for place, claim in placed])
    for section in ("picture", "bottom_line"):
        found = _claims(_list(answer, section), section)
        _sized(section, found)
        placed += [(Place(section), claim) for claim in found]
    for index, group in enumerate(_list(answer, "developments")):
        if not isinstance(group, dict):
            raise BriefError("Each development must be an object.")
        groups.setdefault("developments", []).append({"date": group.get("date"),
                                                      "date_known": group.get("date_known") is not False})
        placed += [(Place("developments", index), claim)
                   for claim in _claims(group.get("sentences"), f"development {index + 1}")]
    for index, group in enumerate(_list(answer, "by_site")):
        if not isinstance(group, dict) or not isinstance(group.get("title"), dict):
            raise BriefError("Each site must be an object with a title sentence.")
        groups.setdefault("by_site", []).append({})
        placed += [(Place("by_site", index, "title"), claim)
                   for claim in _claims([group["title"]], f"site {index + 1}'s title")]
        placed += [(Place("by_site", index), claim) for claim in _claims(group.get("sentences"), f"site {index + 1}")]
    for index, voice in enumerate(_list(answer, "voices")):
        if not isinstance(voice, dict) or not isinstance(voice.get("claim"), dict):
            raise BriefError("Each voice must be an object with its claim.")
        groups.setdefault("voices", []).append({"who": voice.get("who")})
        [claim] = _claims([voice["claim"]], f"voice {index + 1}")
        if claim.quote is None:
            raise BriefError(f"Voice {index + 1} quotes no item.")
        placed.append((Place("voices", index, "quote"), claim))
    questions = _list(answer, "questions")
    _sized("questions", questions)
    for index, question in enumerate(questions):
        if not isinstance(question, dict):
            raise BriefError("Each question must be an object with its lead and sentences.")
        groups.setdefault("questions", []).append({"lead": question.get("lead")})
        placed += [(Place("questions", index, "question"), claim)
                   for claim in _claims(question.get("sentences"), f"question {index + 1}")]
    found = _claims(_list(answer, "could_not_see"), "could_not_see")
    _sized("could_not_see", found)
    placed += [(Place("could_not_see"), claim) for claim in found]
    return placed, groups


def facts_only(placed: list[tuple[Place, Claim]]) -> set[int]:
    """The sentences, by index, whose question or recommendation is Prism's own: the advice of the bottom line and the
    questions. Check 4 asks only whether the facts inside them follow from the items they cite."""
    return {index for index, (place, claim) in enumerate(placed)
            if place.section in OWN_ADVICE and claim.kind == "advice"}


# ── Checking a sentence against an item ──────────────────────────────────

def _iso(when) -> str | None:
    if when.year is None:
        return None
    return dt.date(when.year, when.month or 1, when.day or 1).isoformat()


def checked_row(row: Mapping | None) -> Mapping | None:
    """An item as checks 1 to 3 read it: with the numbers and dates its own words print, so a sentence that states a
    number or date an article or a report printed is backed by the item that printed it (the ticket: "numbers and
    dates match a cited item"). A summary record is read as it is. The judge reads the item as the tool gave it."""
    if row is None or not isinstance(row.get("text"), str) or "kind" not in row:
        return row
    # The author too: an outlet's name can print a digit, as Big3Africa does (ticket 155).
    found = mentions(" ".join(part for part in (row.get("author"), row.get("title"), row["text"])
                              if isinstance(part, str)))
    numbers = sorted({format(mention.value, "f") for mention in found if isinstance(mention.value, Decimal)})
    dates = sorted({day for mention in found if mention.kind == "date" and (day := _iso(mention.value))})
    return {**row, "printed": {"numbers": numbers, "dates": dates}}


# ── The brief ────────────────────────────────────────────────────────────

def _dates_of(evidence_ids, items: Mapping[str, Mapping]) -> list[str]:
    return [day for evidence in evidence_ids for day in ((items.get(evidence) or {}).get("published"),
                                                         (items.get(evidence) or {}).get("observed")) if day]


def compose(placed: list[tuple[Place, Claim]], groups: dict, kept: Mapping[int, dict], items: Mapping[str, Mapping],
            evidence: dict, checks: dict | None, removed: list[dict], coverage: dict, run: Mapping | None,
            subject: dict) -> dict:
    """The brief from the sentences the verifier kept, each section in order. A group whose sentences were all
    removed is left out. A development's date is the writer's when an item its sentences cite printed it, else the
    newest date those items printed, else undated; a voice's outlet and date are its item's own, and its who is kept
    only when the item's words name it; a question's lead is kept only when it states no number or date."""
    def sentences(section: str, group: int | None = None, part: str = "sentence") -> list[dict]:
        return [kept[index] for index, (place, _) in enumerate(placed)
                if index in kept and place == Place(section, group, part)]

    brief: dict = {"subject": subject, "headline": (sentences("headline") or [None])[0],
                   "picture": sentences("picture"), "bottom_line": sentences("bottom_line")}
    developments = []
    for index, group in enumerate(groups.get("developments", [])):
        said = sentences("developments", index)
        if not said:
            continue
        printed = _dates_of([evidence_id for sentence in said for evidence_id in sentence["evidence_ids"]], items)
        known = group["date_known"] and bool(printed)
        date = group["date"] if group["date"] in printed else max(printed, default=None)
        developments.append({"date": date if known else None, "date_known": known,
                             "label": None if known else UNDATED, "sentences": said})
    brief["developments"] = developments
    brief["by_site"] = [{"title": title[0], "sentences": sentences("by_site", index)}
                        for index, _ in enumerate(groups.get("by_site", []))
                        if (title := sentences("by_site", index, "title"))]
    voices = []
    for index, group in enumerate(groups.get("voices", [])):
        said = sentences("voices", index, "quote")
        if not said:
            continue
        claim = placed[said[0]["index"]][1]
        item = items.get(claim.quote.evidence_id) or {}
        who = group.get("who")
        named = isinstance(who, str) and who.strip() and all(
            part in (item.get("text") or "") for part in who.split(",")[0].split())
        voices.append({"quote": claim.quote.text, "who": who.strip() if named else None, "outlet": item.get("author"),
                       "date": item.get("published"), "url": item.get("url"), "sentence": said[0]})
    brief["voices"] = voices
    questions = []
    for index, group in enumerate(groups.get("questions", [])):
        said = sentences("questions", index, "question")
        if not said:
            continue
        lead = group.get("lead")
        lead = lead.strip() if isinstance(lead, str) and lead.strip() and not mentions(lead) else None
        questions.append({"lead": lead, "sentences": said})
    brief["questions"] = questions
    brief["could_not_see"] = sentences("could_not_see")
    brief.update({"evidence": evidence, "checks": checks, "removed": removed, "coverage": coverage, "run": run})
    return brief
