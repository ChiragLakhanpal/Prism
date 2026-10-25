"""Writes the Following page's and the mission brief's recorded answers in tests/fixtures/api from the server itself
(ticket 37).

The screen tests serve these files from their mocked API, and tests/test_following.py checks that the server still
answers with the real ones, so the screens and the server cannot drift apart. Build the fixture database first, then
run:

    uv run --frozen python tests/record_following_api.py

One story makes the real ones, on the fixture database as of October 22, 2026, ticket 09's as-of date (the mission
brief's draft as of October 23, as tests/test_drafts.py writes drafts): Ana, World Bank staff on the Kenya water
team, follows P156634 and P130164, opens Following, opens it as of June 30, 2024, and writes a mission brief on
P156634, which she checks and exports. Ben, also staff, follows nothing. Cy is not staff.

The states the fixture cannot reach (a Watch row, a Not checked row, a partly checked row, a pipeline row, many quiet
rows, a stored track record) are made up from the real answer, each named following-made-up-*.json and saying so in
its made_up field. They are never served as findings: the screen tests use them for layout and states only.
"""

import asyncio
import copy
import datetime as dt
import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from strata.agent.scripted import WRITER_CASES, ScriptedAgent, load_cases  # noqa: E402
from strata.config import load_roles  # noqa: E402
from strata.drafts.store import DraftStore  # noqa: E402
from strata.lakehouse import catalog  # noqa: E402
from strata.lakehouse.engine import DuckDBEngine  # noqa: E402
from strata.server.access import Access, StaticGroups  # noqa: E402
from strata.server.app import create_app  # noqa: E402
from strata.server.evidence import OpenedLog  # noqa: E402
from strata.server.following import FollowStore  # noqa: E402

FIXTURE_DB = ROOT / "data" / "out" / "fixture.duckdb"
OUT = ROOT / "tests" / "fixtures" / "api"


def viewer(number: int, name: str) -> dict:
    return {"X-Forwarded-Email": f"{name.lower()}.example@worldbank.org", "X-Forwarded-Preferred-Username": f"{name} Example",
            "X-Forwarded-User": f"40{number}@1984", "X-Forwarded-Access-Token": f"token-for-{name.lower()}-only"}


ANA, BEN, CY = viewer(21, "Ana"), viewer(22, "Ben"), viewer(23, "Cy")
GROUPS = {"4021@1984": ["users", "strata-team-kenya-water"], "4022@1984": ["users"], "4023@1984": []}


def text(response: httpx.Response) -> str:
    if response.headers.get("content-type", "").startswith("text/event-stream"):
        return response.text
    return json.dumps(response.json(), indent=1, ensure_ascii=False) + "\n"


def answers(folder: Path, fixture_db: Path = FIXTURE_DB, files: dict | None = None) -> dict[str, str]:
    """The real recorded answers, by file name, from one story on a fresh app state in folder. files, when given,
    gets the exported Word file's name and bytes too, which no screen serves."""
    state_db = folder / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(_viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    written = load_cases(WRITER_CASES)["mission-brief-p156634"]
    numbers = iter(range(1, 100))
    clock = iter(dt.datetime(2026, 10, 23, 14, minute, tzinfo=dt.UTC) for minute in range(60))
    days = {"today": dt.date(2026, 10, 22)}
    state = lambda: DuckDBEngine.open(state_db)  # noqa: E731
    app = create_app(engine_for=reading, drafts=DraftStore(state), opened=OpenedLog(state), follows=FollowStore(state),
                     writers=lambda kind: ScriptedAgent(written), access=Access(load_roles(), StaticGroups(GROUPS)),
                     today=lambda: days["today"], now=lambda: next(clock), new_draft_id=lambda: f"draft-{next(numbers):04d}",
                     new_run_id=lambda: "run-0001")

    async def story() -> dict[str, str]:
        found = {}
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://strata.test") as client:
            async def get(name, path, headers=ANA, method="GET", **options):
                found[name] = text(await client.request(method, path, headers=headers, **options))

            await get("me-staff.json", "/api/me")
            await get("me-not-staff.json", "/api/me", CY)
            await get("follow-off.json", "/api/projects/P156634/follow")
            await get("follow-on.json", "/api/projects/P156634/follow", method="PUT")
            await client.put("/api/projects/P130164/follow", headers=ANA)
            await get("following-p156634.json", "/api/following")
            await get("following-asof-2024-06-30.json", "/api/following?asof=2024-06-30")
            await get("following-empty.json", "/api/following", BEN)
            await get("following-not-staff.json", "/api/following", CY)
            days["today"] = dt.date(2026, 10, 23)
            await get("drafts-write-mission-brief.sse", "/api/drafts", method="POST",
                      json={"kind": "mission_brief", "project_id": "P156634", "idempotency_key": "brief-1"})
            await get("drafts-mission-brief-draft.json", "/api/drafts/draft-0001")
            await get("following-with-brief.json", "/api/following")
            await get("drafts-mission-brief-checked.json", "/api/drafts/draft-0001/check", method="POST",
                      json={"expected_state": "draft"})
            await get("drafts-mission-brief-exported.json", "/api/drafts/draft-0001/export", method="POST",
                      json={"expected_state": "checked"})
            if files is not None:
                exported = json.loads(found["drafts-mission-brief-exported.json"])
                for made in exported["export"]["files"]:
                    if made["name"].endswith(".docx"):
                        word = await client.get(f"/api/drafts/draft-0001/files/{made['name']}", headers=ANA)
                        files[made["name"]] = word.content
        return found

    return asyncio.run(story())


def made_up(real: dict) -> dict[str, dict]:
    """The states the fixture cannot reach, made up from the real answer, each saying so."""
    p156634, p130164 = (next(entry for entry in real["projects"] if entry["project"]["project_id"] == pid)
                        for pid in ("P156634", "P130164"))

    def project(pid: str, name: str, closing: str, status: str, **changes) -> dict:
        entry = copy.deepcopy(p156634)
        entry["project"].update({"project_id": pid, "project_name": name, "closing_date": closing,
                                 "evidence_id": f"strata.gold.project:{pid}"})
        entry.update({"status": status, "mission_brief": None, **changes})
        return entry

    watch = project("P900001", "Made-up Rural Water Supply Project", "2027-06-30", "watch",
                    rows=[row for row in p156634["rows"] if row["check"] == "closing_moves"],
                    counts={**p156634["counts"], "signals": 1})
    partly = project("P900002", "Made-up Urban Sanitation Project", "2028-03-31", "no_signals", rows=[],
                     counts={"signals": 0, "strong": 0, "ran": 5, "checks": 7, "not_ran": 2},
                     checks=[{**check, "fired": False, "strong": False,
                              "ran": check["key"] not in ("restructured", "isr_lowered"),
                              "missing": "no_isr" if check["key"] in ("restructured", "isr_lowered") else None}
                             for check in p156634["checks"]])
    unchecked = project("P900003", "Made-up Coastal Roads Project", "2029-12-31", "not_checked", rows=[],
                        counts={"signals": 0, "strong": 0, "ran": 0, "checks": 7, "not_ran": 7},
                        checks=[{**check, "ran": False, "fired": False, "strong": False, "missing": "no_plans"}
                                for check in p156634["checks"]])
    pipeline = project("P900004", "Made-up Irrigation Project", None, "pipeline", rows=[], checks=[],
                       counts={"signals": 0, "strong": 0, "ran": 0, "checks": 7, "not_ran": 7})
    pipeline["project"]["closing_kind"] = "pipeline"
    quiet = [project(f"P9001{n:02d}", f"Made-up Quiet Project {n}", f"2028-0{1 + n % 9}-30", "no_signals", rows=[],
                     counts={"signals": 0, "strong": 0, "ran": 7, "checks": 7, "not_ran": 0},
                     checks=[{**check, "fired": False, "strong": False} for check in p156634["checks"]])
             for n in range(1, 11)]
    strong = copy.deepcopy(p156634)
    strong["rows"][0]["strong"] = True
    strong["counts"]["strong"] = 1
    strong["mission_brief"] = {"draft_id": "draft-0001", "created_at": "2026-10-23T14:02:00+00:00"}

    def answer(entries: list[dict], note: str, **changes) -> dict:
        counts = {"total": len(entries), "checked": 0, "needs_a_look": 0, "watch": 0, "not_checked": 0, "no_signals": 0,
                  "closed": 0, "pipeline": 0, "ended": 0, "folded": 0, "shown": 0, "partly": 0, "fully": 0,
                  "partly_folded": 0}
        for entry in entries:  # counted here once, by hand, for the made-up answers only
            status = entry["status"]
            key = "closed" if status in ("closed", "dropped") else status
            counts[key] += 1
            counts["ended"] += 1 if status in ("closed", "dropped", "pipeline") else 0
            folded = status in ("no_signals", "closed", "pipeline", "dropped")
            counts["folded" if folded else "shown"] += 1
            if status not in ("not_checked", "closed", "pipeline", "dropped"):
                counts["checked"] += 1
                partial = entry["counts"]["ran"] < entry["counts"]["checks"]
                counts["partly" if partial else "fully"] += 1
                counts["partly_folded"] += 1 if partial and folded else 0
        return {"made_up": note, **real, "projects": entries, "counts": counts, **changes}

    track = {"run_id": "signals_track_record-made-up", "mlflow_run_id": "made-up", "ran_on": "2026-10-22",
             "dates": ["2023-06-30", "2024-06-30", "2025-06-30"], "window_months": 12, "cohort": 64,
             "outcomes_through": "2026-06-30", "min": 20,
             "status": {"needs_a_look": {"n": 14, "k": 9, "few": True}, "watch": {"n": 26, "k": 11, "few": False},
                        "no_signals": {"n": 38, "k": 7, "few": False}},
             "checks": {key: {"n": n, "k": k, "few": n < 20} for key, n, k in (
                 ("completion_passed", 21, 12), ("above_estimate", 9, 4), ("late_direct", 3, 2), ("closing_moves", 30, 15),
                 ("restructured", 6, 3), ("isr_lowered", 11, 5), ("disbursement", 0, 0))}}
    return {
        "following-made-up-states.json": answer(
            [strong, watch, unchecked, partly, p130164, pipeline], "Made up from following-p156634.json: a strong signal, "
            "a Watch row, a Not checked row, a partly checked quiet row and a pipeline row, for layout and states only."),
        "following-made-up-many-quiet.json": answer(
            [p156634, *quiet], "Made up from following-p156634.json: ten quiet projects, for the fold only."),
        "following-made-up-all-quiet.json": answer(
            quiet[:3], "Made up from following-p156634.json: three quiet projects and nothing to show."),
        "following-made-up-one.json": answer([watch], "Made up from following-p156634.json: one project, worth watching."),
        "following-made-up-track-record.json": answer(
            [p156634, p130164], "Made up from following-p156634.json: a stored track record, for its layout only.",
            track_record=track),
    }


def main() -> int:
    if not FIXTURE_DB.exists():
        print("Build the fixture database first: uv run --frozen python gates/build_fixture.py")
        return 2
    with tempfile.TemporaryDirectory() as folder:
        written = answers(Path(folder))
    for name, body in written.items():
        (OUT / name).write_text(body)
        print(f"Wrote tests/fixtures/api/{name}.")
    real = json.loads(written["following-p156634.json"])
    for name, body in made_up(real).items():
        (OUT / name).write_text(json.dumps(body, indent=1, ensure_ascii=False) + "\n")
        print(f"Wrote tests/fixtures/api/{name}, made up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
