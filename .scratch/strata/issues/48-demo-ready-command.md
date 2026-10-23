# 48: The demo-ready command

**What to build:** One command makes Strata ready for a review. It starts or restarts the app (apps stop 24 hours after each start or deploy), warms the SQL warehouse and the Genie space (Genie stalls on a cold warehouse), asks one smoke question through the live answer contract and checks its citations, rechecks the P156634 signals (the project closes October 31, 2026) and reports anything that changed since the fixture was recorded, and prints a short status summary. With an option, it also shows how a fresh workspace reaches the demo state from code alone: the bundle, the app, the jobs, the Genie space, the AI Search index, the Foundry agent and the seeds. It is safe to run any number of times.

Read first: docs/PLAN.md sections 11, 12 (Known traps) and 16; docs/agents/areas/ops.md; docs/agents/build.md ("The shared workspace").

**Blocked by:** 33 (Genie, the benchmark, Foundry evaluations and the full gate); 37 (Following, project signals and the mission brief)

**Status:** ready-for-agent
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] Run against a stopped app, the command restarts it, and the app answers its health route within the timeout.
- [ ] After the command, the first Genie call answers within a stated threshold.
- [ ] The smoke question returns a cited answer that passes the six checks; if it does not, the command exits with an error naming the failed step.
- [ ] The P156634 recheck prints each signal's current state and any change since the fixture, such as a package signed since October 9, 2026.
- [ ] The fresh-workspace dry run lists every resource it would create, from code alone, with no manual step.
- [ ] Two runs in a row both succeed and leave nothing different, and the README documents the command and its output.
