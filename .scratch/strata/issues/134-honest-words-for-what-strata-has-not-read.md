# 134: Honest words for what Strata has not read, for a plan with no activities, and for a paused refresh

**What to build:** On October 29, 2026 the first draft of the demo walkthrough found three sentences on the App's screens that say more or less than the records: (a) P156634's Procurement tab says "The only plan I have from this agency is the plan of October 9, 2026" while the Documents tab lists 240 Procurement Plan documents for the project, all but one "Not read"; the honest sentence is "The only plan I have read from this agency is the plan of October 9, 2026" with a link to the Documents tab; (b) P127203's Procurement tab lists "Plan of Sep 17, 2019" with 0 activities and, below it, "I haven't read a Procurement Plan for this project yet"; a plan that was read and holds no rows says "I read the plan of September 17, 2019 and found no activities in it", and the second sentence shows only when no plan was read; (c) the Data page says "I last fetched the project records on October 26, two days behind their daily update" and "Oct 26 · daily, two days late", and the number grows each day now that the owner paused the nightly on October 29 to stop spending; the page should say "Refresh paused since October 29; records as of October 26" from one config value (`config/sources.toml` or `config/thresholds.toml`, `ingestion.paused_since`, empty when running), and say "late" only when the refresh runs. Each sentence is a copy key in `web/src/copy.ts` with its state from the server (`src/strata/server/documents.py`, the Procurement tab's route, `src/strata/server/data.py` or the Data page's route); tests for the three states on the fixture; keep the gate under 150 seconds; no design review (these are wrong facts, not taste).

Read first: `web/src/copy.ts` (the three keys), the Procurement tab's route in `src/strata/server/app.py`, the plans query under `src/strata/server/sql/`, the Data page's route and its freshness lines, `config/thresholds.toml` [ingestion], DESIGN.md section 7 (the words Strata never writes).

**Blocked by:** None (can start immediately)

**Status:** done
**Area:** web
**Phase:** P4
**Design review:** no

- [ ] The Procurement tab says "the only plan I have read from this agency" with a link to the Documents tab when other plan documents are listed unread (a fixture test on P156634), and a plan read with no rows says so, with the "haven't read" sentence only when no plan was read (a test).
- [ ] The Data page reads `ingestion.paused_since` and says "Refresh paused since October 29; records as of October 26" when set, and "late" only when the refresh runs (tests for both).
- [ ] The three sentences are checked on the paid workspace after the merge and the App redeploy (recorded in the catch-up file under this ticket), and the config value is set to October 29, 2026 in the same change.

## Comments

- October 29, 2026, orchestrator: opened from the walkthrough draft's findings; the paused nightly is the owner's decision of October 29.
- October 29, 2026, merger: merged into build/strata as de8e6a06 (a merge with history of strata/134-honest-words-for-what-strata-has-not-read at a6c6c1ec; the history scan found no key-shaped line). Built in the worktree .claude/worktrees/wf_67f02a42-1ac-15, which is now removed; the branch stays.
  - The gate on the merge commit passed in 139.9 seconds; by hand on build/strata afterwards it passed in 144.5 seconds at 23:41 PDT.
  - Conflicts, kept both sides: `packages_reads` sends ticket 133's plan versions and this ticket's `plans_read` in one batch; `packages()` keeps ticket 133's grouped agencies, and `plans_read` now takes its `agency_id` from the same grouping, because ticket 133 removed the bare `agency_id` from projects.py; web/tests/projects.spec.ts keeps ticket 133's one-heading test and this ticket's no-activities test. Ticket 133's two recorded answers for P130164 (project-p130164-one-agency.json, packages-p130164-one-agency.json) were recorded again with tests/record_agency_names_api.py, so they carry `plans_unread` (15) and `plans_read` as the server now answers; tests/test_agency_names.py compares them with the server.
  - Evidence (.notes/134-verify.md, round 1, pass): criterion 1 passed. P156634 lists 240 Procurement Plan documents and 11 are read, so `plans_unread` is 229, equal to the Documents tab's Not read count; the sentence reads "The only plan I have read from this agency is the plan of ..." with "See the plans I haven't read" linking to /projects/P156634/documents. A plan read with no rows says "I read the plan of September 17, 2019 and found no activities in it.", and "I haven't read a Procurement Plan" shows only when no plan was read (a throwaway database test and projects.spec.ts). Criterion 2 passed: `ingestion.paused_since = "2026-10-29"` in config/thresholds.toml; from October 29 the Fresh cell says "Refresh paused since Oct 29" and no "late", and before that day "late" still shows (three tool tests and data.spec.ts). Criterion 3: the config value is set in this change; the workspace half is parked.
  - Workspace results: none run. Every key is set, but mergers run no workspace step. The App redeploy and the three-sentence check are parked in docs/workspace-catchup.md as "Ticket 134, step 1 of 2" and "step 2 of 2", for the second session (strata-58) or the orchestrator to run from a snapshot at or after de8e6a06. The builder named the Free Edition App; the blocks point at the paid workspace's App.
  - Review follow-ups (not blocking, from .notes/134-review.md): (1) `changes.compare()` in src/strata/server/changes.py says `previous_not_read` when the version before was read but held no rows; decide on `parse_reason`, not the row count. (2) Packages.tsx's `readEmpty` should keep only plans with no activities and pass the count for the singular form. (3) Move `display_name` into a shared module so projects.py can import documents at the top. (4) One `DOCUMENT_READS` constant for the query names `_Documents` and `plans_unread_reads` both use.
  - Verifier notes (not blocking): the agent cannot say the refresh is paused, because the pause date comes from config, not a row, so the verifier removes it; the Lakeview snapshot's `days_late` column is empty while the refresh is paused.

  **Deferred to the design pass**

  - None. The verifier reviewed no visual craft, following the function-first rule (one capture at 1440 px per screen).

  **Decisions parked for the user**

  - None from the builder, the reviewer or the verifier.
- October 30, 2026, orchestrator (00:31 PDT): the App redeploy ran from de8e6a06 (the catch-up block "Tickets 127, 138, 133, 136 and 134, the App redeploy ran"); the page's check by eye is the owner's.
