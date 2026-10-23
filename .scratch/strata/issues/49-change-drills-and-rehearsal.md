# 49: The change drills and the full rehearsal

**What to build:** The ten likely change requests from PLAN.md section 15 each land in under ten minutes with the gate green, and the specialist's path runs end to end on the deployed app. For each drill (add a data source; add a tool; change a signal threshold; add a country to the slice; swap the model; reorder the evidence ladder; add a field to the package form; reword copy; add a benchmark or must-refuse question; add a dashboard tile), write a runbook entry naming the single place it lives, the steps, and the test that proves it, then rehearse it on a throwaway branch with a timer and record the time. Then run the demo-ready command and walk the blueprint's "A specialist's path" on the deployed app: Home, Check a plan, the package workspace, the evidence drawer, the project timeline, Drafts, Following and Lessons. Record timings and anything that fails; each failure becomes a ticket or a "designed, not built" line.

Read first: docs/PLAN.md sections 13 (P4) and 15; the blueprint's "A specialist's path" and "From an empty repo to a rehearsed demo"; the spec's "Ten single places"; docs/agents/areas/ops.md.

**Blocked by:** 45 (All three dashboard pages and the KPIs); 47 (The deck at /present, and How Strata works); 48 (The demo-ready command)

**Status:** ready-for-agent
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] Each of the ten drills has a runbook entry that names its single place and its proving test.
- [ ] Each drill was rehearsed, timed under ten minutes, and finished with the gate green; the times are recorded. This is P4's exit criterion.
- [ ] No drill leaves a change on the integration branch.
- [ ] The demo-ready command ran and passed before the rehearsal.
- [ ] All eight steps of the specialist's path ran on the deployed app with timings recorded, and every step either worked or has a recorded follow-up ticket or "designed, not built" line.
