# 34: The hindsight test

**What to build:** The hindsight test runs on every release as the gate for anything that changes what Strata shows about risks. It covers the slice projects with an ICR (49 expected), excluding any project used as an extraction example and any project exposed to Strata. The replay harness freezes Strata at each project's approval date and runs the risk-table builder for the first plan's main packages (the three largest by estimated amount), keeping the top five risks per package. Two people code the risks each completion report blamed, through a coding tool that records both codings and the reconciled set, with the ICR Review prevailing where they differ. The report reads "caught X of Y blamed risks across N projects (95% interval), at five per package", next to what a checklist of the sector's five commonest risks caught. A challenger must not lose a paired comparison on the same risks (McNemar) and must beat the checklist. Results go to strata.ops and MLflow; hindsight recall is coverage times shown-when-covered, for the dashboard.

Read first: docs/PLAN.md sections 10 and 11; ADR 0002; GLOSSARY.md (Hindsight test); the blueprint's "Three loops, one dated store" ("The hindsight test, as a gate"); docs/agents/areas/ml.md.

**Blocked by:** 25 (The replay harness and the survival model's backtests); 30 (Procurement risks and what helped, on the package workspace)

**Status:** in-progress
**Area:** ml
**Phase:** P2
**Design review:** no

- [ ] A test proves that no passage, lesson or record public after a project's approval date reaches its frozen risk table.
- [ ] The coding tool stores two codings per project, the reconciled blamed risks with the ICR Review prevailing, and the agreement statistic.
- [ ] The report sentence is generated from stored results with a 95% interval, beside the checklist baseline's count.
- [ ] A seeded challenger that is worse on the same risks loses the McNemar comparison and is not promoted.
- [ ] Projects used as extraction examples and projects exposed to Strata are excluded and listed.
- [ ] One release-gate command runs the test and records its results with run ids; if fewer than 49 projects have a usable ICR, N is reported as found.
- [ ] Hindsight recall (coverage times shown-when-covered) is stored for the dashboard.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/34-hindsight-test, as soon as ticket 30 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
