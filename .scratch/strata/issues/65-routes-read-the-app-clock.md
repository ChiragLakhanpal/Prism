# 65: Every route reads the app's clock, so recorded answers hold still across midnight UTC

**What to build:** Since 00:00 UTC on October 26, 2026 the gate fails on every branch, including build/strata, on two tests: `tests/test_check_criteria.py::test_the_screens_recorded_criteria_answers_are_what_the_routes_answer` ("package-ke-cwsb-224323.json is out of date": recorded `as_of` 2026-10-25, answered 2026-10-26) and `tests/test_estimate_routes.py::test_the_screens_recorded_estimate_answers_are_what_the_routes_answer`. The recorders (`tests/record_criteria_api.py`, `tests/record_estimate_api.py`) give `create_app` a fixed `today`, but some routes in `src/strata/server/app.py` read the real clock instead: `list_projects` and `open_project` (`registry.today()` at lines 476 and 485) and `as_of_for` (line 636), which the package and criteria routes use. So a recording made on one day answers differently the next. Make every route take its as-of date from the `today` that `create_app` was given (as `project_timeline` already does at line 505), with `registry.today` only as the default when nothing is injected; then record the affected files again with the recorders, so each holds the recorder's fixed date, and fix any screen test or gallery state that asserted the old date text. Prove it by running the two tests with the clock set to October 26 and to October 27 (freeze `registry.today` in the test or run with `faketime`-free means such as monkeypatching), both green. Change no number, claim or tool contract; the as-of rule (never later than today, ADR 0002) stays.

Read first: `src/strata/server/app.py` lines 460 to 520 and 625 to 645 (`today`, `as_of_for`, the three routes); `tests/record_criteria_api.py` and `tests/record_estimate_api.py` (how they build the app and what they write); `tests/fixtures/api/README.md` if it exists; `web/tests/check-criteria.spec.ts` and `web/tests/time-estimate.spec.ts` (what they assert about dates); `.notes/48-verify-r2.md` section "The gate" (the failure as the verifier saw it).

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** app
**Phase:** P2
**Design review:** no

- [ ] With the real clock on any date after the recording, the two tests pass, and a test proves the three routes answer with the injected `today`, not the wall clock; the gate passes by hand on this branch with build/strata merged in.
- [ ] The recorded files under `tests/fixtures/api/` that changed carry the recorder's fixed date, the screen tests and the gallery still pass, and no recorded number changed; the report lists each file that was recorded again and the one field that changed.
- [ ] `docs/agents/areas/app.md` or the recorders' docstrings say in one or two sentences that routes read the app's clock and that recorders must pin it.

## Comments

- October 25, 2026, orchestrator: opened at 17:20 PDT when ticket 48's verifier found build/strata's gate red on these two tests from 00:00 UTC on October 26, which blocks every merge. Dispatched to an implementer in its own worktree on branch strata/65-routes-read-the-app-clock; a side run builds, reviews and verifies it, and a merge-only run lands it before the wave's next merge.
