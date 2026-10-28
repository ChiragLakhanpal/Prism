# 124: The gate costs a third less processor time, starting with the screen tests, so it ends under two minutes on this machine

**What to build:** Ticket 119 (October 28, 2026) kept the sample database between gates and split the Python tests in two lanes, and quiet gates now end at 119 to 125 seconds against 134 to 137 before; under the day's load of two or three builders they still reach the 150-second limit about one run in three, because the gate costs about 1,100 processor-seconds on 16 processors: about 810 in the Playwright lanes (web-1 and web-2: one axe scan per page, state and width, and pages that load every chunk) and the rest in the two Python halves, whose costliest files `uv run --frozen pytest --durations=0 --shard=1/2 tests ops/bundle/tests` (and `2/2`) list on a quiet machine. CLAUDE.md's rule 6 expects the polish pass to bring the gate back toward two minutes. Cut the gate's processor time by at least a third without dropping a check that proves a criterion: run one axe scan per page and width in the states that change the page's structure, and reuse one scan for states that change only text; load each page once per spec file instead of once per test where the tests read the same page; give the heaviest Python modules (the `nights` fixture of tests/test_nightly_delta.py, test_nightly, test_fetch, ops/bundle/tests/test_check's in-memory catalog) a session-scoped fixture or a smaller recorded slice; keep every test that a ticket's acceptance criterion names (the reviewer's and verifier's notes say which). Measure before and after with the gate's own runner on a quiet machine and under two builders, and write the numbers in the done comment with the processor-seconds per lane (`/usr/bin/time` around `.githooks/pre-commit`); record the new budget in `gates/steps.toml` and the ops brief, where ticket 119's record lives. Prove it on the fixture: the gate's own tests stay green, every spec still runs (the counts per lane in the done comment), and the full gate passes under 120 seconds quiet and under 150 with two builders running.

Read first: `gates/steps.toml` and `docs/agents/areas/ops.md` (ticket 119's timing record), `gates/offline.py`, `web/tests/` (the axe helper and the per-page specs), `tests/conftest.py` (the shards), `tests/test_nightly_delta.py`, `ops/bundle/tests/test_check.py`, the follow-ups in ticket 119's done comment and `.notes/119-review-r4.md`.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] The gate's processor time is down by at least a third (measured per lane with `/usr/bin/time` around `.githooks/pre-commit`, before and after, in the done comment), with the counts of specs and tests per lane unchanged except where two tests became one on purpose, each named.
- [ ] Every test an acceptance criterion names still runs (the done comment lists the tests merged or trimmed and the ticket each belongs to); `tests/test_gate.py` stays green.
- [ ] The full gate passes under 120 seconds on a quiet machine and under 150 seconds with two builders running, measured on this machine and recorded in `gates/steps.toml` and the ops brief.

## Comments

- October 28, 2026, orchestrator: opened at 14:45 PDT from ticket 119's review follow-up; it builds in the polish wave after wave 4u, or in its own run when the machine is quiet.
