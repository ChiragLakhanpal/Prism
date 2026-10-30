"""How each registry tool's result answers its benchmark question, in the question's shape (ticket 33).

Each tool question in evals/benchmark.yaml has an expected answer whose keys a reader here fills from the tool's
result: check_plan's references under each mark, find_comparables' past range, and so on. The offline gate reads
each tool's answer on the fixture this way and compares it with the question's expected answer, which comes from
tests/ground_truth/values.toml or ground-truth SQL (tests/test_tools.py). The full gate reads the live agent's tool
calls the same way (strata.evals.scoring), so both gates mean the same thing by a tool's answer.

A reader may find more than a question asks. answered() keeps only the keys the question expects, so a question
can check part of an answer, such as only the packages advertised again.
"""

from __future__ import annotations

import datetime as dt
from decimal import Decimal, InvalidOperation
from pathlib import Path

from strata.lakehouse import ground_truth

ROOT = Path(__file__).resolve().parents[3]


def canonical(value) -> str:
    """One value as text, for comparing rows at the same rounding (CLAUDE.md rule 1): a number with no trailing
    zeros and no exponent, so 1245092.760 and "1245092.76" agree and 4.1503 and 4.15 do not; a date as ISO; true
    or false; and nothing as empty text."""
    if value is None or value == "":
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, dt.datetime | dt.date):
        return value.isoformat()
    try:
        number = Decimal(str(value).strip())
    except InvalidOperation:
        return str(value)
    if not number.is_finite():
        return str(value)
    text = format(number.normalize(), "f")
    return text if text != "-0" else "0"


def same_rows(rows) -> list[list[str]]:
    """Rows as canonical text in a fixed order, each row's cells sorted too, so two queries that order their rows
    or their columns differently agree. Genie names and orders its columns its own way, so a row is compared by
    its values alone. A row with a column the ground truth lacks, such as an added country name, still differs."""
    return sorted(sorted(canonical(cell) for cell in row) for row in rows)


def ground_truth_rows(question, root: Path = ROOT) -> list[list[str]]:
    """The rows a question's ground-truth SQL expects on the fixture, from its '-- expect:' lines."""
    return same_rows(ground_truth.read(root / question["ground_truth"]).expected[1:])


def marks(result) -> dict[str, list[str]]:
    return {row["activity_reference_no"]: [mark["mark"] for mark in row["marks"]] for row in result["rows"]}


def marked(result, question) -> dict[str, list[str]]:
    """check_plan's answer: the references under each mark, in the benchmark question's shape."""
    found = {"unmarked": sorted(ref for ref, given in marks(result).items() if not given)}
    for mark in ("needs_a_look", "watch", "data_note"):
        found[mark] = sorted(ref for ref, given in marks(result).items() if mark in given)
    found["with_a_signal"] = sorted(ref for ref, given in marks(result).items() if {"needs_a_look", "watch"} & set(given))
    # Ticket 21: the activities whose reasons give a delay from the saved baseline as well.
    found["baseline_delays"] = sorted(row["activity_reference_no"] for row in result["rows"]
                                      if any("baseline" in reason for mark in row["marks"] for reason in mark["reasons"]))
    # Ticket 36: the plan's counts come back as a citable summary, which a Project Paper summary cites.
    found["activities"] = [result["summary"]["counts"]["activities"]]
    found["counts_cited_as"] = [result["summary"]["evidence_id"]]
    # Ticket 41: each activity with a signal, with its estimate in US$ millions as Home's briefing line writes it.
    found["estimated_millions"] = sorted(f"{row['activity_reference_no']} {row['estimated_millions']}"
                                         for row in result["rows"]
                                         if {"needs_a_look", "watch"} & {mark["mark"] for mark in row["marks"]})
    # Ticket 38: the rows that came from an upload, by their place in its file.
    found["upload_positions"] = sorted(row["position"] for row in result["rows"] if row.get("position") is not None)
    # Ticket 131: the activities whose reference breaks STEP's grammar and stays as the plan gives it.
    found["reference_as_read"] = sorted(row["activity_reference_no"] for row in result["rows"]
                                        if row.get("reference_as_read"))
    return found


def in_top_three(result, question) -> dict[str, list[str]]:
    """search_passages' answer: which of the expected passages are among its first three, which matched passages
    it left out because Prompt Shields found an attack or never screened them, and which a passage reviewer
    ranked lower for the query's kind of question (ticket 32)."""
    top = {row["evidence_id"] for row in result["rows"][:3]}
    from strata.knowledge.shields import LEFT_OUT

    left_out = [evidence for entry in result["coverage"]["not_used"]
                if entry["reason"] in LEFT_OUT for evidence in entry["evidence_ids"]]
    found = {"top_three_include": sorted(set(question["expected"]["top_three_include"]) & top),
             "left_out": sorted(left_out)}
    if "ranked_lower" in question["expected"]:
        found["ranked_lower"] = sorted(result["ranked_lower"]["evidence_ids"])
    return found


def readiness_answer(result, question) -> dict[str, list]:
    """data_readiness_for's answer, in the keys its question expects: the awards row's STEP-reference
    measure and the known gaps shown, or the stress shelf's P130164 risk annex outcome."""
    found = {}
    awards = [row for row in result["sources"] if row["id"] == "awards"]
    if awards:
        linked = result["rows"][awards[0]["cells"]["linked"]["row"]]
        found["linked_step_reference"] = [linked["count"], linked["denominator"]]
    found["known_gaps"] = [row["id"] for row in result["sources"] if row["type"] == "gap"]
    annex = [entry for entry in result["stress_shelf"] if entry["kind"] == "scan_annex"]
    if annex and annex[0]["outcome_row"] is not None:
        outcome = result["rows"][annex[0]["outcome_row"]]
        found["rated_risks_recovered"] = [outcome["count"], outcome["denominator"]]
    return {key: found.get(key) for key in question["expected"]}


def lessons_answer(result, question) -> dict[str, list]:
    """get_lessons' answer: the first lesson, the evidence ids it rests on and IEG's part in them, and the
    editions of the rules the lessons' projects followed; with packages, from the summary record, the completion
    reports counted and each risk factor they raised with how many raised it (ticket 30)."""
    rows = result["rows"]
    found = {"first": [rows[0]["statement"]] if rows else [],
             "first_evidence": [source["evidence_id"] for source in rows[0]["evidence"]] if rows else [],
             "first_ieg_status": [rows[0]["ieg_status"]] if rows else [],
             "editions": sorted({row["edition"]["key"] for row in rows if row["edition"]})}
    reports = result["summary"]["reports"]
    if reports is not None:
        found |= {"reports_read": [reports["read"]],
                  "raised": [[factor["key"], factor["k"]] for factor in reports["risk_factors"]]}
    return found


def past_range(result, question) -> dict[str, list]:
    """find_comparables' answer: the quartiles and 8-in-10 point in months, read from the summary record
    the agent cites them by, the packages still open, the canceled ones it left out, the packages
    signed within the plan's months, and the numbers each "in 10" phrase states, with the words that go
    with the plan's. A package with no plan row (ticket 15) has no plan, so its question asks nothing of one.
    A question about the quantile dots (ticket 15) asks only how many there are and which packages the last
    one stands for. With too few comparables for a range (ticket 33), it gives the abstention's reason and how
    many comparables there were instead; for a STEP reference it does not know, counts is null, so none."""
    if result["abstention"] is not None and result["summary"]["past_range"] is None:
        return {"abstention": [result["abstention"]["reason"]],
                "comparables": [(result["counts"] or {}).get("comparables", 0)]}
    if "last_dot" in question["expected"]:
        dots = result["quantile_dots"] or []
        return {"quantile_dots": [len(dots)], "last_dot": sorted(dots[-1]["step_references"]) if dots else [],
                "last_dot_still_open": [dots[-1]["still_open"]] if dots else []}
    found = {
        "past_range_months": [result["summary"]["past_range"][name] for name in ("q25", "q50", "q75", "q80")],
        "cited_as": [result["summary"]["evidence_id"]],
        "still_open": sorted(row["step_reference"] for row in result["rows"] if row["still_open"]),
        "canceled_left_out": sorted(reference for entry in result["coverage"]["not_used"]
                                    if entry["reason"] == "canceled" for reference in entry["step_references"]),
        "eight_in_ten": result["summary"]["frequencies"]["q80"],
    }
    if result["plan"] is not None:
        plan_months = result["plan"]["months"]
        found |= {
            "signed_within_plan": sorted(row["step_reference"] for row in result["rows"]
                                         if not row["still_open"] and row["months"] <= plan_months),
            "plan_in_ten": result["summary"]["frequencies"]["plan"]["states"],
            "plan_in_ten_words": [result["summary"]["frequencies"]["plan"]["words"]],
        }
    return found


def disagreement_answer(result, question) -> dict[str, list]:
    """get_disagreements' answer: each disagreement's two sides by evidence id in the order written, the side
    it leans on, the ladder's rule, the sides that carry their passage's words for a quote, the passages whose
    words the coverage line says it kept from the agent because Prompt Shields found an attack or never screened
    them (ticket 64), and, from the summary record the agent cites them by, the runs of the trajectory, each as
    [rating, first ISR, last ISR], and the count of assertions the run left out."""
    evidence = {side["assertion_id"]: side["evidence_id"] for row in result["rows"] for side in row["sides"]}
    from strata.knowledge.shields import LEFT_OUT

    left_out = [evidence for entry in result["coverage"]["not_used"]
                if entry["reason"] in LEFT_OUT for evidence in entry["evidence_ids"]]
    return {"disagreements": [[side["evidence_id"] for side in row["sides"]] for row in result["rows"]],
            "leans_on": [evidence[row["lean_assertion_id"]] for row in result["rows"]],
            "rules": [row["rule_id"] for row in result["rows"]],
            "quotable_sides": [side["evidence_id"] for row in result["rows"] for side in row["sides"] if side["text"]],
            "left_out": sorted(left_out),
            "cited_as": [result["summary"]["evidence_id"]],
            "trajectory_runs": [[run["value"], run["first_sequence"], run["last_sequence"]]
                                for trajectory in result["summary"]["trajectories"] for run in trajectory["runs"]],
            "rejected": [result["summary"]["rejected"]["count"]]}


def estimate_time_answer(result, question) -> dict[str, list]:
    """estimate_time's answer, from the summary record the agent cites it by. The time estimate (ticket 26): why it
    gives no time estimate, and for which feature; how many comparable packages it counted; and why there is no
    track record, if there is none. The planned dates for each step (ticket 27): the method family, the basis, the
    steps that got a cautious date, how many steps the tool counts as undated, and one named comparable's delay at
    the signed contract. Section 4's counts: the comparable packages whose records give their whole approach, those
    of them the thresholds rule out for this package, and those whose records don't give it. For a STEP reference
    the tool does not know there are no step dates, so it found none of them."""
    abstention = result["abstention"] or {}
    track = result["summary"]["track_record"] or {}
    options = result["summary"]["options"] or {}
    found = {"abstention": [abstention.get("reason")], "feature": [abstention.get("feature")],
             "comparables": [result["summary"]["comparables"]["n"]], "cited_as": [result["summary"]["evidence_id"]],
             "track_record": [(track.get("abstention") or {}).get("reason")],
             "approach_counts": [[options.get("recorded"), options.get("ruled_out"), options.get("unrecorded")]]}
    steps = result["summary"]["step_dates"]
    if steps is None:
        return found
    signed = next(entry for entry in steps["steps"] if entry["step_key"] == "contract_signed")
    named = {reference for reference, _ in question["expected"].get("signed_delay", [])}
    return {**found, "family": [steps["family"]], "basis": [steps["basis"]],
            "step_comparables": [steps["coverage"]["total"]],
            "dated_steps": [entry["step_key"] for entry in steps["steps"]
                            if entry["cautious"] and entry["cautious"]["planned_date"]],
            "undated_steps": [steps["undated_n"]],
            "signed_delay": [[entry["step_reference"], entry["days"]] for entry in signed["comparables"]
                             if entry["step_reference"] in named],
            # Ticket 38: the date the signed contract's step is dated from, the plan's as first published here, or an
            # upload's own date for an upload's row.
            "dated_from": [signed["plan_first_date"]]}


def cost_answer(result, question) -> dict[str, list]:
    """compare_cost_estimates' answer: the packages signed above and below their own cost estimates, its
    abstention, and the package's own cost estimate (ticket 31)."""
    return {"signed_above": sorted(row["step_reference"] for row in result["rows"] if row["diff_pct"] > 0),
            "signed_below": sorted(row["step_reference"] for row in result["rows"] if row["diff_pct"] < 0),
            "abstention": [result["abstention"]["reason"]] if result["abstention"] else [],
            "own_estimate": [result["package"]["estimated_amount_usd"]]}


def rejected_answer(result, question) -> dict[str, list]:
    """rejected_bids' answer: n of m from the summary, the packages in two of its groups, and the groups' order
    (ticket 31)."""
    def packages(key: str) -> list[str]:
        return sorted({row["step_reference"] for row in result["rows"] if row["item_key"] == key})
    counts = result["summary"]["counts"]
    return {"n_of_m": [counts["n"], counts["m"]], "bid_security": packages("bid_security"),
            "key_staff": packages("key_staff"),
            "group_order": [group["item_key"] for group in result["summary"]["groups"]]}


def criteria_answer(result, question) -> dict[str, list]:
    """compare_criteria's answer: n of the total whose criteria are public, one item's stated, compared and same or
    less, and the comparables still open, which it never compares (ticket 31)."""
    counts = result["summary"]["counts"]
    items = {item["item_key"]: item for item in result["summary"]["items"]}
    found = {"public": [counts["n"], counts["total"]],
             "still_open": sorted(evidence.split(":", 1)[1] for entry in result["coverage"]["not_used"]
                                  if entry["reason"] == "still_open" for evidence in entry["evidence_ids"])}
    for key in items:
        found[key] = [items[key]["stated"], items[key]["compared"], items[key]["same_or_less"]]
    return found


def signals_answer(result, question) -> dict[str, list]:
    """project_signals' answer: the status, and what each check that fired fired on: the activities by STEP
    reference, or the months the loan history first showed a new closing date (ticket 37)."""
    found = {"status": [result["status"]]}
    for row in result["rows"]:
        found[row["check"]] = sorted(item.get("activity_reference_no") or item.get("reported_on") for item in row["items"])
    return found


def rebidding_answer(result, question) -> dict[str, list]:
    """rebidding_risk's answer: n of m and the past range's total from the summary, the packages advertised again,
    each reason quoted with its notice, the groups' order and why the model is not shown (ticket 28)."""
    summary = result["summary"]
    return {"n_of_m": [summary["n"], summary["m"]], "past_range_total": [summary["past_range_total"]],
            "advertised_again": sorted(row["step_reference"] for row in result["rows"]),
            "quoted": [[row["step_reference"], row["quote"]["notice_id"], row["quote"]["text"]]
                       for row in result["rows"] if row["quote"]],
            "group_order": [group["reason_code"] for group in summary["groups"]],
            "model_not_shown": [summary["model"]["not_shown_reason"]] if not summary["model"]["shown"] else [],
            "cited_as": [summary["evidence_id"]]}


def track_answer(result, question) -> dict[str, list]:
    """agency_track_record's answer: its counts from the summary, the packages in each state, which source it
    counted as signed and the packages the awards dataset shows signed while the plan does not (ticket 36)."""
    counts = result["summary"]["counts"]
    return {"counts": [counts["n"], counts["signed_by_plan"], counts["signed_late"], counts["open_past_date"]],
            "middle_delay_days": [counts["middle_delay_days"]],
            "signed_late": sorted(row["step_reference"] for row in result["rows"] if row["state"] == "signed_late"),
            "open_past_date": sorted(row["step_reference"] for row in result["rows"] if row["state"] == "open_past_date"),
            "signed_from": [result["signed_from"]],
            "differs_from_awards": [entry["step_reference"] for entry in result["differs_from_awards"]],
            "cited_as": [result["summary"]["evidence_id"]]}


def genie_answer(result, question) -> dict[str, list]:
    """ask_genie's answer: the rows of the query Genie wrote, by value and in a fixed order, which its ground-truth
    SQL's rows must equal (ticket 33). Column names and their order are left out: Genie names and orders its
    columns its own way."""
    return {"rows": same_rows(list(row["values"].values()) for row in result["rows"])}


ANSWERS = {"ask_genie": genie_answer, "check_plan": marked, "search_passages": in_top_three, "data_readiness_for": readiness_answer,
           "agency_track_record": track_answer,
           "find_comparables": past_range, "get_disagreements": disagreement_answer,
           "get_lessons": lessons_answer, "estimate_time": estimate_time_answer, "compare_cost_estimates": cost_answer,
           "rejected_bids": rejected_answer, "compare_criteria": criteria_answer, "project_signals": signals_answer,
           "rebidding_risk": rebidding_answer,
           "project_records": lambda result, question: {
               part: sorted(row["reference"] for row in result["rows"] if row["part"] == part)
               for part in question["expected"]}}


def answered(result, question) -> dict[str, list[str]]:
    """The tool's answer, in its benchmark question's shape: only the keys the question expects. The keys are the
    file's own (ask_genie's is rows, the same key expected() gives), so reading an answer opens no file."""
    found = ANSWERS[question["tool"]](result, question)
    return {key: found.get(key) for key in question["expected"]}


def expected(question) -> dict[str, list[str]]:
    """The answer a tool question expects: for ask_genie the rows its ground-truth SQL expects, and for any other
    tool its expected answer as the benchmark file writes it. Each reader gives its answer in that same form, so a
    list whose order does not matter is written sorted in the file and sorted by its reader."""
    if question["tool"] == "ask_genie":
        return {"rows": ground_truth_rows(question)}
    return question["expected"]


def arguments_of(question, engine, viewer, today: dt.date | None = None) -> dict:
    """A tool question's arguments. A check-your-criteria tool's question (ticket 31) names the find_comparables call
    its comparables come from, and their STEP references become its comparables argument, as of today at the
    latest when given."""
    from strata.tools import registry

    arguments = dict(question["arguments"])
    if "comparables_of" in question:
        found = registry.call("find_comparables", question["comparables_of"],
                              registry.Context(engine=engine, viewer=viewer, as_of=today))
        arguments["comparables"] = ",".join(row["step_reference"] for row in found["rows"])
    return arguments


def reference(question, engine, viewer, root: Path = ROOT, today: dt.date | None = None) -> dict | None:
    """What a tool question's answer must be on this engine's data: for ask_genie, the rows its ground-truth SQL
    returns here; for any other tool, the reading of what the tool gives for the question's own arguments. On the
    fixture both equal the question's expected answer (tests/test_tools.py), so the full gate can score the live
    agent on the workspace's data with no literal from the fixture. None for a question with no tool. today, the
    day the full gate runs, caps the as-of date as the answer loop caps a turn's (ADR 0002: the earlier wins)."""
    from strata.tools import registry

    tool = question.get("tool")
    if not tool:
        return None
    if tool == "ask_genie":
        case = ground_truth.read(root / question["ground_truth"])
        return {"rows": same_rows(engine.run(case.sql, case.params).rows)}
    result = registry.call(tool, arguments_of(question, engine, viewer, today),
                           registry.Context(engine=engine, viewer=viewer, as_of=today))
    return answered(result, question)
