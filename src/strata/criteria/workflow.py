"""The check-your-criteria workflow (ticket 31): section 5 of the package workspace.

It is the third workflow in code, after ticket 15's plan-a-package (src/strata/packages/workflow.py) and ticket
29's review-proposed-lessons (src/strata/knowledge/lessons/writer.py), and like them it is plain Python steps:
the Microsoft Agent Framework package is not in the lockfile (a parked decision since ticket 15). Every tool
runs through the tool registry as the viewer (call_tool), and every step is announced as a step event.

- summary() is the section's collapsed state, read with the page: the comparable packages (find_comparables),
  how many published their qualification criteria (compare_criteria with no items), and the person's own saved
  runs, which show at once while the comparable packages and the records date are the same.
- package_run() is the part that needs no pasted text, started the first time the section opens: the rejected
  bids (rejected_bids), the cost estimate (compare_cost_estimates) and the lessons on cost estimates and
  specifications (get_lessons), each quote then checked by the verifier.
- compare() reads the pasted text with the criteria reader (one structured call to the drafting model,
  config/agents.toml, criteria_reader), compares each item with compare_criteria, and runs the verifier on each
  "I read this as ..." sentence against the person's own words (paste:{check_id}/{item_key}). The text is saved
  when the comparison starts, treated like an upload (strata.criteria.store). A request to judge a live tender's
  bids or a review decision comes back from the reader as a refusal key, and the app writes the words.

The verifier runs checks 1 to 3 here (strata.agent.verifier.check). Ticket 24 brings checks 4 to 6 to every
answer; until it lands, checks_run says which checks ran, and the check line says so.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import logging
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field

from strata.agent.claims import Claim, ClaimsError, Quote
from strata.agent.loop import AgentError, output_text
from strata.agent.verifier import Verdict, answer_events, check, find_quote, mentions
from strata.config import CriteriaItems, Thresholds, load_criteria_items
from strata.criteria.store import COMPARISON, PACKAGE_RUN, CriteriaStore
from strata.harness.facts import Facts
from strata.harness.turn import Event

log = logging.getLogger("strata.criteria")
FACTORS = ("cost_estimates", "designs_and_specifications")
# The refusal keys the reader may give (ticket 24's src/strata/agent/refusals.py names every key; these two are
# the ones this section's text can call for, the 31 brief, section 5.5).
REFUSALS = ("live_tenders", "review_decisions")
# Why a comparison could not run. web/src/copy.ts has one sentence for each, under criteria.errors.
COMPARE_ERRORS = ("no_reader", "agent_unavailable", "content_filter", "agent_output", "store", "data_service",
                  "internal")
PASSAGES = "strata.gold.passage"
ToolCall = Callable[[str, dict], dict]


class CompareError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class Package:
    """The package whose section this is: its key in the app state store, its STEP reference when it has a plan
    row, the find_comparables arguments that choose its comparables, and, for a package planned from a sentence,
    its cost estimate and description from its criteria."""

    key: str
    step_reference: str | None
    query: dict | None
    estimate_usd: float | None = None
    description: str | None = None


def step(name: str, status: str, **details) -> Event:
    return Event("step", {"id": name, "kind": name, "status": status, **details})


def limits(thresholds: Thresholds) -> dict:
    value = thresholds.value
    return {"max_chars": int(value("criteria.max_chars")), "counter_left": int(value("criteria.counter_left")),
            "rows_per_group": int(value("criteria.rows_per_group")),
            "lessons_per_group": int(value("criteria.lessons_per_group")),
            "min_comparables": int(value("past_range.min_comparables"))}


def labels(items: CriteriaItems) -> dict:
    """Each item's label and phrase from the item registry, for the screen."""
    return {item.key: {"label": item.label, "phrase": item.phrase} for item in items.items}


def comparables_of(call_tool: ToolCall, package: Package) -> tuple[dict, list[str]]:
    """find_comparables on the package's criteria. A planned package whose criteria choose no comparables yet has
    none."""
    if package.query is None:
        return {"rows": [], "abstention": {"reason": "no_comparables"}, "records_through": None, "as_of": None}, []
    found = call_tool("find_comparables", package.query)
    return found, [row["step_reference"] for row in found["rows"]]


def signature(refs: list[str], records_through: str | None) -> str:
    """Which comparable packages and records a run used, so a saved run shows only while they are the same."""
    text = ",".join(sorted(refs)) + "|" + (records_through or "")
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def state_of(found: dict) -> str:
    """not_measurable when section 1 cannot measure the package, no_comparables when nothing matched, else ok."""
    reason = (found.get("abstention") or {}).get("reason")
    if reason in ("unknown_package", "no_public_notice"):
        return "not_measurable"
    return "ok" if found["rows"] else "no_comparables"


def combine(*counts: dict | None) -> dict | None:
    """The check line's counts over the whole section: each run's verifier counts, added."""
    given = [entry for entry in counts if entry]
    if not given:
        return None
    total = {"checks_run": sorted({check for entry in given for check in entry["checks_run"]})}
    for key in ("sentences", "numbers", "dates", "quotes", "sources"):
        total[key] = {name: sum(entry[key][name] for entry in given) for name in given[0][key]}
    total["quotes_without_pages"] = sum(entry.get("quotes_without_pages", 0) for entry in given)
    return total


def _saved(store: CriteriaStore | None, owner_id: str, package: Package, kind: str):
    return store.latest(owner_id, package.key, kind) if store is not None and owner_id else None


# ── The collapsed summary ────────────────────────────────────────────────

def summary(call_tool: ToolCall, package: Package, store: CriteriaStore | None, owner_id: str,
            thresholds: Thresholds) -> dict:
    found, refs = comparables_of(call_tool, package)
    state = state_of(found)
    signed = signature(refs, found.get("records_through"))
    view = {"state": state, "comparables_total": len(refs), "public_criteria_count": 0, "public": [],
            "signature": signed, "records_through": found.get("records_through"), "limits": limits(thresholds),
            "comparison": None, "package_run": None, "section_checks": None, "public_sources": []}
    if state != "ok":
        return view
    criteria = call_tool("compare_criteria", {"comparables": ",".join(refs)})
    counts = criteria["summary"]["counts"]
    view |= {"public_criteria_count": counts["n"], "public": public_entries(criteria),
             "public_sources": [source["key"] for source in criteria["sources"]],
             "state": "ok" if counts["n"] else "none_public"}
    comparison, run = _saved(store, owner_id, package, COMPARISON), _saved(store, owner_id, package, PACKAGE_RUN)
    if comparison is not None:
        view["comparison"] = {"check_id": comparison.check_id, "status": comparison.status,
                              "pasted_text": comparison.pasted_text, "result": comparison.result,
                              "stale": comparison.comparables_signature != signed,
                              "compared_at": comparison.created_at.isoformat()}
    if run is not None and run.comparables_signature == signed and run.status == "ready":
        view["package_run"] = run.result
    view["section_checks"] = combine((view["package_run"] or {}).get("checks"),
                                     ((view["comparison"] or {}).get("result") or {}).get("checks"))
    return view


def public_entries(criteria: dict) -> list[dict]:
    """The packages whose criteria are public, newest notice first, each with the passage that opens it."""
    return [{"step_reference": row["step_reference"], "notice_id": row["notice_id"], "notice_date": row["notice_date"],
             "country_name": row["country_name"], "passage_id": row["requirements"][0]["passage_id"]}
            for row in criteria["rows"]]


# ── The package-level run ────────────────────────────────────────────────

def lesson_groups(call_tool: ToolCall, package: Package, per_group: int) -> list[dict]:
    """Lessons on cost estimates, then on specifications, each group in get_lessons' order (fit, then evidence,
    never use), at most per_group each; a lesson tagged with both shows once, under the first."""
    groups, shown = [], set()
    query = " ".join(word for word in (package.description or "", "cost estimates specifications") if word)
    for factor in FACTORS:
        found = call_tool("get_lessons", {"risk_factor": factor, "query": query})
        lessons = []
        for row in found["rows"]:
            if row["lesson_id"] in shown or len(lessons) >= per_group or not row["evidence"]:
                continue
            shown.add(row["lesson_id"])
            source = row["evidence"][0]
            lessons.append({"lesson_id": row["lesson_id"], "version": row["version"], "statement": row["statement"],
                            "ieg_status": row["ieg_status"], "evidence_id": row["evidence_id"],
                            "passage_evidence_id": source["evidence_id"], "passage_id": source["passage_id"],
                            "quote": source["quote"], "document_type": source["document_type"],
                            "doc_short": source["doc_short"], "project_id": source["project_id"],
                            "document_date": source["document_date"], "para": source["paragraph"],
                            "locator": source["locator"], "page": source["page"], "row": row})
        if lessons:
            groups.append({"factor": factor, "lessons": lessons})
    return groups


def _reason_claims(rejected: dict, facts: Facts) -> list[tuple[Claim, str]]:
    claims = []
    for row in rejected["rows"]:
        facts.record(row["evidence_id"], row, tool="rejected_bids")
        claims.append((Claim(f'"{row["reason"]["quote"]}"', "quote", (row["evidence_id"],)), row["evidence_id"]))
    return claims


def _lesson_claims(groups: list[dict], read_passage: Callable[[str], dict | None], facts: Facts) -> list[tuple[Claim, str]]:
    claims = []
    for group in groups:
        for lesson in group["lessons"]:
            facts.record(lesson["evidence_id"], lesson.pop("row"), tool="get_lessons")
            passage = read_passage(lesson["passage_id"])
            if passage is not None:
                facts.record(lesson["passage_evidence_id"], passage, tool="get_lessons")
            claims.append((Claim(f'"{lesson["quote"]}"', "quote", (lesson["evidence_id"], lesson["passage_evidence_id"]),
                                 quote=Quote(lesson["quote"], lesson["passage_evidence_id"])), lesson["evidence_id"]))
    return claims


def verdict_of(claims: list[tuple[Claim, str]], facts: Facts, tools: list[str]) -> tuple[dict, list[dict], set[str]]:
    """The verifier's counts over the claims, the removed sentences with their reasons, and the evidence ids of the
    rows whose sentence it removed. A quote from a record, such as an award notice's reason, has no page: the check
    line says such quotes are in their sources."""
    checked = [check(index, claim, facts) for index, (claim, _) in enumerate(claims)]
    verdict = Verdict(tuple(checked))
    counts, removed = None, []
    for event in answer_events(verdict, facts, tools):
        if event.type == "checks":
            counts = dict(event.data)
        elif event.type == "removed":
            removed.append({**event.data, "about": claims[event.data["index"]][1]})
    counts["quotes_without_pages"] = sum(1 for sentence in checked if sentence.quoted and sentence.claim.quote is None)
    return counts, removed, {entry["about"] for entry in removed}


async def package_run(call_tool: ToolCall, read_passage: Callable[[str], dict | None], package: Package,
                      store: CriteriaStore | None, owner_id: str, thresholds: Thresholds,
                      now: Callable[[], dt.datetime], new_check_id: Callable[[], str]) -> AsyncIterator[Event]:
    items, per = load_criteria_items(), limits(thresholds)
    yield step("notices", "running")
    found, refs = await asyncio.to_thread(comparables_of, call_tool, package)
    joined = ",".join(refs)
    yield step("notices", "done", count=len(refs))

    yield step("reasons", "running")
    rejected = await asyncio.to_thread(call_tool, "rejected_bids", {"comparables": joined})
    yield step("reasons", "done", count=rejected["summary"]["counts"]["n"])

    yield step("cost", "running")
    asked = {"comparables": joined}
    if package.step_reference:
        asked["step_reference"] = package.step_reference
    elif package.estimate_usd is not None:
        asked["estimate_usd"] = package.estimate_usd
    cost = await asyncio.to_thread(call_tool, "compare_cost_estimates", asked)
    yield step("cost", "done", count=cost["summary"]["counts"]["m"])

    yield step("lessons", "running")
    groups = await asyncio.to_thread(lesson_groups, call_tool, package, per["lessons_per_group"])
    yield step("lessons", "done", count=sum(len(group["lessons"]) for group in groups))

    yield step("checks", "running")
    facts = Facts()
    claims = _reason_claims(rejected, facts) + await asyncio.to_thread(_lesson_claims, groups, read_passage, facts)
    counts, removed, removed_ids = verdict_of(claims, facts, ["rejected_bids", "get_lessons"])
    yield step("checks", "done")

    signed = signature(refs, found.get("records_through"))
    names = labels(items)
    reject_state = ("no_comparables" if not refs else "no_award_notices" if not rejected["summary"]["counts"]["m"]
                    else "none_rejected" if not rejected["summary"]["counts"]["n"] else "ok")
    result = {
        "check_id": new_check_id(), "signature": signed, "records_through": found.get("records_through"),
        "as_of": found["as_of"], "labels": names,
        "rejected": {"state": reject_state, "counts": rejected["summary"]["counts"],
                     "groups": [{**group, **names[group["item_key"]]} for group in rejected["summary"]["groups"]],
                     "rows": [{**row, "removed": row["evidence_id"] in removed_ids} for row in rejected["rows"]],
                     "sources": rejected["sources"], "records_through": rejected["records_through"]},
        "cost": {key: cost[key] for key in ("rows", "coverage", "package", "counts", "band", "quartiles",
                                            "quantile_dots", "min_comparables", "sources", "records_through",
                                            "abstention", "as_of")},
        "lessons": {"state": "ok" if groups else "none",
                    "groups": [{"factor": group["factor"],
                                "lessons": [{**lesson, "removed": lesson["evidence_id"] in removed_ids}
                                            for lesson in group["lessons"]]} for group in groups]},
        "checks": counts, "removed": removed,
    }
    if store is not None and owner_id:
        try:
            await asyncio.to_thread(store.save, result["check_id"], owner_id, package.key, PACKAGE_RUN, "ready", now(),
                                    result=result, signature=signed,
                                    records_through=_day(found.get("records_through")))
        except Exception:  # a run the store could not keep still shows; it runs again the next time
            log.exception("I could not keep the package-level run of %s.", package.key)
    comparison = _saved(store, owner_id, package, COMPARISON) if store is not None and owner_id else None
    other = comparison.result.get("checks") if comparison is not None and comparison.result and \
        comparison.comparables_signature == signed else None
    yield Event("package_run", {**result, "section_checks": combine(counts, other)})


def _day(value) -> dt.date | None:
    return dt.date.fromisoformat(str(value)[:10]) if value else None


# ── Comparing your criteria ──────────────────────────────────────────────

@dataclass
class Reading:
    refusal: dict | None
    items: list[dict] = field(default_factory=list)
    unplaced: list[str] = field(default_factory=list)


def message(text: str, items: CriteriaItems) -> dict:
    """What the reader is sent: data only, since its rules live in its instructions."""
    return {"task": "read_criteria", "text": text,
            "items": [{"key": item.key, "phrase": item.phrase, "parts": list(item.parts)} for item in items.criteria]}


def _numbers_in(text: str) -> set:
    return {mention.value for mention in mentions(text) if mention.kind == "number"}


def read_answer(answer_text: str, text: str, items: CriteriaItems) -> Reading:
    """The reader's answer, checked against the person's text and the item registry: each item a criterion key,
    once, whose excerpt is word for word in the text and whose parts state only numbers the excerpt states; each
    unplaced part word for word in the text; a refusal only with a key this section can call for. ClaimsError when
    it is not the JSON its instructions ask for."""
    try:
        answer = json.loads(answer_text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ClaimsError(f"The criteria reader's answer is not JSON: {error}.") from error
    if not isinstance(answer, dict) or not isinstance(answer.get("items", []), list):
        raise ClaimsError("The criteria reader's answer must be an object with a list of items.")
    refusal = answer.get("refusal")
    if refusal is not None:
        if not isinstance(refusal, dict) or refusal.get("key") not in REFUSALS:
            raise ClaimsError(f"The criteria reader refused with {refusal!r}, which this section cannot give.")
        refusal = {"key": refusal["key"], "partial": bool(refusal.get("partial"))}
        if not refusal["partial"]:
            return Reading(refusal)
    kept, seen = [], set()
    for entry in answer.get("items") or []:
        key = entry.get("item_key") if isinstance(entry, dict) else None
        if not isinstance(key, str) or not items.has(key) or not items.item(key).is_criterion or key in seen:
            log.info("The criteria reader gave an item the registry does not take: %r.", key)
            continue
        excerpt = str(entry.get("excerpt") or "").strip()
        if not excerpt or find_quote(excerpt, text) is None:
            log.info("The criteria reader's words for %s are not in the text; I left the item out.", key)
            continue
        seen.add(key)
        stated = _numbers_in(excerpt)
        parts = {}
        for part, value in (entry.get("parts") or {}).items():
            if part not in items.item(key).parts or value is None:
                continue
            number = value.get("value") if isinstance(value, dict) else value
            written = _written(number, stated)
            if written is None:
                log.info("The criteria reader gave %s's %s a number its words do not state; I left it out.", key, part)
                continue
            parts[part] = ({"value": str(number), "currency": str(value.get("currency") or "USD").upper()}
                           if part == "amount" else int(number))
        kept.append({"item_key": key, "excerpt": excerpt, "reading": str(entry.get("reading") or "").strip() or None,
                     "parts": parts})
    unplaced = [str(part).strip() for part in answer.get("unplaced") or []
                if str(part).strip() and find_quote(str(part).strip(), text) is not None]
    return Reading(refusal, kept, unplaced)


def _written(number, stated: set):
    """The number if the excerpt states it, as written or in millions or thousands ("US$10 million" states 10 and
    10,000,000), else None."""
    from decimal import Decimal, InvalidOperation

    try:
        value = Decimal(str(number))
    except (InvalidOperation, TypeError):
        return None
    if value <= 0:
        return None
    for scale in (1, 1000, 1_000_000, 1_000_000_000):
        if value / scale in stated:
            return number
    return None


def shortened(excerpt: str, most: int) -> dict:
    """Your words for one item, cut at a word end past most characters, with "…" where they were cut."""
    if len(excerpt) <= most:
        return {"text": excerpt, "shortened": False}
    cut = excerpt[:most].rsplit(" ", 1)[0].rstrip(",;:")
    return {"text": cut + "…", "shortened": True}


async def compare(call_tool: ToolCall, reader_for: Callable[[], object | None], package: Package, text: str,
                  store: CriteriaStore, owner_id: str, thresholds: Thresholds, now: Callable[[], dt.datetime],
                  new_check_id: Callable[[], str]) -> AsyncIterator[Event]:
    """One comparison of the person's qualification criteria, as events. A step that cannot run raises
    CompareError with its code, after the text was saved."""
    items, per = load_criteria_items(), limits(thresholds)
    check_id, started = new_check_id(), now()
    try:
        await asyncio.to_thread(store.save, check_id, owner_id, package.key, COMPARISON, "running", started,
                                pasted_text=text)
    except Exception as error:
        raise CompareError("store") from error
    yield Event("saved", {"check_id": check_id})

    yield step("read", "running")
    agent = reader_for()
    if agent is None:
        raise CompareError("no_reader")
    try:
        response = await asyncio.to_thread(agent.respond, [{"role": "user", "content": json.dumps(
            message(text, items), ensure_ascii=False)}], None)
        reading = read_answer(output_text(response), text, items)
    except AgentError as error:
        raise CompareError(error.code if error.code in COMPARE_ERRORS else "agent_unavailable") from error
    except ClaimsError as error:
        log.warning("The criteria reader answered check %s in a shape I can't read: %s", check_id, error)
        raise CompareError("agent_output") from error
    yield step("read", "done", count=len(reading.items))

    found, refs = await asyncio.to_thread(comparables_of, call_tool, package)
    signed = signature(refs, found.get("records_through"))
    base = {"check_id": check_id, "compared_at": started.isoformat(), "signature": signed,
            "records_through": found.get("records_through"), "as_of": found["as_of"], "refusal": reading.refusal,
            "content_filtered": False, "items": [], "unplaced": reading.unplaced, "fx_count": 0, "coverage": None,
            "sources": [], "checks": None, "removed": []}
    if reading.refusal and not reading.refusal["partial"]:
        result = {**base, "unplaced": []}
        await _keep(store, check_id, owner_id, package, "refused", now(), text, result, signed, found)
        yield Event("comparison", {**result, "section_checks": _with_run(store, owner_id, package, None, signed)})
        return

    yield step("find", "running")
    yours = [{"item_key": item["item_key"], "parts": item["parts"]} for item in reading.items]
    criteria = await asyncio.to_thread(call_tool, "compare_criteria", {"comparables": ",".join(refs),
                                                                       "items": json.dumps(yours)}) if refs else None
    yield step("find", "done", count=criteria["summary"]["counts"]["n"] if criteria else 0)

    yield step("compare", "running")
    rejected = await asyncio.to_thread(call_tool, "rejected_bids", {"comparables": ",".join(refs)}) if refs else None
    groups = {group["item_key"]: group["count"] for group in (rejected["summary"]["groups"] if rejected else [])}
    counted = {entry["item_key"]: entry for entry in (criteria["summary"]["items"] if criteria else [])}
    names = labels(items)
    shown = []
    for item in reading.items:
        counts = counted.get(item["item_key"], {})
        notices = []
        for row in (criteria["rows"] if criteria else []):
            relation = row["relations"].get(item["item_key"])
            if relation is None:
                continue
            requirement = next(entry for entry in row["requirements"]
                               if entry["item_key"] == item["item_key"] and entry["compared"])
            notices.append({"step_reference": row["step_reference"], "country_name": row["country_name"],
                            "notice_id": row["notice_id"], "notice_date": row["notice_date"], "relation": relation,
                            "requirement": {"text": requirement["requirement"]["text"],
                                            "lang": requirement["language"] or "en",
                                            "start": requirement["requirement"]["start"],
                                            "end": requirement["requirement"]["end"]},
                            "passage_id": requirement["passage_id"]})
        shown.append({"item_key": item["item_key"], **names[item["item_key"]],
                      "your_excerpt": shortened(item["excerpt"], int(thresholds.value("criteria.excerpt_max_chars"))),
                      "reading": item["reading"], "parts": item["parts"],
                      **{key: counts.get(key, 0) for key in ("stated", "compared", "less", "same", "more", "different",
                                                             "same_or_less", "not_stated")},
                      "rejected_packages": groups.get(item["item_key"], 0), "notices": notices})
    yield step("compare", "done", count=len(shown))

    yield step("checks", "running")
    facts, claims = Facts(), []
    for item in reading.items:
        if item["reading"] is None:
            continue
        evidence = f"paste:{check_id}/{item['item_key']}"
        facts.record(evidence, {"excerpt": item["excerpt"], "numbers": sorted(str(n) for n in _numbers_in(item["excerpt"]))},
                     tool="criteria_reader")
        claims.append((Claim(item["reading"], "summary", (evidence,)), item["item_key"]))
    counts, removed, removed_keys = verdict_of(claims, facts, ["compare_criteria"]) if claims else (None, [], set())
    for entry in shown:
        entry["reading_removed"] = entry["item_key"] in removed_keys
    yield step("checks", "done")

    criteria_counts = criteria["summary"]["counts"] if criteria else {"n": 0, "total": 0, "open": 0, "missing": 0}
    result = {**base, "items": shown,
              "coverage": {key: criteria_counts.get(key, 0) for key in ("n", "total", "open", "missing")},
              "sources": criteria["sources"] if criteria else [], "checks": counts, "removed": removed}
    await _keep(store, check_id, owner_id, package, "ready", now(), text, result, signed, found)
    yield Event("comparison", {**result, "section_checks": _with_run(store, owner_id, package, counts, signed)})


def _with_run(store: CriteriaStore, owner_id: str, package: Package, counts: dict | None, signed: str) -> dict | None:
    run = store.latest(owner_id, package.key, PACKAGE_RUN)
    other = run.result.get("checks") if run is not None and run.result and run.comparables_signature == signed else None
    return combine(counts, other)


async def _keep(store: CriteriaStore, check_id: str, owner_id: str, package: Package, status: str, at: dt.datetime,
                text: str, result: dict, signed: str, found: dict) -> None:
    try:
        await asyncio.to_thread(store.save, check_id, owner_id, package.key, COMPARISON, status, at, pasted_text=text,
                                result=result, signature=signed, records_through=_day(found.get("records_through")))
    except Exception as error:
        raise CompareError("store") from error
