# 50: Gate lanes, so the offline gate stays under two minutes as the tests grow

**What to build:** The offline gate runs its six steps one after another, and the Python tests alone take about 63 of its 72 to 80 seconds. Most of that came with ticket 03's wizard and day-one tests. Tickets 02, 04 and 05 each add 10 to 15 seconds, so build/strata will sit near 110 of the 120 seconds that CLAUDE.md rule 6 allows once they land, and every P1 ticket adds tests on top. This ticket makes the gate run steps that do not depend on each other at the same time, so the limit holds with room to grow. The spec already allows it: "If the screen tests threaten that budget they run in parallel workers; they never leave the gate."

`gates/steps.toml` gains an optional `lane` key. A step with no lane runs alone, in the file's order, and waits for everything before it. A run of neighbouring steps that have lanes runs each lane's steps in order, with the lanes side by side. The secret scan stays first and alone. The fixture build stays ahead of the Python tests that read the fixture database, in the same lane. The Python tests split by path into two lanes: the gate, server, fixture and ground-truth tests under `tests/`, and the wizard and day-one tests under `ops/`. The web build and the Playwright tests form another lane. The runner still prints every step's name and time, prints a failed step's full output, stops every other lane when one step fails, keeps the limit over the whole run, keeps the Markdown-only skip, and keeps the check for unstaged changes. If splitting by path does not bring the gate under 45 seconds, the slow lane runs pytest with pytest-xdist, pinned in `pyproject.toml` and `uv.lock`, and any test that cannot share a process is marked to run alone.

Read first: CLAUDE.md rule 6; `gates/offline.py`; `gates/steps.toml`; `tests/test_gate.py` (its `repo` fixture builds a throwaway repo, which is how the new tests should work too); `docs/agents/areas/ops.md`; the spec's paragraph that starts "The gates use the seams as follows".

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P1
**Design review:** no

- [ ] Two steps in different lanes run at the same time: a throwaway steps file with two steps that each wait 2 seconds finishes in under 3.5 seconds when they are in different lanes, and takes over 4 seconds when they share a lane.
- [ ] A step with no lane is a barrier: each step in a throwaway steps file appends its name to one log file, and the log shows that a step without a lane ran only after every lane before it finished, and that every step after it waited for it.
- [ ] When a step in one lane fails, the gate stops the other lanes within a few seconds, prints the failing step's full output and the step's name, and exits 1; the test shows that the other lane's long step is no longer running and that the gate finished well before that step would have.
- [ ] The limit covers the whole run across all lanes: when the lanes together run past it, every lane is stopped and the gate prints the limit message it prints today.
- [ ] Every existing gate test passes, with only `gates/steps.toml` and the tests' throwaway steps files changed for the lane key: the Markdown-only skip, the unstaged-changes check, the code 127 message, the `show` output, the secret scan, the history scan and the merge tests.
- [ ] The fixture database is built before any Python test reads it, proven by the barrier or lane order in `gates/steps.toml` and a test that reads the file's order.
- [ ] `.githooks/pre-commit` on this branch, with build/strata merged in, prints "The gate passed in" a time under 45 seconds, and each step's own time still prints.
- [ ] `gates/steps.toml`'s comment explains the lane key in plain words, and README's gate section and `docs/agents/areas/ops.md` say how to add a step to a lane.

## Comments

- October 23, 2026, orchestrator: Opened during wave 2 of the build. The timings above come from the reviewers' and verifiers' gate runs in `.notes/` (Python tests 62.4 to 67.1 seconds of 71.8 to 78.9 seconds). Build on build/strata at 79a3ab3. This ticket merges right after tickets 02, 04 and 05 land and before any P1 ticket merges, so the first P1 merge already has the room. Keep the new tests short (waits of about 2 seconds), because they run inside the gate too.
