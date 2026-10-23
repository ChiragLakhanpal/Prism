# 51: Python lane workers, so the gate's slowest lane keeps room as the tests under tests/ grow

**What to build:** The offline gate runs in lanes since ticket 50, and the python lane sets its total. That lane runs `pytest tests ops/bundle/tests` in one process: 27.5 of 28.9 seconds right after ticket 50 landed, 31.5 of 33.4 seconds with ticket 08, and 48.0 seconds on ticket 07's branch. Every P1 ticket adds tests under `tests/`, and the whole gate must stay under the 120 seconds that CLAUDE.md rule 6 allows. The ops lane already runs its wizard tests under six pytest-xdist workers. This ticket gives the python lane's pytest step workers the same way, and makes every test under `tests/` and `ops/bundle/tests/` safe to run beside the others: the tests open the fixture database read-only, tests that build a database use `tmp_path`, and the gate tests build throwaway repos. A test that cannot share a process gets an xdist group mark with a comment that says why, and the step runs with `--dist loadgroup`. The fixture build stays ahead of the tests in the same lane. `pytest-xdist` 3.8.0 is already pinned in `pyproject.toml` and `uv.lock`, so neither file changes.

Read first: CLAUDE.md rule 6; `gates/steps.toml` and its comment on lanes; `tests/test_gate.py` (the steps-file checks, `FIXTURE_READERS`); the root `conftest.py` (the network guard, which ticket 50 moved there so workers load it); `tests/conftest.py`; `docs/agents/areas/ops.md`; ticket 50's notes in `.notes/50-review-r3.md` and `.notes/50-verify-r3.md`.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P1
**Design review:** no

- [ ] The python lane's pytest step in `gates/steps.toml` runs with pytest-xdist workers, the fixture build still runs before it in the same lane, and every steps-file check in `tests/test_gate.py` passes with the new run list.
- [ ] Ten runs in a row of the step's command pass, each collecting the same test IDs as a bare `pytest --co tests ops/bundle/tests`, with none dropped and none repeated, and a test that opens a network socket still fails inside a worker with the guard's message.
- [ ] No test under `tests/` or `ops/bundle/tests/` writes to `data/out/` or to any other path that two workers could share, sets an environment variable the others read, or changes the working directory; each test that writes uses `tmp_path` or a throwaway repo. A test that cannot share a process carries an xdist group mark with a comment that says why.
- [ ] The gate, by hand on this branch with build/strata merged in, passes three times in a row, and the python lane's time is at least a third lower than the same tree in one process; the report gives both times and the worker count.
- [ ] `gates/steps.toml`'s comment on the step, README's gate section and `docs/agents/areas/ops.md` say how many workers the step uses and what to do when the lane gets slow again; `pyproject.toml` and `uv.lock` are unchanged.

## Comments

- October 23, 2026, orchestrator: opened after wave 3, in which tickets 50 and 08 landed. The timings above come from the merger's and the verifiers' gate runs in `.notes/` and on build/strata at 5993efc. The PM asked for workers on this lane before it passes 60 seconds. This is enabling work the spec allows ("If the screen tests threaten that budget they run in parallel workers; they never leave the gate"), not new scope. Ticket 02 lands in the same wave and also changes `gates/steps.toml` (a lint step and a gallery build in the web lane); whichever merges second keeps both changes. Ticket 50 left two small leftovers that belong here if they are cheap: `gates/offline.py` starts the lane threads before its `try`, so a Ctrl-C between two starts leaves a lane running, and `tests/test_offline.py` ends with a blank line. Dispatched to an implementer in its own worktree on branch strata/51-python-lane-workers.
