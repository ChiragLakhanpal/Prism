# 43: The nightly job, incremental, with quality checks

**What to build:** Every night, one job takes in only what changed and carries it all the way through, within Free Edition's quotas and away from fairshare's job. The bundle's nightly job now runs every task for real, in order: fetch by watermark for every source; bronze to gold; parse and embed only new or changed documents; sync the index; re-link new contracts and passages; propose lessons on the Batch API for new ICRs, ICR Reviews and PPARs; detect disagreements; score (time estimates, the what-if grid and signals); measure data readiness; and mark drafts that cite a changed lesson (marking them, never changing them). Each task records its run, duration, rows changed and quality checks (row counts, key nulls, missing public_from dates, duplicates) for the Governance page. A failed night can be rerun without duplicates. Concurrency stays within the five-task limit, and the schedule keeps clear of fairshare's window and review hours.

Read first: docs/PLAN.md sections 2 (shared workspace limits), 11 and 16; docs/agents/build.md ("The shared workspace"); docs/agents/areas/ops.md.

**Blocked by:** 20 (Assertions, disagreements and the evidence ladder); 22 (Edges between strata: the contract trail and the Connections tab); 29 (The knowledge loop: proposed lessons with verified quotes, the review queue and versions)

**Status:** ready-for-agent
**Area:** ops
**Phase:** P2
**Design review:** no

- [ ] Offline, a fixture "next day" delta (one new ICR and one new plan version) runs through the tasks in order: only the new documents are parsed and embedded, a lesson is proposed, data readiness measures update, and a draft citing the changed lesson is marked.
- [ ] On the workspace, a scheduled run completes within its window, and strata.ops records each task's duration, rows changed and quality checks passed and failed.
- [ ] Running the same night twice changes nothing.
- [ ] A run forced to fail midway, then rerun, finishes with no duplicate rows.
- [ ] The job never runs more than five tasks at once, and its window does not overlap fairshare's.
- [ ] No draft's content changes during the run; only its was-and-now marker is set.

## Comments

- October 24, 2026, orchestrator: the gate's time is drifting up. By hand on build/strata it took about 30 seconds after ticket 51, 55 to 66 seconds after tickets 14, 16 and 19 landed, and 86 to 105 seconds on reviewers' runs while four tickets built at once. The web lane sets the total now: tickets 10, 12, 14 and 16 added Playwright specs that take 13 to 53 seconds each on one worker, mostly axe runs. CLAUDE.md rule 6 caps the gate at two minutes, and `.githooks/pre-commit` enforces it. Before the nightly job's own checks add more, bring the gate back under 60 seconds by hand: run the Playwright specs on more workers or shard them across two lanes that need nothing from each other, keep the fixture build and the python tests where they are, and record the new lane times in `gates/steps.toml`'s comments, README's gate section and `docs/agents/areas/ops.md`. Report the gate's time alone and under load. If this does not fit the ticket, say so in the report and the orchestrator opens a ticket for it.
