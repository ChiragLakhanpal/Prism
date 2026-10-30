# 134: Honest words for what Strata has not read, for a plan with no activities, and for a paused refresh

**What to build:** On October 29, 2026 the first draft of the demo walkthrough found three sentences on the App's screens that say more or less than the records: (a) P156634's Procurement tab says "The only plan I have from this agency is the plan of October 9, 2026" while the Documents tab lists 240 Procurement Plan documents for the project, all but one "Not read"; the honest sentence is "The only plan I have read from this agency is the plan of October 9, 2026" with a link to the Documents tab; (b) P127203's Procurement tab lists "Plan of Sep 17, 2019" with 0 activities and, below it, "I haven't read a Procurement Plan for this project yet"; a plan that was read and holds no rows says "I read the plan of September 17, 2019 and found no activities in it", and the second sentence shows only when no plan was read; (c) the Data page says "I last fetched the project records on October 26, two days behind their daily update" and "Oct 26 · daily, two days late", and the number grows each day now that the owner paused the nightly on October 29 to stop spending; the page should say "Refresh paused since October 29; records as of October 26" from one config value (`config/sources.toml` or `config/thresholds.toml`, `ingestion.paused_since`, empty when running), and say "late" only when the refresh runs. Each sentence is a copy key in `web/src/copy.ts` with its state from the server (`src/strata/server/documents.py`, the Procurement tab's route, `src/strata/server/data.py` or the Data page's route); tests for the three states on the fixture; keep the gate under 150 seconds; no design review (these are wrong facts, not taste).

Read first: `web/src/copy.ts` (the three keys), the Procurement tab's route in `src/strata/server/app.py`, the plans query under `src/strata/server/sql/`, the Data page's route and its freshness lines, `config/thresholds.toml` [ingestion], DESIGN.md section 7 (the words Strata never writes).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** web
**Phase:** P4
**Design review:** no

- [ ] The Procurement tab says "the only plan I have read from this agency" with a link to the Documents tab when other plan documents are listed unread (a fixture test on P156634), and a plan read with no rows says so, with the "haven't read" sentence only when no plan was read (a test).
- [ ] The Data page reads `ingestion.paused_since` and says "Refresh paused since October 29; records as of October 26" when set, and "late" only when the refresh runs (tests for both).
- [ ] The three sentences are checked on the paid workspace after the merge and the App redeploy (recorded in the catch-up file under this ticket), and the config value is set to October 29, 2026 in the same change.

## Comments

- October 29, 2026, orchestrator: opened from the walkthrough draft's findings; the paused nightly is the owner's decision of October 29.
