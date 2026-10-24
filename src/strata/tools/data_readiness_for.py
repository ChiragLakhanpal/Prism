"""data_readiness_for: how fit each source is to support answers, from the measures in strata.ops.

The tool registry (config/tools.toml) defines its parameters and result shape; this module is its
adapter. The Data readiness page (the 16 design brief), the agent and the dashboard's headline all
call it, so they say the same thing for the same date. It reads three things:

- the latest row of each source, subject and measure in strata.ops.data_readiness that was public
  on or before the as-of date (the newest measured_at; never a sum or an average over runs), and
  the Procurement Plan pages the layout parser could not read (strata.ops.parse_failures);
- the source registry (config/sources.toml): each source's readiness rows, the measure behind each
  cell, its known gaps, the limits it declares and the fixes that would close its gaps;
- the tool registry's kinds of question (config/tools.toml, [tools.<name>.readiness]).

A row of the Sources table shows a source as a whole: its row for every country (subject all) when
the source has one, or else the sum of its subjects' latest rows, such as the documents source's
projects. A sum is a column the tool returns, so the page computes nothing (CLAUDE.md rule 1).

What it decides, with its thresholds in config/thresholds.toml's [data_readiness] (CLAUDE.md rule 9):

- A cell is Partial when its linked or read-well share is under the threshold, when its source's
  latest fetch is older than its cadence allows (late), or when the registry declares a limit on it.
  A cell with no rows is a Gap, and so is each known gap. Nothing else gets a status, and there is
  no composite score.
- Each gap counts the projects its fix would add evidence to, from a measure the registry names.
  Gaps and fixes are ranked by that count, highest first, ties in registry order; a gap with no
  count ranks last, and a fix with no count does not appear.
- A kind of question is a Gap when its "Ready for" measure is missing or zero, Partial when any row
  it draws on has a gap, and ready otherwise. The headline counts the kinds by status and names the
  two biggest gaps. Its words are copy.dataReadiness.server in web/src/copy.ts, read from
  data_readiness_copy.json beside this file; no model writes them.

Every sentence comes back as segments: text, and numbers with the row they come from, so the page
can put each number in Num. The headline also comes back as plain text, for the dashboard.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from functools import cache
from importlib import resources

from strata.config import (AS_PUBLISHED, EVERY_COUNTRY, READINESS_COLUMNS, SLICE_COUNTRIES, Fix, ReadinessColumn,
                           ReadinessRow, Source, load_sources, load_tools)
from strata.tools.registry import Call, ToolContractError

ALL = "all"  # the subject of a source's measure for every country
PLANS = "plans"  # the readiness row of the plan reader, whose layout parser's failures the page lists
PROJECT = re.compile(r"P\d{6}")
SHARES = {"linked": "linked_min_share", "read_well": "read_well_min_share"}
TABLE = "strata.ops.data_readiness"
Segments = list[dict]


@cache
def words() -> dict:
    """copy.dataReadiness.server, with copy.num.words, as web/lint/server-copy.ts copied it."""
    return json.loads((resources.files("strata.tools") / "data_readiness_copy.json").read_text())


def _sql(name: str) -> str:
    return (resources.files("strata.tools") / "sql" / "data_readiness_for" / name).read_text()


def _rows(call: Call, name: str, **params) -> list[dict]:
    result = call.engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


# Values arrive typed from DuckDB and as text from the SQL warehouse, so each is read once here.

def _date(value) -> dt.date | None:
    if value is None or value == "":
        return None
    return value if isinstance(value, dt.date) else dt.date.fromisoformat(str(value)[:10])


def _whole(value) -> int | None:
    return None if value is None or value == "" else int(value)


def _iso(value: dt.date | None) -> str | None:
    return value.isoformat() if value else None


# ── Sentences ────────────────────────────────────────────────────────────

def _count_text(number: int) -> str:
    """DESIGN.md section 7, rule 12: one to nine in words, numerals from 10, as Num writes them."""
    return words()["words"][number - 1] if 1 <= number <= 9 else f"{number:,}"


def _date_text(day: dt.date, today: dt.date) -> str:
    """A date in a sentence: "October 23", with the year when it is not the as-of date's."""
    month = words()["months"][day.month - 1]
    return f"{month} {day.day}" if day.year == today.year else f"{month} {day.day}, {day.year}"


def number(value: int, row: int | None = None, noun: str | None = None, role: str | None = None,
           noun_one: str | None = None, lack: str | None = None) -> dict:
    """A number in a sentence: the result row it comes from, what it counts (plural, and singular for
    a one), and, when it is neither that row's count nor its denominator, what it is (missing, a
    shortfall; days, how late), so its window can show it above the measure's own numbers. A
    shortfall also says what its records lack, so its tooltip can name them."""
    return {"number": value, "row": row, "noun": noun, "noun_one": noun_one, "role": role, "lack": lack}


def fill(template: str, slots: dict) -> Segments:
    """A template with each {slot} replaced by text or by segments."""
    out: Segments = []
    for index, part in enumerate(re.split(r"\{(\w+)\}", template)):
        if index % 2 == 0:
            if part:
                out.append({"text": part})
            continue
        value = slots[part]
        out.extend(value if isinstance(value, list) else [value] if isinstance(value, dict) else [{"text": str(value)}])
    return out


def text_of(segments: Segments) -> str:
    """Segments as plain text, with each number written as Num writes it in a sentence."""
    return "".join(segment["text"] if "text" in segment else _count_text(segment["number"]) for segment in segments)


def _joined(parts: list[Segments]) -> Segments:
    out: Segments = []
    for index, part in enumerate(parts):
        if index:
            out.append({"text": words()["clauseLastJoin"] if index == len(parts) - 1 else words()["clauseJoin"]})
        out.extend(part)
    return out


# ── The measures behind the page ─────────────────────────────────────────

@dataclass
class Measures:
    """The latest rows, by source and measure, and the rows the result has used so far."""

    latest: dict[tuple[str, str], list[dict]]
    rows: list[dict] = field(default_factory=list)
    index: dict[tuple[str, str], int] = field(default_factory=dict)

    def use(self, source: str, measure: str, counted_in: str | None = None, newest: bool = False) -> int | None:
        """The result row for one measure of a source, added the first time it is used, or None when
        the measure has no row. A freshness date summed over subjects is the stalest of them, or the
        newest for a source whose documents arrive as they are published."""
        key = (source, measure)
        if key in self.index:
            return self.index[key]
        found = self.latest.get(key)
        if not found:
            return None
        whole = [row for row in found if row["subject"] == ALL]
        chosen = whole or sorted(found, key=lambda row: row["subject"])
        counts = [_whole(row["count"]) for row in chosen]
        denominators = [_whole(row["denominator"]) for row in chosen]
        count = None if None in counts else sum(counts)
        denominator = None if None in denominators else sum(denominators)
        days = [_date(row["as_of"]) for row in chosen if row["as_of"] not in (None, "")]
        as_of = (max(days) if newest else min(days)) if days else None
        subjects = [row["subject"] for row in chosen]
        measured_on = max(_date(row["measured_on"]) for row in chosen)
        self.rows.append({
            "evidence_id": f"{TABLE}:{source}/{'+'.join(subjects)}/{measure}",
            "public_from": max(_date(row["public_from"]) for row in chosen).isoformat(),
            "source": {"table": TABLE, "source_key": source, "measure": measure, "subjects": subjects,
                       "measured_on": measured_on.isoformat(), "counted_in": counted_in},
            "source_key": source,
            "measure": measure,
            "kind": chosen[0]["kind"],
            "subjects": subjects,
            "count": count,
            "denominator": denominator,
            # share_percent, share_bound, in_ten and in_ten_exact: filled by the caller, which knows
            # the thresholds (share)
            **share(None, None, 0, 0),
            "as_of": _iso(as_of),
            "measured_on": measured_on.isoformat(),
            "run_ids": sorted({row["run_id"] for row in chosen}),
        })
        self.index[key] = len(self.rows) - 1
        return self.index[key]

    def subjects_short(self, source: str, measure: str) -> int:
        """How many of a measure's subjects that are project IDs fall short of their denominator."""
        return sum(1 for row in self.latest.get((source, measure), [])
                   if PROJECT.fullmatch(row["subject"]) and (_whole(row["count"]) or 0) < (_whole(row["denominator"]) or 0))


def _rounded(count: int, denominator: int, scale: int) -> int:
    return int((Decimal(count) * scale / Decimal(denominator)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def share(count: int | None, denominator: int | None, fewest_in_ten: int, fewest_percent: int) -> dict:
    """A share as DESIGN.md section 7 writes it (rules 6, 11 and 15), worked out here once, rounded
    half up, so neither the page nor the dashboard divides (CLAUDE.md rule 1):

    - share_percent, the whole percent, from fewest_percent rows, for the page and the dashboard's
      charts, 0 and 100 included;
    - in_ten, "about N in 10", with in_ten_exact when it is exact, from fewest_in_ten rows up to
      fewest_percent, for a part strictly between none and all (the count says the rest);
    - share_bound, "under" or "over", when a part strictly between none and all rounds to the end of
      its scale, so it reads "<1%" or "more than 9 in 10", never 0 or 100 for a part.
    Under fewest_in_ten rows, none of them: the cell shows the count alone."""
    out = {"share_percent": None, "share_bound": None, "in_ten": None, "in_ten_exact": None}
    if count is None or not denominator or denominator < fewest_in_ten:
        return out
    part = 0 < count < denominator
    if denominator >= fewest_percent:
        out["share_percent"] = _rounded(count, denominator, 100)
        top = 100
    elif part:
        out["in_ten"], out["in_ten_exact"] = _rounded(count, denominator, 10), count * 10 % denominator == 0
        top = 10
    else:
        return out
    rounded = out["share_percent"] if out["share_percent"] is not None else out["in_ten"]
    if part and rounded in (0, top):
        out["share_bound"] = "under" if rounded == 0 else "over"
    return out


# ── The page ─────────────────────────────────────────────────────────────

@dataclass
class Gap:
    """One gap, with its words twice: as a phrase in the headline (copy's server.gap) and as a full
    sentence under "What holds it back" (server.holds), both filled from the same slots."""

    id: str
    type: str  # published, no_rows, declared, linked, read_well, late or check
    status: str  # gap or partial
    row_id: str
    source_key: str
    column: str | None
    words: str  # the key of its templates in server.gap and server.holds
    slots: dict
    measure: str | None = None
    projects: int | None = None
    order: int = 0
    form: str = ""  # for a shortfall: One, All or Only (shortfall_form), when copy has that form

    def _template(self, kind: str) -> str:
        found = words()[kind]
        return found.get(self.words + self.form, found[self.words])

    @property
    def phrase(self) -> Segments:
        return fill(self._template("gap"), self.slots)

    @property
    def holds(self) -> Segments:
        return fill(self._template("holds"), self.slots)

    def as_dict(self) -> dict:
        return {"id": self.id, "type": self.type, "status": self.status, "row_id": self.row_id,
                "source_key": self.source_key, "column": self.column, "projects": self.projects,
                "phrase": self.phrase}


@dataclass
class Page:
    call: Call
    sources: dict[str, Source]
    measures: Measures
    gaps: list[Gap] = field(default_factory=list)

    def value(self, name: str):
        return self.call.thresholds.value(f"data_readiness.{name}")

    def row_ref(self, source: Source, column: ReadinessColumn, newest: bool = False) -> int | None:
        return self.shared(self.measures.use(source.key, column.measure, column.counted_in, newest))

    def shared(self, index: int | None) -> int | None:
        """A result row with its share filled in, by the thresholds file's rules."""
        if index is not None:
            row = self.measures.rows[index]
            row.update(share(row["count"], row["denominator"], int(self.value("fewest_for_a_share")),
                             int(self.value("fewest_for_a_percentage"))))
        return index

    def gap(self, **fields) -> Gap:
        found = Gap(order=len(self.gaps), **fields)
        self.gaps.append(found)
        return found

    def short(self, index: int | None, threshold: str) -> bool:
        if index is None:
            return False
        row = self.measures.rows[index]
        if row["count"] is None or not row["denominator"]:
            return False
        return Decimal(row["count"]) / Decimal(row["denominator"]) < Decimal(str(self.value(threshold)))

    def shortfall(self, index: int, column: ReadinessColumn) -> dict:
        row = self.measures.rows[index]
        return {"missing": number(row["denominator"] - row["count"], index, column.noun, "missing", column.noun_one,
                                  column.lack),
                "total": number(row["denominator"], index, column.noun, noun_one=column.noun_one),
                "noun": column.noun_one if row["denominator"] == 1 and column.noun_one else column.noun,
                "lack": column.lack or ""}

    def shortfall_form(self, index: int) -> str:
        """Which form of a shortfall's words agrees with its numbers: Only when the one record falls
        short, All when every record does, One when one of several does, else the plain form."""
        row = self.measures.rows[index]
        missing, total = row["denominator"] - row["count"], row["denominator"]
        return "Only" if missing == total == 1 else "All" if missing == total else "One" if missing == 1 else ""

    def late_days(self, source: Source, schedule: str, as_of: dt.date | None) -> int | None:
        if as_of is None or schedule in ("frozen", AS_PUBLISHED):
            return None
        allowed = int(self.value("schedule_days")[schedule])
        age = (self.call.as_of - as_of).days
        return age - allowed if age >= allowed + int(self.value("late_grace_days")) else None

    def cell(self, source: Source, row: ReadinessRow, name: str) -> dict:
        column: ReadinessColumn | None = getattr(row, name)
        declared = [limit for limit in source.declared if limit.row == row.id and limit.column == name]
        if column is None:
            if name == "read_well" and source.paged:
                return {"published_as_table": True}
            # No measure, and none to wait for; a row whose documents arrive as published says so.
            return {"measure": None, "row": None, **({"schedule": row.schedule} if name == "fresh" else {})}
        schedule = row.schedule or source.cadence
        index = self.row_ref(source, column, newest=schedule == AS_PUBLISHED)
        cell = {"measure": column.measure, "row": index, "counts": column.counts, "counts_one": column.counts_one,
                "noun": column.noun, "noun_one": column.noun_one, "status": None, "note": None}
        if name == "coverage" and column.years:
            cell["years_row"] = self.row_ref(source, ReadinessColumn(column.years, "", "", column.counted_in))
        if name == "fresh":
            cell["schedule"] = schedule
            cell["late_days"] = None
        if index is None:
            return cell
        measured = self.measures.rows[index]
        base = {"row_id": row.id, "source_key": source.key, "column": name, "measure": column.measure}
        if name == "coverage" and measured["count"] == 0:
            cell["status"] = "gap"
            self.gap(id=f"{row.id}/{name}", type="no_rows", status="gap", words="noRows",
                     slots={"sourceNoun": row.noun}, **base)
        elif name in SHARES and self.short(index, SHARES[name]):
            cell["status"] = "partial"
            self.gap(id=f"{row.id}/{name}", type=name, status="partial",
                     words="linked" if name == "linked" else "readWell", slots=self.shortfall(index, column),
                     form=self.shortfall_form(index), **base)
        elif name == "fresh":
            late = self.late_days(source, schedule, _date(measured["as_of"]))
            if late is not None:
                cell["status"], cell["late_days"] = "partial", late
                fetched = _date(measured["as_of"])
                self.gap(id=f"{row.id}/{name}", type="late", status="partial",
                         words="lateOneDay" if late == 1 else "late", slots={
                             "sourceNoun": row.noun, "date": _date_text(fetched, self.call.as_of),
                             "days": number(late, index, words()["daysLate"], "days", words()["dayLate"]),
                             "schedule": words()["schedules"][schedule]}, **base)
        if declared and cell["status"] is None:
            cell["status"], cell["note"] = "partial", declared[0].note
            self.gap(id=f"{row.id}/{name}/declared", type="declared", status="partial", words="declared",
                     slots={"sourceNoun": row.noun, "note": declared[0].note}, **base)
        return cell

    def checks(self, source: Source, row: ReadinessRow) -> None:
        for check in row.checks:
            index = self.row_ref(source, check)
            if index is not None and self.short(index, "check_min_share"):
                self.gap(id=f"{row.id}/{check.measure}", type="check", status="partial", row_id=row.id,
                         source_key=source.key, column=None, measure=check.measure, words="check",
                         slots=self.shortfall(index, check), form=self.shortfall_form(index))

    def scope(self, source: Source, row: ReadinessRow, cells: dict) -> dict:
        if source.scope == EVERY_COUNTRY:
            return {"kind": "every_country"}
        if source.scope == SLICE_COUNTRIES:
            return {"kind": "countries", "names": [country.name for country in source.countries]}
        subjects = {subject for cell in cells.values() if cell.get("row") is not None
                    for subject in self.measures.rows[cell["row"]]["subjects"] if PROJECT.fullmatch(subject)}
        return {"kind": "projects", "count": len(subjects)}

    def source_rows(self, keys: list[str]) -> list[dict]:
        out = []
        for key in keys:
            source = self.sources[key]
            for row in source.readiness:
                cells = {name: self.cell(source, row, name) for name in READINESS_COLUMNS}
                self.checks(source, row)
                measured = any(cell.get("row") is not None for cell in cells.values())
                out.append({"type": "measured" if measured else "unmeasured", "id": row.id, "source_key": key,
                            "label": row.label, "stratum": row.stratum, "scope": self.scope(source, row, cells),
                            "covers": row.covers, "cells": cells})
            for known in source.known_gaps:
                out.append({"type": "gap", "id": known.id, "source_key": key, "label": known.label,
                            "first_fiscal_year": known.first_fiscal_year, "last_fiscal_year": known.last_fiscal_year,
                            "note": known.note})
                self.gap(id=known.id, type="published", status="gap", row_id=source.readiness[0].id, source_key=key,
                         column=None, words="published", slots={
                             "sourceNoun": known.noun, "fromYear": known.first_fiscal_year,
                             "toYear": known.last_fiscal_year})
        return out

    def fix_for(self, found: Gap) -> Fix | None:
        """The registry's fix for a gap: the one that names its known gap, or the one on its measure."""
        return next((fix for fix in self.sources[found.source_key].fixes
                     if (fix.gap == found.id if found.type == "published"
                         else fix.gap is None and fix.measure == found.measure)), None)

    def noun(self, source: Source, measure: str) -> tuple[str | None, str | None, str | None]:
        """What a measure of a source counts, plural and singular, and what a record that falls short
        lacks, from the column that shows it."""
        for row in source.readiness:
            for column in (*(getattr(row, name) for name in READINESS_COLUMNS), *row.checks):
                if column and column.measure == measure:
                    return column.noun, column.noun_one, column.lack
        return None, None, None

    def routes(self, in_view: set[str]) -> list[dict]:
        """Each reading route of the rows in view, with the result row of the pages it read well."""
        out = []
        for source in self.sources.values():
            for row in source.readiness:
                for route in row.routes if row.id in in_view else ():
                    index = self.shared(self.measures.use(source.key, route.measure, route.counted_in))
                    if index is not None:
                        out.append({"measure": route.measure, "label": route.label, "noun": route.noun,
                                    "row": index})
        return out

    def rank(self) -> list[Gap]:
        """Gaps by the projects their fix would add evidence to, highest first, ties in registry order."""
        for found in self.gaps:
            source = self.sources[found.source_key]
            fix = self.fix_for(found)
            if fix is None:
                continue
            if fix.projects:
                index = self.measures.use(source.key, fix.projects, fix.projects_counted_in)
                found.projects = None if index is None else self.measures.rows[index]["count"]
            else:
                found.projects = self.measures.subjects_short(source.key, fix.measure)
        return sorted(self.gaps, key=lambda found: (found.projects is None, -(found.projects or 0), found.order))

    def fixes(self, ranked: list[Gap]) -> list[dict]:
        out = []
        for found in ranked:
            source = self.sources[found.source_key]
            fix = self.fix_for(found)
            if fix is None or not found.projects:
                continue
            index = self.measures.use(source.key, fix.measure, fix.counted_in)
            if index is None or not self.measures.rows[index]["count"] and found.type == "published":
                continue
            row = self.measures.rows[index]
            count, denominator = row["count"] or 0, row["denominator"] or 0
            noun, noun_one, lack = (fix.noun, None, None) if fix.noun else self.noun(source, fix.measure)
            known = next((gap for gap in source.known_gaps if gap.id == fix.gap), None)
            slots = {"count": number(count, index, noun, noun_one=noun_one),
                     "denominator": number(denominator, index, noun, noun_one=noun_one),
                     "missing": number(denominator - count, index, noun, "missing", noun_one, lack),
                     "fromYear": known.first_fiscal_year if known else "", "toYear": known.last_fiscal_year if known else ""}
            # Projects counted by a measure open it; projects counted as the measure's subjects that
            # fall short have no row of their own.
            out.append({"rank": len(out) + 1, "gap": found.id, "projects": found.projects, "row": index,
                        "projects_row": self.measures.use(source.key, fix.projects, fix.projects_counted_in)
                        if fix.projects else None,
                        "projects_from": "measure" if fix.projects else "subjects",
                        "sentence": fill(fix.sentence, slots)})
        return out


def _kinds(page: Page, ranked: list[Gap], in_view: set[str], from_tool: str | None) -> list[dict]:
    """Each kind of question in view, with its status from every gap in the rows it draws on, even
    rows a filtered view leaves out, so a kind is never called ready because its gaps are hidden.
    Opened from a tool that answers a kind, the view shows that kind alone."""
    out = []
    for tool in load_tools().values():
        if tool.readiness is None:
            continue
        kind = tool.readiness
        if (from_tool != tool.name) if from_tool in _kind_tools() else not set(kind.draws_on) & in_view:
            continue
        source = next((key for key, found in page.sources.items()
                       if kind.ready_for_row in {row.id for row in found.readiness}), None)
        if source is None:
            raise ToolContractError(f"The tool {tool.name}'s readiness names the row {kind.ready_for_row!r}, which "
                                    "no source in config/sources.toml has.")
        ready_for = page.measures.use(source, kind.ready_for_measure)
        mine = [found for found in ranked if found.row_id in kind.draws_on]
        if ready_for is None or not page.measures.rows[ready_for]["count"]:
            status = "gap"
        else:
            status = "partial" if mine else "ready"
        held = [found.holds for found in mine[:2]]
        more = len(mine) - len(held)
        if more == 1:
            held.append([{"text": words()["moreOne"]}])
        elif more > 1:
            held.append(fill(words()["more"], {"n": number(more)}))
        if not mine:
            held.append([{"text": words()["nothingHolds"]}])
        out.append({"kind": kind.kind, "tool": tool.name, "status": status, "ready_for": ready_for,
                    "holds_back": held})
    return out


def _kind_tools() -> set[str]:
    return {name for name, tool in load_tools().items() if tool.readiness}


def _gaps_sentence(ranked: list[Gap]) -> Segments:
    if not ranked:
        return [{"text": words()["gapsNone"]}]
    if len(ranked) == 1:
        return fill(words()["gapsOne"], {"gap1": ranked[0].phrase})
    return fill(words()["gapsTwo"], {"gap1": ranked[0].phrase, "gap2": ranked[1].phrase})


def _kinds_sentence(kinds: list[dict]) -> Segments:
    total = len(kinds)
    count = {status: sum(1 for kind in kinds if kind["status"] == status) for status in ("ready", "partial", "gap")}
    if total == 1:
        clause = {"ready": "oneFull", "partial": "onePart", "gap": "oneNone"}[kinds[0]["status"]]
        return fill(words()["kindsOne"], {"clause": words()[clause]})
    for status, template in (("ready", "kindsAllFull"), ("partial", "kindsAllPartial"), ("gap", "kindsAllGap")):
        if count[status] == total:
            return fill(words()[template], {"kindCount": number(total)})
    clauses = [fill(words()[template], {"n": number(count[status])})
               for status, template in (("ready", "clauseFull"), ("partial", "clausePart"), ("gap", "clauseNone"))
               if count[status]]
    return fill(words()["kinds"], {"kindCount": number(total), "clauses": _joined(clauses)})


def _filtered_sentence(shown: int, from_noun: str) -> Segments:
    if shown == 1:
        return fill(words()["filteredOne"], {"fromNoun": from_noun})
    if shown <= 9:
        word = _count_text(shown)
        return fill(words()["filteredFew"], {"SourceCount": word[:1].upper() + word[1:], "fromNoun": from_noun})
    return fill(words()["filteredMany"], {"sourceCount": number(shown), "fromNoun": from_noun})


def _keys(sources: dict[str, Source], asked: str | None) -> tuple[list[str], int, bool]:
    """The source keys in view, in registry order, how many asked-for keys the registry lacks, and
    whether the page was filtered."""
    if asked is None:
        return list(sources), 0, False
    wanted = [key.strip() for key in asked.split(",") if key.strip()]
    known = [key for key in sources if key in wanted]
    return known, len({key for key in wanted if key not in sources}), True


def _in_view(sources: dict[str, Source], keys: list[str], from_tool: str | None) -> set[str]:
    """The readiness rows in view: every row of the keys in view, and, when the link came from a tool
    that answers a kind of question, only the rows that tool draws on (config/tools.toml)."""
    rows = {row.id for key in keys for row in sources[key].readiness}
    tool = load_tools().get(from_tool) if from_tool else None
    return rows & set(tool.readiness.draws_on) if tool and tool.readiness else rows


def _empty(filter_: dict, abstention: dict, matched: int) -> dict:
    return {"rows": [], "coverage": {"matched": matched, "used": 0, "not_used": []}, "abstention": abstention,
            "filter": filter_, "sources": [], "kinds": [], "gaps": [], "fixes": [], "routes": [], "headline": None,
            "headline_abstention": None, "parse_failures": None, "measured": None}


def data_readiness_for(call: Call, sources: str | None = None, from_tool: str | None = None) -> dict:
    """The Data readiness page for every source, or for the sources behind one answer."""
    registry_sources = load_sources()
    keys, unknown, filtered = _keys(registry_sources, sources)
    nouns = words()["fromNouns"]
    from_key = from_tool if from_tool in nouns and from_tool != "unknown" else "unknown"
    in_view = _in_view(registry_sources, keys, from_tool if filtered else None)
    filter_ = {"sources": keys if filtered else None, "unknown": unknown, "from": from_key if filtered else None,
               "shown": len(in_view), "total": sum(len(source.readiness) for source in registry_sources.values())}
    # A link whose known sources are all outside its tool's rows shows nothing either, so it says the
    # same as one that names no known source, never "0 sources".
    if filtered and not in_view:
        return _empty(filter_, {"reason": "unknown_sources"}, 0)

    latest: dict[tuple[str, str], list[dict]] = {}
    for row in _rows(call, "latest_measures.sql", as_of=call.as_of):
        latest.setdefault((row["source"], row["measure"]), []).append(row)
    if not latest:
        first = _rows(call, "first_measured.sql")[0]["first_measured_on"]
        if first in (None, ""):
            return _empty(filter_, {"reason": "no_measures"}, len(in_view))
        return _empty(filter_, {"reason": "before_first_measure", "first_measured_on": _iso(_date(first))},
                      len(in_view))

    # Every row is measured, so each kind's status counts the gaps a filtered view leaves out.
    page = Page(call, registry_sources, Measures(latest))
    every_row = page.source_rows(list(registry_sources))
    every_gap = page.rank()
    first_rows = {key: source.readiness[0].id for key, source in registry_sources.items() if source.readiness}
    rows = [row for row in every_row
            if (first_rows[row["source_key"]] if row["type"] == "gap" else row["id"]) in in_view]
    ranked = [found for found in every_gap if found.row_id in in_view]
    kinds = _kinds(page, every_gap, in_view, from_tool if filtered else None)
    fixes = page.fixes(ranked)
    routes = page.routes(in_view)
    unmeasured = [row["id"] for row in rows if row["type"] == "unmeasured"]

    headline = abstained = None
    if unmeasured:
        abstained = {"reason": "unmeasured", "unmeasured": len(unmeasured), "sources": len(in_view)}
    else:
        first = (_filtered_sentence(len(in_view), nouns[from_key]) if filtered else _kinds_sentence(kinds))
        segments = [*first, {"text": " "}, *_gaps_sentence(ranked)]
        headline = {"segments": segments, "text": text_of(segments)}

    # The plan pages the layout parser could not read belong with the plans' row: none to list
    # (None) when that row is out of view.
    failures = [{"project_id": row["project_id"], "document_id": row["document_id"], "pdf_page": int(row["pdf_page"]),
                 "failed_on": _iso(_date(row["failed_on"]))}
                for row in _rows(call, "parse_failures.sql", as_of=call.as_of)] if PLANS in in_view else None
    days = [_date(row["measured_on"]) for row in page.measures.rows if row["source_key"] in keys]
    not_used = [{"reason": "not_measured", "rows": unmeasured}] if unmeasured else []
    if unknown:
        not_used.append({"reason": "unknown_source", "keys": unknown})
    return {
        "rows": page.measures.rows,
        "coverage": {"matched": len(in_view), "used": len(in_view) - len(unmeasured), "not_used": not_used},
        "abstention": None,
        "filter": filter_,
        "sources": rows,
        "kinds": kinds,
        "gaps": [found.as_dict() for found in ranked],
        "fixes": fixes,
        "routes": routes,
        "headline": headline,
        "headline_abstention": abstained,
        "parse_failures": failures,
        "measured": {"first": _iso(min(days)), "last": _iso(max(days))} if days else None,
    }


def registry_page() -> dict:
    """What the Sources and licenses page lists, and how many rows and fixes the Data readiness page's
    skeleton holds, from the source and tool registries alone: it never waits for the warehouse."""
    sources = load_sources()
    return {
        "datasets": [{"key": key, "dataset_name": source.dataset_name, "data_source": source.attribution.data_source,
                      "catalog_url": source.attribution.catalog_url,
                      "name_checked": source.attribution.name_checked.isoformat(), "license": source.license}
                     for key, source in sources.items() if source.attribution],
        "collections": [{"name": found.name, "publisher": found.publisher, "origin": found.origin}
                        for source in sources.values() for found in source.collections],
        "readiness_rows": sum(len(source.readiness) for source in sources.values()),
        "kinds": sum(1 for tool in load_tools().values() if tool.readiness),
        "known_gaps": sum(len(source.known_gaps) for source in sources.values()),
        "fixes": sum(len(source.fixes) for source in sources.values()),
    }
