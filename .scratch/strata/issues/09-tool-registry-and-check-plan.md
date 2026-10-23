# 09: The tool registry with the as-of contract, and check_plan

**What to build:** The tool registry, the one seam that every tool, page, workflow and the agent go through, with its first tool, check_plan, and the HTTP route the Check a plan page calls. A tool is defined once: name, description, parameters (always including an optional as-of date), adapter and result shape. Called with the viewer's identity and view, it returns rows with evidence ids, public_from dates and source-line fields, plus a coverage line (how many matched, how many were used, and why the rest were not). The agent's tool list is generated from the registry, so adding a tool later is one entry. check_plan takes a project and an implementing agency's plan (the latest by default, or a named version) and runs the fixed checks from the thresholds file: planned completion passed with no signed contract, with the days left before the project closes; signed late against the first published planned date; actual amount far above the estimate; still pending close to the project's closing date; and the data notes. It returns a mark per package (Needs a look, Watch, Data note or none) with its reasons as structured values, which the screen turns into sentences from the copy file. With an as-of date it uses only plan versions, contracts and project dates public on or before that date.

Read first: docs/PLAN.md sections 6 and 10; ADRs 0002 and 0003; the spec's Seams (seam 2) and "The tool registry and the tools"; docs/agents/areas/agent.md.

**Blocked by:** 07 (Kenya's procurement records, bronze to gold); 08 (P156634's Procurement Plans read into STEP rows)

**Status:** in-progress
**Area:** agent
**Phase:** P1
**Design review:** no

- [ ] A test lists the registry and fails if any tool lacks an as-of parameter or a result shape; the generated agent tool list contains exactly the registry's tools.
- [ ] On the fixture, as of October 22, 2026, check_plan on the NWWDA October 9 plan checks 8 activities and returns: KE-NWWDA-541055-CW-RFB as Needs a look (planned completion July 31, 2026 passed with no signed contract; the project closes October 31, 2026); KE-NWWDA-229129-CW-RFB as Watch (signed 186 days late at about 4 times its estimate); KE-NWWDA-541062-CW-RFQ as Watch (still pending 9 days before closing); three data notes; and two packages with no signals.
- [ ] As of July 1, 2026, KE-NWWDA-541055-CW-RFB is not marked as passing its planned completion, and as of October 1, 2026 the October 9 version is not used.
- [ ] Overriding the days-before-closing threshold in the thresholds file changes KE-NWWDA-541062-CW-RFQ's mark, proving the threshold lives in one place.
- [ ] Every returned row carries an evidence id, a public_from date and its source-line fields (Procurement Plan, agency, version date).
- [ ] The plan-check HTTP route returns the tool's result for the viewer, and a viewer whose token cannot read strata gets a permission error and no rows.
- [ ] The ground-truth SQL for these counts runs in the offline gate.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/09-tool-registry-and-check-plan, as soon as ticket 07 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
