"""The hindsight test (ticket 34; docs/PLAN.md section 10): Strata replayed as of each closed pilot project's
approval date, counting which risks its completion report later blamed Strata would have shown.

It is a scorer for the replay harness (strata.estimates.harness, the spec's seam 5). Each gate-set project is
one window: the cutoff is its approval date, and the outcomes are read as of the run. For each project the scorer

1. reads the main packages of its first Procurement Plan: the hindsight.main_packages largest by Estimated
   Amount (US$), as of the run, since the packages are the question;
2. runs the risk-table builder (strata.packages.risks, ticket 30) for each one, frozen at the approval date,
   with the package's category, Method and country, and keeps the risks each table shows (at most
   package_risks.max_rows; a row the verifier removed is not shown). Every row and passage a table rests on
   goes through the harness's frozen reader, which stops the run if one was public after the approval date;
3. asks get_lessons, frozen the same way, whether a lesson in the library already covered each blamed risk.

The library in a replay is the one decided by the run's date, with each lesson counted from the day the quotes
it rests on became public (get_lessons, call.decided_by). Strata did not exist on a 2014 approval date, so
counting lessons from their 2026 decisions would leave the library empty at every approval date.

A project's blamed risks are the reconciled set the coding tool stored (strata.estimates.hindsight_coding):
two coders' readings of the ICR, with the ICR Review settling where they differ. A blamed risk is caught when
any main package's table showed it.

Around the scorer:

- gate_set() picks the projects: the pilot projects (config/slice.toml) with an ICR, leaving out and listing
  extraction examples (config/lessons.toml) and projects exposed to Strata (sql/hindsight/exposed.sql), and
  listing those still waiting for their ICR to be read, their coding or their first plan.
- run() replays the gate set for a release and stores each project's scores and the release's totals in
  strata.ops.evaluation_result and the tracker: blamed, covered at approval, shown, the checklist's catch, and
  hindsight recall, coverage times shown-when-covered, with Wilson's interval. The checklist is each sector's
  hindsight.checklist_size commonest blamed risks among the other gate-set projects (checklists()).
- decide() is the release gate: a run must not lose McNemar's exact test to the champion on the same blamed
  risks, and must catch more than the checklist, to become the champion.
- report_sentence() writes the report in the first person from the stored totals alone.
ops/hindsight/release_gate.py runs all of it as one command.
"""

from __future__ import annotations

import datetime as dt
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from importlib import resources

from strata.config import LessonLists, Slice, Thresholds, load_lesson_lists, load_slice, load_thresholds
from strata.estimates import harness
from strata.estimates.harness import HARNESS, Replay, Score, Scored, Window
from strata.estimates.past_range import as_date
from strata.lakehouse.engine import Engine
from strata.tools import registry

SCORER = "hindsight_test"
MODEL = "strata.packages.risks"


def _sql(name: str) -> str:
    return (resources.files("strata.estimates") / "sql" / "hindsight" / f"{name}.sql").read_text()


@dataclass(frozen=True)
class Settings:
    """The test's settings, from config/thresholds.toml's [hindsight] and the builder's max_rows."""

    main_packages: int
    checklist_size: int
    interval_level: float
    min_blamed_for_share: int
    expected_projects: int
    mcnemar_alpha: float
    notices_from: dt.date
    max_rows: int

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds) -> Settings:
        value = thresholds.value
        return cls(int(value("hindsight.main_packages")), int(value("hindsight.checklist_size")),
                   float(value("hindsight.interval_level")), int(value("hindsight.min_blamed_for_share")),
                   int(value("hindsight.expected_projects")), float(value("hindsight.mcnemar_alpha")),
                   as_date(value("hindsight.notices_from")), int(value("package_risks.max_rows")))


@dataclass(frozen=True)
class Case:
    """One gate-set project: when it was approved, its sector, the risks its completion report blamed (risk keys
    from config/lessons.toml) and the checklist the baseline shows for it."""

    project_id: str
    approval_date: dt.date
    sector: str | None
    blamed: tuple[str, ...]
    checklist: tuple[str, ...]


def _criteria(package: Mapping, notices_from: dt.date) -> dict:
    """find_comparables' arguments for a first-plan package, as a planned package with no STEP row gives them."""
    from strata.tools.find_comparables import CATEGORIES

    return {"category": CATEGORIES.get(str(package["section"] or "").upper()), "method": package["method"],
            "country": package["country_code"], "notice_from": notices_from}


def _risks_build(*args, **options):
    from strata.packages import risks

    return risks.build(*args, **options)


def _detail(package: Mapping, table) -> dict:
    """What one frozen risk table showed, with the date each source it cites became public, for the stored record."""
    payload = table.payload
    return {"step_reference": package["activity_reference_no"],
            "estimated_amount_usd": None if package["estimated_amount_usd"] is None
            else f"{float(package['estimated_amount_usd']):.2f}",
            "empty_reason": payload.get("empty_reason"),
            "rows": [{"risk_key": row["risk_key"], "lesson_evidence_id": row["lesson"]["evidence_id"],
                      "sources": [{"evidence_id": source["evidence_id"], "public_from": source["public_from"]}
                                  for source in row["sources"]]}
                     for row in payload.get("rows", [])],
            "removed": [row["risk_key"] for row in ((payload.get("verifier") or {}).get("removed") or [])]}


class HindsightScorer:
    """The replay harness's scorer for the hindsight test: one window per gate-set project."""

    name = SCORER

    def __init__(self, cases: Mapping[str, Case], builder: Callable = _risks_build, model: str = MODEL):
        self.cases, self.builder, self.model = dict(cases), builder, model

    def score(self, replay: Replay) -> Scored:
        case = self.cases[replay.window.segment]
        settings = Settings.from_thresholds(replay.thresholds)
        cutoff, decided_by = replay.window.cutoff, replay.window.outcomes_through
        engine = replay.inputs.engine
        packages = replay.outcomes.rows(_sql("first_plan"), project_id=case.project_id)[:settings.main_packages]
        shown: list[str] = []
        details, read = [], []  # the date each row and passage the frozen tables read became public
        for package in packages:
            table = self.builder(engine, HARNESS, as_of=cutoff, criteria=_criteria(package, settings.notices_from),
                                 words=package["description"], thresholds=replay.thresholds, decided_by=decided_by)
            rows = replay.inputs.checked([row for _, row in table.facts.items()])
            read += [as_date(row["public_from"]) for row in rows if row.get("public_from")]
            details.append(_detail(package, table))
            shown += [row["risk_key"] for row in table.payload.get("rows", []) if row["risk_key"] not in shown]

        context = registry.Context(engine, HARNESS, "staff", cutoff, replay.thresholds, decided_by)
        covered = []
        for key in case.blamed:
            found = registry.call("get_lessons", {"risk_factor": key, "limit": 1}, context)
            lessons = [*found["rows"], *(quote for row in found["rows"] for quote in row["evidence"])]
            read += [as_date(row["public_from"]) for row in replay.inputs.checked(lessons)]
            if found["rows"]:
                covered.append(key)
        caught = [key for key in case.blamed if key in shown]
        checklist_caught = [key for key in case.blamed if key in case.checklist]
        scores = [Score("blamed", len(case.blamed)), Score("covered", len(covered)), Score("shown", len(caught)),
                  Score("shown_covered", len([key for key in caught if key in covered])),
                  Score("checklist_caught", len(checklist_caught)), Score("packages", len(packages)),
                  Score("blamed_keys", text=json.dumps(list(case.blamed))),
                  Score("covered_keys", text=json.dumps(covered)), Score("shown_keys", text=json.dumps(caught)),
                  Score("every_shown_key", text=json.dumps(shown)),
                  Score("checklist_keys", text=json.dumps(list(case.checklist))),
                  Score("package_tables", text=json.dumps(details)),
                  Score("inputs_through", text=max(read).isoformat() if read else None)]
        return Scored(scores, params={"project_id": case.project_id, "approval_date": cutoff.isoformat(),
                                      "main_packages": settings.main_packages, "max_rows": settings.max_rows})


# ── The gate set ─────────────────────────────────────────────────────────

# Why a pilot project with an ICR is not replayed. Left out: it never is. Waiting: it can be once its records or its
# coding are complete.
EXCLUDED = ("extraction_example", "exposed")
WAITING = ("icr_not_read", "not_coded", "no_first_plan")


@dataclass(frozen=True)
class GateSet:
    """The pilot projects with an ICR on a date: the cases the test replays, and the ones left out and the ones
    waiting, each with its reason, in project order."""

    as_of: dt.date
    candidates: tuple[str, ...]
    cases: tuple[Case, ...]
    excluded: tuple[dict, ...]
    waiting: tuple[dict, ...]


def checklists(blamed: Mapping[str, tuple[str | None, tuple[str, ...]]], size: int, order: list[str]) -> dict[str, tuple]:
    """The baseline for each project: the size risk factors that the completion reports of the other gate-set
    projects in its sector blamed most often, ties in the closed list's order. The project's own report is left out,
    so its checklist never rests on the answer it is scored against."""
    found = {}
    for project, (sector, _) in blamed.items():
        counts = {key: 0 for key in order}
        for other, (other_sector, keys) in blamed.items():
            if other != project and other_sector == sector:
                for key in keys:
                    counts[key] += 1
        ranked = sorted((key for key in order if counts[key] > 0), key=lambda key: (-counts[key], order.index(key)))
        found[project] = tuple(ranked[:size])
    return found


def _rows(engine: Engine, name: str, **params) -> list[dict]:
    result = engine.run(_sql(name), params)
    return [dict(zip(result.columns, row)) for row in result.rows]


def gate_set(engine: Engine, as_of: dt.date, lists: LessonLists | None = None, chosen: Slice | None = None,
             thresholds: Thresholds | None = None) -> GateSet:
    """The pilot projects (config/slice.toml) with an ICR, as of a date. A project the lesson extractor's
    instructions use as an example (config/lessons.toml, [extraction]) or one exposed to Strata
    (sql/hindsight/exposed.sql) is left out. One whose ICR Strata has not read, whose blamed risks are not reconciled
    yet, or whose first Procurement Plan Strata has not read, waits."""
    from strata.estimates import hindsight_coding
    from strata.lakehouse.passages import select

    lists = lists or load_lesson_lists()
    settings = Settings.from_thresholds(thresholds or load_thresholds())
    selected = select(engine, chosen or load_slice()).selected
    reports = hindsight_coding.reports(engine, selected, as_of)
    candidates = tuple(project for project in selected if (reports.get(project) or {}).get("icr_document_id"))
    exposed = {row["project_id"] for row in _rows(engine, "exposed", as_of=as_of)}
    reconciled = hindsight_coding.reconciled(engine, as_of)
    excluded, waiting, usable = [], [], []
    for project in candidates:
        reason = ("extraction_example" if project in lists.example_projects else "exposed" if project in exposed
                  else "icr_not_read" if not int(reports[project]["icr_passages"] or 0)
                  else "not_coded" if project not in reconciled
                  else "no_first_plan" if not _rows(engine, "first_plan", project_id=project, as_of=as_of) else None)
        if reason in EXCLUDED:
            excluded.append({"project_id": project, "reason": reason})
        elif reason in WAITING:
            waiting.append({"project_id": project, "reason": reason})
        else:
            usable.append(project)
    order = [item.key for item in lists.risk_factors]
    blamed = {project: (reports[project]["sector"], tuple(reconciled[project]["blamed"])) for project in usable}
    checklist = checklists(blamed, settings.checklist_size, order)
    cases = tuple(Case(project, as_date(reports[project]["approval_date"]), blamed[project][0], blamed[project][1],
                       checklist[project]) for project in usable)
    return GateSet(as_of, candidates, cases, tuple(excluded), tuple(waiting))


REASON_WORDS = {"extraction_example": "an example in the lesson extractor's instructions",
                "exposed": "exposed to Strata", "icr_not_read": "ICR not read yet", "not_coded": "not coded yet",
                "no_first_plan": "no Procurement Plan read"}


def funnel_lines(gate: GateSet) -> list[str]:
    """The gate set in words, for the commands' output: how many pilot projects have an ICR, how many the test
    replays, and each one left out or waiting, with its reason."""
    lines = [f"Pilot projects with an ICR on {gate.as_of.isoformat()}: {len(gate.candidates)}. "
             f"The hindsight test replays {len(gate.cases)}."]
    for heading, listed in (("Left out", gate.excluded), ("Waiting", gate.waiting)):
        if listed:
            lines.append(f"{heading}: " + ", ".join(f"{row['project_id']} ({REASON_WORDS[row['reason']]})"
                                                    for row in listed) + ".")
    return lines


# ── A run ────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class HindsightRun:
    run_id: str
    release: str
    record: dict
    gate: GateSet


def _share(part: int, whole: int) -> float | None:
    return None if whole == 0 else round(part / whole, 4)


def wilson(caught: int, blamed: int, level: float) -> tuple[float, float] | None:
    """Wilson's score interval for caught of blamed at the given level, as two fractions at four decimals."""
    from statistics import NormalDist

    if blamed == 0:
        return None
    z = NormalDist().inv_cdf(1 - (1 - level) / 2)
    share = caught / blamed
    middle = (share + z * z / (2 * blamed)) / (1 + z * z / blamed)
    half = z / (1 + z * z / blamed) * (share * (1 - share) / blamed + z * z / (4 * blamed * blamed)) ** 0.5
    return round(max(0.0, middle - half), 4), round(min(1.0, middle + half), 4)


def run(engine: Engine, tracker, release: str, ran_at: dt.datetime, *, builder: Callable = _risks_build,
        model: str = MODEL, store: Engine | None = None, thresholds: Thresholds | None = None,
        lists: LessonLists | None = None, chosen: Slice | None = None) -> HindsightRun:
    """Run the hindsight test for a release: replay every gate-set project, then store the release's totals beside
    each project's scores in strata.ops.evaluation_result and in the tracker (MLflow on the workspace)."""
    limits = thresholds or load_thresholds()
    settings = Settings.from_thresholds(limits)
    as_of = ran_at.astimezone(dt.UTC).date()
    gate = gate_set(engine, as_of, lists, chosen, limits)
    scorer = HindsightScorer({case.project_id: case for case in gate.cases}, builder, model)
    run_id = harness.new_run_id(SCORER, ran_at)
    written = store or engine
    for case in gate.cases:
        harness.replay(engine, scorer, Window(case.approval_date, as_of, "project", case.project_id), tracker, run_id,
                       ran_at, written, limits)
    projects = [record for (kind, _), record in harness.segments(harness.run_rows(written, run_id)).items()
                if kind == "project"]
    total = {measure: sum(int(record[measure]) for record in projects)
             for measure in ("blamed", "covered", "shown", "shown_covered", "checklist_caught")}
    low, high = wilson(total["shown"], total["blamed"], settings.interval_level) or (None, None)
    coverage, when_covered = _share(total["covered"], total["blamed"]), _share(total["shown_covered"], total["covered"])
    # Coverage times shown-when-covered, from the counts rather than the rounded shares: shown_covered of blamed,
    # which is 0 when no lesson covered any blamed risk.
    recall = _share(total["shown_covered"], total["blamed"])
    scores = [Score("projects", len(projects)), Score("expected_projects", settings.expected_projects),
              Score("candidates", len(gate.candidates)), Score("blamed", total["blamed"]),
              Score("covered", total["covered"]), Score("shown", total["shown"]),
              Score("checklist_caught", total["checklist_caught"]),
              Score("coverage", coverage, f"{total['covered']} of {total['blamed']}"),
              Score("shown_when_covered", when_covered, f"{total['shown_covered']} of {total['covered']}"),
              Score("hindsight_recall", recall, f"{total['shown_covered']} of {total['blamed']}"),
              Score("interval_low", low), Score("interval_high", high),
              Score("interval_level", settings.interval_level), Score("risks_per_package", settings.max_rows),
              Score("main_packages", settings.main_packages), Score("checklist_size", settings.checklist_size),
              Score("min_blamed_for_share", settings.min_blamed_for_share),
              Score("excluded", text=json.dumps(list(gate.excluded))),
              Score("waiting", text=json.dumps(list(gate.waiting)))]
    summary = tracker.start_run(f"{SCORER} {release}", {"scorer": SCORER, "run_id": run_id, "release": release,
                                                        "model": model, "main_packages": settings.main_packages,
                                                        "max_rows": settings.max_rows})
    tracker.log_metrics(summary, {score.measure: score.value for score in scores if score.value is not None})
    tracker.log_text(summary, json.dumps({"excluded": gate.excluded, "waiting": gate.waiting}, indent=2),
                     "gate_set.json")
    tracker.end_run(summary)
    harness.write(written, [harness.row(run_id, scorer, Window(None, as_of, "release", release), score, summary,
                                        ran_at) for score in scores])
    return HindsightRun(run_id, release, stored_release(written, run_id), gate)


def stored_release(engine: Engine, run_id: str | None = None) -> dict | None:
    """A run's release totals as stored, with its run id, its MLflow run id and the day it ran: the latest run when
    run_id is None, and None when the test has never run."""
    run_id = run_id or harness.latest_run(engine, SCORER)
    if run_id is None:
        return None
    for (kind, segment), record in harness.segments(harness.run_rows(engine, run_id)).items():
        if kind == "release":
            return {**record, "release": segment, "ran_on": _moment(record["ran_at"]).date()}
    return None


# ── The release gate ─────────────────────────────────────────────────────

GATE_REASONS = ("promoted", "lost_to_champion", "did_not_beat_checklist", "nothing_to_compare")


@dataclass(frozen=True)
class Decision:
    """The release gate's verdict on one run: whether it became the champion, and why. pairs are the blamed risks
    both it and the champion were scored on; champion_only and challenger_only are those only one of them caught."""

    run_id: str
    release: str
    champion_run_id: str | None
    promoted: bool
    reason: str
    pairs: int
    champion_only: int
    challenger_only: int
    p_value: float | None
    caught: int
    checklist_caught: int


def mcnemar(champion_only: int, challenger_only: int) -> float:
    """McNemar's exact test: the two-sided p-value of the discordant pairs, each side as likely as the other."""
    from math import comb

    pairs = champion_only + challenger_only
    if pairs == 0:
        return 1.0
    tail = sum(comb(pairs, k) for k in range(min(champion_only, challenger_only) + 1)) / 2 ** pairs
    return min(1.0, 2 * tail)


def champion_run(engine: Engine) -> str | None:
    """The newest run the release gate promoted, or None before the first."""
    found = engine.run(_sql("champion"), {"scorer": SCORER, "gate": "gate", "promoted": "promoted", "yes": 1.0})
    return found.rows[0][0] if found.rows else None


def _caught(engine: Engine, run_id: str) -> dict[tuple[str, str], bool]:
    """Each blamed risk of a run, by project and risk key, and whether the run showed it."""
    found = {}
    for (kind, project), record in harness.segments(harness.run_rows(engine, run_id)).items():
        if kind == "project":
            shown = set(json.loads(record["shown_keys"]))
            found.update({(project, key): key in shown for key in json.loads(record["blamed_keys"])})
    return found


@dataclass(frozen=True)
class _GateScorer:
    name: str = SCORER
    model: str | None = None


def decide(engine: Engine, run_id: str, tracker, thresholds: Thresholds | None = None,
           store: Engine | None = None) -> Decision:
    """The release gate for one run of the hindsight test (spec, "Evaluation"). The run is a challenger to the
    champion: it must not lose a paired comparison on the same blamed risks (McNemar's exact test, losing when it
    caught fewer and p is below hindsight.mcnemar_alpha), and it must catch more blamed risks than the checklist did.
    A run that passes both becomes the champion. The verdict goes to strata.ops.evaluation_result and the tracker."""
    settings = Settings.from_thresholds(thresholds or load_thresholds())
    written = store or engine
    record = stored_release(written, run_id)
    champion = champion_run(written)
    champion = None if champion == run_id else champion
    caught, checklist = int(record["shown"]), int(record["checklist_caught"])
    pairs, champion_only, challenger_only, p_value = 0, 0, 0, None
    if champion is not None:
        mine, theirs = _caught(written, run_id), _caught(written, champion)
        both = [risk for risk in mine if risk in theirs]
        pairs = len(both)
        champion_only = sum(1 for risk in both if theirs[risk] and not mine[risk])
        challenger_only = sum(1 for risk in both if mine[risk] and not theirs[risk])
        p_value = mcnemar(champion_only, challenger_only)
    loses = p_value is not None and champion_only > challenger_only and p_value < settings.mcnemar_alpha
    reason = ("nothing_to_compare" if int(record["blamed"]) == 0 else "lost_to_champion" if loses
              else "did_not_beat_checklist" if caught <= checklist else "promoted")
    decision = Decision(run_id, record["release"], champion, reason == "promoted", reason, pairs, champion_only,
                        challenger_only, None if p_value is None else round(p_value, 6), caught, checklist)
    scores = [Score("promoted", int(decision.promoted)), Score("reason", text=reason),
              Score("champion_run_id", text=champion), Score("pairs", pairs), Score("champion_only", champion_only),
              Score("challenger_only", challenger_only), Score("mcnemar_p", decision.p_value),
              Score("caught", caught), Score("checklist_caught", checklist)]
    logged = tracker.start_run(f"{SCORER} gate {decision.release}", {"scorer": SCORER, "run_id": run_id,
                                                                    "champion_run_id": champion or "", "reason": reason})
    tracker.log_metrics(logged, {score.measure: score.value for score in scores if score.value is not None})
    tracker.end_run(logged)
    harness.write(written, [harness.row(run_id, _GateScorer(model=record.get("model")),
                                        Window(None, record["ran_on"], "gate", decision.release), score, logged,
                                        _moment(record["ran_at"])) for score in scores])
    return decision


def _moment(value) -> dt.datetime:
    """A stored ran_at as a time in UTC: from a datetime with or without a zone, or from text."""
    if not isinstance(value, dt.datetime):
        value = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return value if value.tzinfo else value.replace(tzinfo=dt.UTC)


def stored_decision(engine: Engine, run_id: str) -> dict | None:
    """The release gate's stored verdict on a run, or None when the gate has not judged it."""
    for (kind, _), record in harness.segments(harness.run_rows(engine, run_id)).items():
        if kind == "gate":
            return record
    return None


# ── The report sentence ──────────────────────────────────────────────────

NOT_RUN = "The hindsight test hasn't run yet. It runs on every release."


def _word(number) -> str:
    """One to nine in words, larger counts in numerals (DESIGN.md section 7, rule 12)."""
    from strata.estimates.model_card import WORDS

    return WORDS.get(int(number), str(int(number)))


def _plural(number, noun: str) -> str:
    return noun if int(number) == 1 else f"{noun}s"


def _percent(share: float) -> int:
    from decimal import ROUND_HALF_UP, Decimal

    return int((Decimal(str(share)) * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def report_sentence(record: Mapping | None) -> str:
    """The hindsight test's report, in the first person, written only from a run's stored totals (stored_release).
    The dashboard's "What the measures say" (the 45 design brief, section 7.3) and the proposal take it from here.
    The interval is given only from min_blamed_for_share blamed risks (DESIGN.md section 7, rule 15), and a run that
    found fewer pilot projects than expected says how many it could use."""
    if record is None:
        return NOT_RUN
    day = record["ran_on"]
    when = f"{day:%B} {day.day}"
    found, expected = int(record["projects"]), int(record["expected_projects"])
    if found == 0:
        return (f"In the hindsight test of {when}, I had no pilot project to check. None of the {expected} I expected "
                "had a completion report I could use yet.")
    blamed, per_package, checklist = int(record["blamed"]), record["risks_per_package"], record["checklist_size"]
    text = (f"In the hindsight test of {when}, I caught {int(record['shown'])} of {blamed} blamed risks across "
            f"{_word(found)} {_plural(found, 'project')}, at {_word(per_package)} {_plural(per_package, 'risk')} per "
            f"package. A checklist of the sector's {_word(checklist)} commonest {_plural(checklist, 'risk')} caught "
            f"{int(record['checklist_caught'])}.")
    if blamed >= int(record["min_blamed_for_share"]) and record.get("interval_low") is not None:
        text += (f" The {_percent(record['interval_level'])} percent interval runs from "
                 f"{_percent(record['interval_low'])} to {_percent(record['interval_high'])} percent.")
    if found < expected:
        text += f" I expected {expected} pilot projects with a completion report and could use {_word(found)}."
    return text
