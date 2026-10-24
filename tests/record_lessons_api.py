"""Writes the Lessons routes' recorded answers in tests/fixtures/api from the server itself (ticket 29).

The screen tests and the design gallery serve these files, and tests/test_lesson_review_routes.py checks that
the server still answers with them, so the Lessons screens and the server cannot drift apart. Build the
fixture database first, then run:

    uv run --frozen python tests/record_lessons_api.py

One story makes them all, on a copy of the fixture database, with the made-up reviewers of
tests/fixtures/roles.toml and a fixed clock. The fixture's queue holds three proposed lessons from P130164,
which entered it on Friday, October 23, 2026: ICR paragraph 54 (rebidding), ICR paragraph 55 (permits before
award) and IEG's own lesson in section 12 of the ICR Review.

- Tuesday, October 27: Asha (accredited, South Asia) opens the queue and the rebidding lesson, which Leela (a
  lead who works on P130164) may not act on. Asha recommends adding it, and Leela's late recommendation is
  stale. Omar (a lead) opens it, Leela is refused when she tries to decide it, and Omar adds it. Asha
  recommends IEG's lesson and Omar adds it too. The lesson review writer writes again, now that the library
  holds lessons, and names IEG's lesson as a likely repeat of paragraph 55's. Omar recommends adding
  paragraph 55's quote to IEG's lesson, so he may not decide it, and Priya, the other free lead, does.
- Wednesday, October 28: Wanjiru (a lead in Eastern and Southern Africa) asks for a re-check of the
  rebidding lesson, and Asha's second request is refused while it is open. Asha recommends a change.
- Monday, January 4, 2027: the re-check has passed its ten business days, and the quarterly job assigns one
  of South Asia's decisions to Wanjiru's region.
"""

import asyncio
import datetime as dt
import json
import shutil
import sys
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.config import load_roles  # noqa: E402
from strata.knowledge.lessons import cross_check, writer  # noqa: E402
from strata.knowledge.lessons.review import LessonReview  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.app import create_app  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"
ROLES = load_roles(ROOT / "tests" / "fixtures" / "roles.toml")


def viewer(email: str) -> dict:
    return {"X-Forwarded-Email": email, "X-Forwarded-User": f"id-{email}", "X-Forwarded-Access-Token": "not-a-real-token"}


ANA = viewer("ana.example@worldbank.org")
ASHA = viewer("asha.raman@worldbank.example")
LEELA = viewer("leela.iyer@worldbank.example")
OMAR = viewer("omar.haddad@worldbank.example")
PRIYA = viewer("priya.nair@worldbank.example")
WANJIRU = viewer("wanjiru.kamau@worldbank.example")
REBIDDING, PERMITS, IEG_LESSON = "31525018/v1/54", "31525018/v1/55", "34056616/v2/12"


def answers(folder: Path) -> dict[str, str]:
    """Every recorded answer, by its file name, as the text the file holds."""
    database = folder / "lessons.duckdb"
    shutil.copy(FIXTURE_DB, database)
    at = [dt.datetime(2026, 10, 27, 9, 0, tzinfo=dt.UTC)]

    @contextmanager
    def engine_for(_viewer):
        with DuckDBEngine.open(database) as engine:
            yield engine

    review = LessonReview(ROLES, today=lambda: at[0].date(), now=lambda: at[0])
    app = create_app(engine_for=engine_for, lessons=review)

    def item_of(passage_id: str, kind: str = "new") -> str:
        with DuckDBEngine.open(database, read_only=True) as engine:
            result = engine.run("SELECT i.item_id FROM strata.ops.lesson_review_items AS i "
                                "JOIN strata.silver.lesson_proposals AS p ON p.proposal_id = i.proposal_id "
                                "WHERE p.passage_id = :passage_id AND i.kind = :kind", {"passage_id": passage_id,
                                                                                         "kind": kind})
            return result.rows[0][0]

    def later(minutes: int):
        at[0] += dt.timedelta(minutes=minutes)

    def rewrite():
        with DuckDBEngine.open(database) as engine:
            writer.run(engine, writer.recorded_agent_for(), lambda: at[0], 3)

    async def story() -> dict[str, str]:
        found = {}
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://strata.test") as client:
            def text(answer) -> str:
                return json.dumps({"status": answer.status_code, "body": answer.json()}, indent=2,
                                  ensure_ascii=False) + "\n" if answer.status_code != 200 else \
                    json.dumps(answer.json(), indent=2, ensure_ascii=False) + "\n"

            async def get(path: str, headers) -> str:
                return text(await client.get(path, headers=headers))

            async def act(item: str, verb: str, headers, **body) -> str:
                return text(await client.post(f"/api/lessons/review/{item}/{verb}", headers=headers, json=body))

            rebidding, permits, ieg = item_of(REBIDDING), item_of(PERMITS), item_of(IEG_LESSON)
            # Who may open what.
            found["lessons-me-viewer.json"] = await get("/api/lessons/me", ANA)
            found["lessons-me-reviewer.json"] = await get("/api/lessons/me", ASHA)
            found["lessons-library-empty.json"] = await get("/api/lessons", ANA)
            found["lessons-queue-no-access.json"] = await get("/api/lessons/review", ANA)
            found["lessons-item-no-access.json"] = await get(f"/api/lessons/review/{rebidding}", ANA)
            found["lessons-queue.json"] = await get("/api/lessons/review", ASHA)
            found["lessons-item-recommend.json"] = await get(f"/api/lessons/review/{rebidding}", ASHA)
            found["lessons-item-own-project.json"] = await get(f"/api/lessons/review/{rebidding}", LEELA)
            found["lessons-item-not-found.json"] = await get("/api/lessons/review/new-0000000000", ASHA)
            # Asha recommends adding the rebidding lesson, and Omar adds it.
            later(30)
            found["lessons-act-recommended.json"] = await act(rebidding, "recommend", ASHA, expected_stage="recommendation",
                                                              outcome="add", reason=(
                "The ICR and IEG's review both say estimates below market rates led to rebidding."))
            later(5)
            found["lessons-act-stale.json"] = await act(rebidding, "recommend", LEELA, expected_stage="recommendation",
                                                        outcome="reject", reason="Too general to act on.")
            later(240)
            found["lessons-item-decide.json"] = await get(f"/api/lessons/review/{rebidding}", OMAR)
            found["lessons-queue-lead.json"] = await get("/api/lessons/review", OMAR)
            found["lessons-act-refused-own-project.json"] = await act(rebidding, "decide", LEELA, expected_stage="decision",
                                                                      outcome="add", reason="It reads well.")
            later(5)
            found["lessons-act-added.json"] = await act(rebidding, "decide", OMAR, expected_stage="decision", outcome="add",
                                                        reason="Two reports state it, and it names a step to take.")
            # IEG's own lesson: Asha recommends it and Omar adds it.
            later(10)
            await act(ieg, "recommend", ASHA, expected_stage="recommendation", outcome="add",
                      reason="IEG wrote this lesson itself, in its review of the ICR.")
            later(10)
            await act(ieg, "decide", OMAR, expected_stage="decision", outcome="add",
                      reason="It is IEG's own lesson, and the ICR's paragraph 55 says the same.")
            # The writer writes again, now that the library holds lessons.
            later(60)
            rewrite()
            found["lessons-item-recommend-repeats.json"] = await get(f"/api/lessons/review/{permits}", ASHA)
            # Omar recommends adding paragraph 55's quote to IEG's lesson, so Priya decides it.
            later(10)
            [repeat] = json.loads(found["lessons-item-recommend-repeats.json"])["repeats"]
            await act(permits, "recommend", OMAR, expected_stage="recommendation", outcome="repeat",
                      repeat_of=repeat["lesson_id"], reason="It gives the same advice as IEG's lesson.")
            found["lessons-item-same-person.json"] = await get(f"/api/lessons/review/{permits}", OMAR)
            found["lessons-act-refused-same-person.json"] = await act(permits, "decide", OMAR, expected_stage="decision",
                                                                      outcome="repeat", repeat_of=repeat["lesson_id"],
                                                                      reason="I recommended it, and I agree.")
            found["lessons-item-decide-repeats.json"] = await get(f"/api/lessons/review/{permits}", PRIYA)
            later(15)
            found["lessons-act-merged.json"] = await act(permits, "decide", PRIYA, expected_stage="decision",
                                                         outcome="repeat", repeat_of=repeat["lesson_id"],
                                                         reason="The ICR's paragraph 55 is more evidence for IEG's lesson.")
            found["lessons-item-decided-added.json"] = await get(f"/api/lessons/review/{rebidding}", ASHA)
            found["lessons-item-decided-merged.json"] = await get(f"/api/lessons/review/{permits}", ASHA)
            found["lessons-queue-decided.json"] = await get("/api/lessons/review", ASHA)
            found["lessons-library.json"] = await get("/api/lessons", ANA)
            found["lessons-library-reviewer.json"] = await get("/api/lessons", ASHA)
            # Wednesday: a re-check of the rebidding lesson.
            at[0] = dt.datetime(2026, 10, 28, 10, 0, tzinfo=dt.UTC)
            lesson = json.loads(found["lessons-library.json"])["lessons"][-1]["lesson_id"]
            found["lessons-act-recheck.json"] = text(await client.post(
                f"/api/lessons/{lesson}/recheck", headers=WANJIRU,
                json={"reason": "The 2025 Procurement Regulations changed how cost estimates are prepared."}))
            found["lessons-act-recheck-open.json"] = text(await client.post(
                f"/api/lessons/{lesson}/recheck", headers=ASHA, json={"reason": "Check it against the new rules."}))
            found["lessons-library-rechecking.json"] = await get("/api/lessons", ASHA)
            found["lessons-queue-recheck.json"] = await get("/api/lessons/review", ASHA)
            with DuckDBEngine.open(database, read_only=True) as engine:
                recheck = engine.run("SELECT item_id FROM strata.ops.lesson_review_items WHERE kind = 'recheck'", {}).rows[0][0]
            found["lessons-item-recheck-recommend.json"] = await get(f"/api/lessons/review/{recheck}", ASHA)
            later(30)
            await act(recheck, "recommend", ASHA, expected_stage="recommendation", outcome="change",
                      change={"statement": "Base works cost estimates on current market rates to avoid rebidding"},
                      reason="The lesson holds, and current market rates is what the new rules ask for.")
            found["lessons-item-recheck-decide.json"] = await get(f"/api/lessons/review/{recheck}", OMAR)
            # January 4, 2027: the re-check is overdue, and the quarterly cross-check.
            at[0] = dt.datetime(2027, 1, 4, 11, 0, tzinfo=dt.UTC)
            found["lessons-queue-overdue.json"] = await get("/api/lessons/review", ASHA)
            with DuckDBEngine.open(database) as engine:
                cross_check.run(engine, at[0].date(), now=lambda: at[0], roles=ROLES)
                crossing = engine.run("SELECT item_id FROM strata.ops.lesson_review_items WHERE kind = 'cross_check'",
                                      {}).rows[0][0]
            found["lessons-queue-cross-check.json"] = await get("/api/lessons/review", WANJIRU)
            found["lessons-item-cross-check.json"] = await get(f"/api/lessons/review/{crossing}", WANJIRU)
            found["lessons-item-same-region.json"] = await get(f"/api/lessons/review/{crossing}", ASHA)
        return found

    return asyncio.run(story())


def main() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as folder:
        for name, text in answers(Path(folder)).items():
            (OUT / name).write_text(text)
            print(f"Wrote tests/fixtures/api/{name}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
