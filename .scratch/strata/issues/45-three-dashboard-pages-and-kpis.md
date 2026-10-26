# 45: All three dashboard pages and the KPIs

**What to build:** The people who run Strata see data readiness, governance, and AI quality and adoption in one AI/BI dashboard built from code. The Data readiness page now covers the full slice. Governance shows lineage from source to answer (an answer's run id to its tool calls to the tables they read), quality checks passed and failed per pipeline run, personal data stripped at ingestion, who queried what where Free Edition exposes it, and Azure spend against the budget from a daily cost pull into strata.ops. AI quality and adoption shows benchmark pass rates and Foundry evaluation scores, sentences the verifier removed, abstentions, retrieval precision at 10 and recall at 20, hindsight recall (coverage times shown-when-covered), each loop's leading and lagging indicators, the share of plans anchored on Strata's ranges, weekly users, and drafts checked and exported. Each KPI is defined once, and adding a tile is one entry in the dashboard definition.

Read first: docs/PLAN.md sections 9 and 11; the blueprint's "The dashboard for the people who run Strata" and the indicators rows of the "Three loops, one dated store" table; DESIGN.md section 6; CLAUDE.md rule 4.

**Blocked by:** 16 (Data readiness: the page and the first dashboard page); 32 (The retrieval loop); 33 (Genie, the benchmark, Foundry evaluations and the full gate); 34 (The hindsight test); 43 (The nightly job, incremental, with quality checks); 44 (Exposure logging, the estimates loop and the hazard model in shadow)

**Status:** in-progress
**Area:** ops
**Phase:** P2
**Design review:** yes

- [ ] The dashboard deploys from code with three pages, and a test compares every tile's number with its defining query over strata.ops and strata.gold.
- [ ] A daily cost pull writes Azure spend to strata.ops, and the Governance page shows it against the budget.
- [ ] From an answer's run id, the lineage view reaches its tool calls and the tables they read.
- [ ] Each loop's leading indicator (days from publication to decision; "Wrong passage" per 100 sources opened; rolling coverage of the 8-in-10 range) and lagging indicator appears with its definition.
- [ ] Weekly users and drafts checked and exported are computed from usage events and draft states.
- [ ] Adding a tile, then removing it, takes one entry in the dashboard definition each time, shown in a test deploy.
- [ ] Every chart follows DESIGN.md section 6 (the finding as the title, a source note, category colors in order with text variants for essential marks, the number rules) and the lists in the blueprint's dashboard section.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/45-three-dashboard-pages-and-kpis, as soon as ticket 44 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
