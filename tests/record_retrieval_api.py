"""Writes the retrieval loop's recorded answers in tests/fixtures/api from the server itself (ticket 32).

The screen tests and the design gallery serve these files, and tests/test_retrieval_recordings.py checks that the
server still answers with them, so the feedback row, Passage reports and Judging cannot drift from the routes.
Build the fixture database first, then run:

    uv run --frozen python tests/record_retrieval_api.py

One story makes them, on a copy of the fixture database, with the made-up people of tests/fixtures/roles.toml and
a clock that starts on Friday, October 23, 2026 (tests/retrieval_scenario.py):

- Ana asks why P130164's works contracts were advertised again and marks paragraph 54 as the wrong passage, with a
  reason. Leela, who works on P130164, marks it as not useful, with none. Priya marks paragraph 55 as the wrong
  passage.
- Daniel, a passage reviewer, ranks paragraph 54 lower, and Priya's late decision on it is stale. Daniel keeps
  paragraph 55's ranking, then reopens it.
- Mei and Tomas, the two query judges, both grade query 2; Mei starts on query 1.
- In scale mode, Ana, Kofi and Sara agree on paragraph 54, and the weekly run picks the agreement for an audit.

Each list is recorded with the frame's counts (/api/lessons/me) from the same moment, as retrieval-me-*.json, so a
screen that serves the two together shows the counts the server gave together: the start of the story for the
empty and not-started states, then "-waiting" once the reports are in, "-decided" after Daniel's decision, "-after"
once the judges have graded, and "-audit" in scale mode.
"""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))

from retrieval_scenario import (ANA, DANIEL, KOFI, LEELA, MEI, PARAGRAPH_54, PARAGRAPH_55, PRIYA, SARA,  # noqa: E402
                                TOMAS, Loop)

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
QUERY_1, QUERY_2 = "nq-rural-works-delays", "nq-water-works-readiness"


def text(response) -> str:
    """An answer as the screens serve it: the body, or for a refusal its status with its body."""
    body = response.json()
    found = body if response.status_code == 200 else {"status": response.status_code, "body": body}
    return json.dumps(found, indent=2, ensure_ascii=False) + "\n"


def grades(passages: list[str], judge: str) -> dict[str, str]:
    """Query 2's grades: Mei grades the first 10 passages by id "Answers it", the next 5 "Partly", the rest "Not
    relevant"; Tomas the same, except two of her "Answers it" and three of her "Not relevant" as "Partly"."""
    ordered = sorted(passages)
    mei = {passage: "answers" if i < 10 else "partly" if i < 15 else "not_relevant" for i, passage in enumerate(ordered)}
    if judge == "mei":
        return mei
    return {**mei, **{passage: "partly" for passage in ordered[:2] + ordered[15:18]}}


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    found: dict[str, str] = {}
    pilot = Loop(FIXTURE_DB, folder / "pilot")
    try:
        get = lambda path, who, **params: text(pilot.request("GET", path, who, params=params or None))  # noqa: E731
        found["retrieval-me-passage-reviewer.json"] = get("/api/lessons/me", DANIEL)
        found["retrieval-me-judge.json"] = get("/api/lessons/me", MEI)
        found["retrieval-me-both.json"] = get("/api/lessons/me", PRIYA)
        found["passage-reports-empty.json"] = get("/api/passage-reports", DANIEL)
        found["passage-reports-no-access.json"] = get("/api/passage-reports", ANA)
        found["judging-no-access.json"] = get("/api/judging/queries", ANA)

        # Three reports from the drawer.
        ana = pilot.ask(ANA)
        found["feedback-sent.json"] = text(pilot.report(ANA, ana, reason=(
            "It is about estimates in general, not why these contracts were advertised again.")))
        found["feedback-mine-waiting.json"] = get("/api/feedback", ANA, evidence_id=PARAGRAPH_54, run_id=ana)
        # The same report sent again, as from another tab: refused, with the report already sent.
        found["feedback-already-sent.json"] = text(pilot.report(ANA, ana, kind="not_useful"))
        found["feedback-preview.json"] = text(pilot.report(ANA, ana, kind="not_useful", view="piu"))
        pilot.later(minutes=20)
        pilot.report(LEELA, pilot.ask(LEELA), kind="not_useful")
        pilot.later(minutes=20)
        priya = pilot.ask(PRIYA)
        pilot.report(PRIYA, priya, evidence_id=PARAGRAPH_55)

        # Passage reports, as Daniel and as Priya see them.
        pilot.later(hours=2)
        found["retrieval-me-passage-reviewer-waiting.json"] = get("/api/lessons/me", DANIEL)
        found["retrieval-me-both-waiting.json"] = get("/api/lessons/me", PRIYA)
        queue = pilot.request("GET", "/api/passage-reports", DANIEL).json()
        found["passage-reports.json"] = get("/api/passage-reports", DANIEL)
        found["passage-reports-own-report.json"] = get("/api/passage-reports", PRIYA)
        groups = {row["passage_id"]: row["group_id"] for row in queue["groups"]["you"]}
        rebidding, clearances = groups["31525018/v1/54"], groups["31525018/v1/55"]
        found["passage-report.json"] = get(f"/api/passage-reports/{rebidding}", DANIEL)
        found["passage-report-own-report.json"] = get(f"/api/passage-reports/{clearances}", PRIYA)
        found["passage-report-not-found.json"] = get("/api/passage-reports/grp-000000000000", DANIEL)
        seen = pilot.request("GET", f"/api/passage-reports/{rebidding}", PRIYA).json()["state"]
        found["passage-report-saved.json"] = text(pilot.decide(DANIEL, rebidding, reason=(
            "The paragraph is about estimates in general. Questions about these contracts need paragraph 55.")))
        found["passage-report-stale.json"] = text(pilot.decide(PRIYA, rebidding, outcome="keep",
                                                               reason="It answers the question.", state=seen))
        found["feedback-mine-ranked-lower.json"] = get("/api/feedback", ANA, evidence_id=PARAGRAPH_54, run_id=ana)
        found["passage-report-decided.json"] = get(f"/api/passage-reports/{rebidding}", DANIEL)
        found["passage-reports-decided.json"] = get("/api/passage-reports", DANIEL)
        found["retrieval-me-passage-reviewer-decided.json"] = get("/api/lessons/me", DANIEL)
        pilot.later(minutes=10)
        pilot.decide(DANIEL, clearances, outcome="keep", reason="Paragraph 55 is the right one for this question.")
        found["feedback-mine-kept.json"] = get("/api/feedback", PRIYA, evidence_id=PARAGRAPH_55, run_id=priya)
        pilot.later(minutes=10)
        found["passage-report-reopened.json"] = text(pilot.request(
            "POST", f"/api/passage-reports/{clearances}/reopen", DANIEL,
            {"reason": "Priya's question was about the clearances, so I want a second look."}))

        # Judging: Mei and Tomas grade query 2, and Mei starts query 1.
        found["judging-queries-start.json"] = get("/api/judging/queries", MEI)
        found["judging-query.json"] = get(f"/api/judging/queries/{QUERY_1}", MEI)
        pool = [passage["passage_id"] for passage in pilot.request("GET", f"/api/judging/queries/{QUERY_2}", MEI).json()["passages"]]
        for who, judge in ((MEI, "mei"), (TOMAS, "tomas")):
            for passage, grade in grades(pool, judge).items():
                saved = pilot.request("PUT", f"/api/judging/queries/{QUERY_2}/passages/{passage}", who, {"grade": grade})
                if judge == "mei" and passage == sorted(pool)[0]:
                    found["judging-grade-saved.json"] = text(saved)
            pilot.later(minutes=30)
        first = [passage["passage_id"] for passage in pilot.request("GET", f"/api/judging/queries/{QUERY_1}", MEI).json()["passages"]]
        for passage in first[:4]:
            pilot.request("PUT", f"/api/judging/queries/{QUERY_1}/passages/{passage}", MEI, {"grade": "partly"})
        found["judging-query-progress.json"] = get(f"/api/judging/queries/{QUERY_1}", MEI)
        found["judging-query-locked.json"] = get(f"/api/judging/queries/{QUERY_2}", MEI)
        found["judging-grade-locked.json"] = text(pilot.request(
            "PUT", f"/api/judging/queries/{QUERY_2}/passages/{sorted(pool)[0]}", MEI, {"grade": "not_relevant"}))
        found["judging-queries.json"] = get("/api/judging/queries", MEI)
        found["retrieval-me-judge-after.json"] = get("/api/lessons/me", MEI)
        found["judging-queries-both.json"] = get("/api/judging/queries", MEI, show="finished_by_both")
        found["judging-query-not-found.json"] = get("/api/judging/queries/nq-nothing", MEI)
    finally:
        pilot.close()

    scale = Loop(FIXTURE_DB, folder / "scale", mode="scale")
    try:
        runs = {}
        for who in (ANA, KOFI, SARA):
            runs[who["X-Forwarded-Email"]] = scale.ask(who)
            scale.report(who, runs[who["X-Forwarded-Email"]])
        withdrawn = scale.ask(LEELA)
        sent = scale.report(LEELA, withdrawn, kind="not_useful", evidence_id=PARAGRAPH_55).json()["my_report"]
        found["feedback-withdrawn.json"] = text(scale.request("POST", f"/api/feedback/{sent['report_id']}/withdraw", LEELA))
        scale.later(days=3)
        scale.weekly()
        found["passage-reports-audit.json"] = text(scale.request("GET", "/api/passage-reports", DANIEL))
        found["retrieval-me-passage-reviewer-audit.json"] = text(scale.request("GET", "/api/lessons/me", DANIEL))
        [audit] = scale.request("GET", "/api/passage-reports", DANIEL).json()["groups"]["you"]
        found["passage-report-audit.json"] = text(scale.request("GET", f"/api/passage-reports/{audit['group_id']}", DANIEL))
        found["feedback-mine-by-agreement.json"] = text(scale.request(
            "GET", "/api/feedback", KOFI, params={"evidence_id": PARAGRAPH_54, "run_id": runs["kofi.example@worldbank.org"]}))
    finally:
        scale.close()
    return found


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        for name, body in answers(Path(folder)).items():
            (OUT / name).write_text(body)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
