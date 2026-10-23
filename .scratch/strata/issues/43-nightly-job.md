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
