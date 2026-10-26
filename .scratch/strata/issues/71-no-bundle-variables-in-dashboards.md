# 71: No bundle variable reference in the dashboard files, so the bundle deploys again

**What to build:** Every bundle deploy from db96b3a onward fails at its first step with `Error: invalid dependency "${budget}", no such node ""` (two tries on October 26, 2026 at 06:12 UTC, nothing deployed). The Databricks CLI interpolates `${...}` inside the dashboard files it uploads, and `bundle/dashboards/strata.lvdash.json` line 370 (and `strata_test.lvdash.json`) held the SQL text `replace(replace('US${spent} of US${budget}', ...)`, which the writer inlined from the copy key `money` ("US${spent} of US${budget}"). The writer's SQL literal helper (`src/strata/dashboard/render.py`, `_literal`) now splits every `${` so the literal reads `concat('US$', '{spent} of US$', '{budget}')`, which the `replace()` calls still fill the same way; both dashboard files are written again; and a test keeps `${` out of them. Until this landed no bundle deploy could run, so ticket 45's dashboard step and every new table from later tickets waited on it.

Read first: `src/strata/dashboard/render.py` (`_literal` and the `:copy__` parameters), `src/strata/dashboard/__init__.py` (`written`, `FILE`, `TEST_FILE`), `tests/test_dashboard.py` (the file is pinned to the code), `src/strata/dashboard/copy.json` line 706.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** data
**Phase:** P2
**Design review:** no

- [x] Neither `bundle/dashboards/strata.lvdash.json` nor `strata_test.lvdash.json` contains `${`, a test proves it for the files the writer produces, and the pinned-file test still passes after `uv run --frozen python -m strata.dashboard --write`.
- [x] The money tile's SQL still fills the same words: the test checks the helper gives `concat('US$', '{spent} of US$', '{budget}')` for the copy key and leaves plain words as they were.
- [ ] The second session's bundle deploy from a snapshot of build/strata with this change passes its first step (recorded in the catch-up file under this ticket).

## Comments

- October 25, 2026, orchestrator: opened at 23:25 PDT from the second session's deploy failure and built by the orchestrator itself in the worktree `.claude/worktrees/orch-71`, because every live step waited on it tonight. The dashboard tests (49) pass with the change; the live proof is the second session's next bundle deploy.
