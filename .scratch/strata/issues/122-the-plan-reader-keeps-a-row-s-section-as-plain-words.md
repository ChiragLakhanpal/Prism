# 122: The plan reader keeps a row's section as plain words, so a live plan's rows find their step family

**What to build:** On October 28, 2026, with the App on 4484310a, `GET /api/packages/KE-NWWDA-541055-CW-RFB/steps` on the paid workspace answered 200 with `step_dates.steps` empty, `family` null and `family_reason` "no_family", so the package page shows neither an estimate nor ticket 115's tracker, although `strata.silver.plan_step_delays` holds the package's eight steps with four planned dates and one actual date from plan 40132287. The cause is in silver: the plan reader writes the row's section as ai_parse_document's markdown gives it, with its underline tags, so `strata.silver.plan_rows` holds `<u>WORKS</u>` (130 rows), `<u>GOODS</u>` (86), `<u>CONSULTING FIRMS</u>` (28) and `<u>INDIVIDUAL CONSULTANTS</u>` (1): 245 of the 268 rows of the 25 plans read so far, and `clean.category` reads none of them, so `family_for` (src/strata/estimates/step_dates.py) returns no_family for the package and for every comparable from those plans. The fixture's plans were read by the other parser path, whose sections are plain, so no test saw it. Make the reader strip markup from every text field it writes (the section, the description, the method and the other words of a row), in one place in `src/strata/lakehouse/plans.py` (or `strata.lakehouse.clean`, where the notice reader's plain_text lives), so `<u>WORKS</u>` is written as WORKS and `clean.category` reads it; a fixture test feeds a page whose section carries tags and checks the row, and the step-dates test checks that `family_for` finds the family for such a row. Keep the rule in one place (CLAUDE.md rule 4). The live step is the orchestrator's: after the merge and the bundle deploy, `ops/plans/run_live.py` rewrites each read project's plan rows from the pages bronze already holds (ticket 78's step 2 did it for P156634 with `--project`; do it for every project with plan rows, or add the option that does), then gold is rebuilt, and the steps route on the App answers with a family and the tracker's steps for the demo package, with "Contract signed" done on June 22, 2026 (contract 1903781) as the fixture's recorded answer shows.

Read first: `src/strata/lakehouse/plans.py` (the rows it writes, around line 700), `src/strata/lakehouse/readers.py` (ai_parse_document's output), `src/strata/lakehouse/clean.py` (`category`, `text`), `src/strata/lakehouse/silver/notices.py` (`plain_text`, the notice reader's markup rule), `src/strata/estimates/step_dates.py` (`family_for`), `src/strata/server/tracker.py`, `ops/plans/run_live.py`, the catch-up file's block "Tickets 112, 113, 114 and 115, the App redeploy ran" of October 28 and ticket 78's step 2.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P4
**Design review:** no

- [ ] A plan page whose section (or any text field) carries markup is written to `strata.silver.plan_rows` as plain words, by one rule in one place, proven by a fixture test; `clean.category` reads WORKS, GOODS, CONSULTING FIRMS and INDIVIDUAL CONSULTANTS from such rows.
- [ ] `family_for` finds the family for a row read that way (a test), and the recorded steps answer for KE-NWWDA-541055-CW-RFB is unchanged on the fixture.
- [ ] On the paid workspace, after the merge, the bundle deploy and the rewrite of every read plan's rows with the fixed reader (`ops/plans/run_live.py`), `strata.silver.plan_rows` holds no section with a tag, and the steps route for KE-NWWDA-541055-CW-RFB answers with a family and the tracker's steps (recorded in the catch-up file under this ticket).

## Comments

- October 28, 2026, orchestrator: opened at 04:30 PDT on the orchestrator's judgment from ticket 115's live proof on the App; it builds in its own run tonight, ahead of wave 4u's merges, because the demo package's page shows no tracker on the workspace until it lands.
