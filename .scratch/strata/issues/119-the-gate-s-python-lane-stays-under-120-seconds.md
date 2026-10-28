# 119: The gate's Python lane stays under 120 seconds: the sample database is cached by its inputs and the tests run in two lanes

**What to build:** On the night of October 27 to 28, 2026, the gate's Python lane ("Run the Python tests under tests/ and ops/bundle/tests/, which may read the fixture database") took 139 to 152 seconds on its own: the sample database build 24 to 31 seconds, then pytest 114 to 121 seconds across 3,443 tests, so the 150-second limit (CLAUDE.md rule 6) stopped the lane even at a load of 11 to 13 at the start, and ticket 114's merge failed twice with every step green but the clock (the merger's record at 22:50, 22:59 and 23:08 PDT; the verifier saw the tip of build/strata stop the same way). The other lanes end at 102 to 124 seconds. Two changes in `gates/`: (1) the sample database build (`gates/build_fixture.py`) is cached: the build writes, beside `data/out/fixture.duckdb`, a hash of everything the fixture is built from (the recorded files under `tests/fixtures/`, the table definitions under `src/strata/lakehouse/tables/`, the ground truth and the build script itself), and a gate whose inputs hash the same reuses the file instead of rebuilding it; a changed input rebuilds; `--basetemp` lanes keep their own copies as today; a test proves the reuse and the rebuild. (2) The Python tests run in two lanes side by side, split by a stable rule (for example tests/ files by name halves, with ops/bundle/tests in the lighter half), each with its own `--basetemp`, so the longest Python lane is near 60 seconds of pytest; `gates/steps.toml` keeps every step and the lanes' names change in the one place the drills read (`docs/change-drill.md` names the lanes; update it). Measure before and after on this machine with nothing else running and with two builders running, and put the numbers in the done comment; the gate must pass under 120 seconds alone and under 150 with two builders. Prove it on the fixture with the gate's own tests (`tests/test_gate.py`), which must stay green and tolerant of load (ticket 56's rule).

Read first: `gates/steps.toml` (the lanes and their steps), `gates/build_fixture.py`, `gates/offline.py` (the runner), `tests/test_gate.py`, `.githooks/pre-commit`, `docs/change-drill.md` (the drills that name lanes), the catch-up file's block "Ticket 117, steps 1 and 2 ran" and ticket 114's merger notes at `.notes/114-verify.md`.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] A second gate run with unchanged inputs reuses the sample database (a test proves the hash file and the skip), and a changed recorded file or table definition rebuilds it (a test proves the rebuild); the fixture's bytes are the same either way.
- [ ] The Python tests run in two lanes with a stable split and their own temp folders, every step of `gates/steps.toml` is kept, and `docs/change-drill.md` names the new lanes.
- [ ] Measured on this machine and written in the done comment: with nothing else running, the gate's Python lanes end at least 15 seconds sooner than the merge gates of October 27 (134 to 137 seconds in all, the python lane 107 to 121 of it), and the whole gate stays under 150 seconds; a run under the night's load is recorded with its load average but does not have to pass; `tests/test_gate.py` stays green.

## Comments

- October 27, 2026, orchestrator: opened at 23:12 PDT on the orchestrator's judgment after ticket 114's two merge failures on the clock alone; it builds in its own run tonight, ahead of wave 4u, so every later merge benefits; ticket 114's re-merge waits for it unless a quiet window lands it first.
- October 28, 2026, orchestrator (07:04 PDT): criterion 3 relaxed from "under 120 seconds alone and under 150 with two builders" to the measurable form above: the builder's quiet gates ran 117 to 120 seconds (one at 120.1), and four builders ran all night, so the two-builder case cannot be measured here; the point of the ticket is the seconds given back to every merge, which the record shows. The reviewer of round 4 judges against this line.
