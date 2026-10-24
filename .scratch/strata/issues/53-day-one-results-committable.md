# 53: The day-one results document can hold the wizard's results and still pass the gate

**What to build:** The user ran the credentials wizard on October 24, 2026, and it recorded day-one test 7 as failed and test 8 as passed in `docs/day-one-results.md`. Two of ticket 03's tests in `ops/dayone/tests/test_results_document.py` then fail: one asserts that every test's Status is still "not run", and one asserts that the document equals what `dayone.render_document(dayone.load_config())` renders. So the results cannot be committed, and while they sit uncommitted in the main checkout the gate's unstaged-changes rule (`gates/offline.py`, `unstaged_changes`) refuses every commit that stages a code file; each merger has had to set the wizard's edit aside and put it back. Change the two tests so that the template is tested as a rendering in `tmp_path` (every test waits with the command that fills it, and the rendering never drifts from `dayone.toml`), and the committed document is tested block by block: each test block is either the template's text or a recorded result with a Status other than "not run", a Result, at least one Evidence line and a dated Last run. Keep every other test as it is. Then commit the wizard's two results as they stand in the working copy, and say in README's gate section or `docs/agents/areas/ops.md` that the wizard's results are committed like any other file.

Read first: `ops/dayone/tests/test_results_document.py`; `ops/dayone/dayone.py` (`render_document`, `read_results`, `record_test`); `docs/day-one-results.md` as the wizard left it in the main checkout (do not change its content); `gates/offline.py` lines 1 to 30 and 70 to 90; ticket 03's done comment.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P1
**Design review:** no

- [ ] With the main checkout's `docs/day-one-results.md` (test 7 failed, test 8 passed) copied into the branch, `uv run --frozen pytest ops/dayone/tests/test_results_document.py` passes, and it also passes against a freshly rendered template; a block whose Status is not "not run" but has no Evidence line or no dated Last run fails the new check.
- [ ] The rendering test still fails when `dayone.toml` and the renderer drift: changing a test's question in a copy of `dayone.toml` makes the test fail.
- [ ] The gate passes by hand on the branch with build/strata merged in and the two recorded results committed; the ops lane's time is reported.
- [ ] README's gate section or `docs/agents/areas/ops.md` says in one or two sentences that the wizard writes `docs/day-one-results.md` in the main checkout and the results are committed like any other change; `docs/workspace-catchup.md`'s note on the wizard is updated to match.

## Comments

- October 24, 2026, orchestrator: opened while the wizard was running. Until this lands, mergers set the wizard's edit aside before a merge and put it back after, as the note at the top of `docs/workspace-catchup.md` says. Dispatched to an implementer in its own worktree on branch strata/53-day-one-results-committable; a side run builds, reviews and verifies it, and the next restart of the wave merges it first.
