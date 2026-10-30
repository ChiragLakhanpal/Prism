# 132: The plan check names a row the records have moved past: the plan says pending while the awards say signed

**What to build:** On October 29, 2026 the first draft of the demo walkthrough showed, on the demo package KE-NWWDA-541055-CW-RFB (P156634), that the plan row's Process Status reads "Pending Implementation" and the plan check says "Still pending, 2 days before the project closes", while the same package's step tracker shows "Bid evaluation report: Done, Apr 24, 2026" and "Contract signed: Done, Jun 22, 2026", taken from the contract awards data (`src/strata/server/tracker.py`, `sql/tracker/signed.sql`). The two sentences sit one click apart and neither names the other. Make the plan check read what the tracker knows: for each plan row with a package, the plan check (`src/strata/server/changes.py` and `baseline.py`, the per-row finding) asks the tracker's step states; when the plan's status is pending (or any state before signing) and a later step is done from another source, the row's state becomes "moved on since the plan" (a new state in the plan check's state registry and copy, counted apart from "still pending") and its sentence says what the record shows, with the record cited: "The plan still says pending, but the contract awards say the contract was signed on June 22, 2026." Where the disagreements tool (`src/strata/tools/get_disagreements.py`) already holds a plan-versus-awards disagreement for the package, the plan check cites that disagreement instead of working it out again; where it does not, the finding is written as a disagreement row too, so the Timeline tab's "where the records disagree" shows it (one definition, rule 4: the measure lives in one place and the plan check reads it). Tests on the fixture, which holds this package (the October 9, 2026 plan and the award of June 22, 2026). The live proof is the orchestrator's: the Kenya water plan check shows the new state for 541055 and the Timeline tab lists the disagreement, recorded in the catch-up file.

Read first: `src/strata/server/tracker.py` (the states and sources), `src/strata/server/changes.py` and `baseline.py` (the plan check's row findings and states), `src/strata/tools/get_disagreements.py` (subject kinds), `config/` for the plan check's state registry and the disagreement kinds, `web/src/components/PlanCheck.tsx` (the state rows and counts), DESIGN.md section 5 (the plan check's rows).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] A plan row whose status is pending while the tracker shows a later step done from another source gets the state "moved on since the plan", counted apart from "still pending", with a sentence that cites the record (fixture tests on KE-NWWDA-541055-CW-RFB and on a row that is pending with no later step, which stays "still pending").
- [ ] The finding is one definition: it is read from or written as a disagreement row, so the plan check and the Timeline tab's disagreements show the same fact (a test that both routes name the package).
- [ ] On the paid workspace, the Kenya water plan check shows the new state for 541055 and the Timeline tab lists the disagreement (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened from the walkthrough draft's findings on the demo package.
