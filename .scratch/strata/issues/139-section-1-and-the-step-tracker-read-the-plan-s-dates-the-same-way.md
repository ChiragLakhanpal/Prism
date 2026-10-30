# 139: Section 1 of the package workspace and the step tracker read the plan's dates the same way

**What to build:** On October 29, 2026 the demo walkthrough's second capture showed, on the Kenya roads package KE-SDOR-KIHBT-563865-CW-RFB (P161305, plan of September 28, 2026), the step tracker drawing planned dates from the plan (bid invitation December 9, 2026 through a contract signed "Planned for Nov 7, 2029") while section 1 above it reads "The plan row has no planned notice date or signing date, so there is no plan line yet. Type a number of months to compare." Both read the same plan row; section 1 (`web/src/components/PastRange.tsx`, fed by `find_comparables` or the package route) looks at two columns the tracker does not, and the tracker (`src/strata/server/tracker.py`, `estimate_time`'s step dates) reads the plan's step dates. Make one reading: the plan's planned notice and signing dates come from the tracker's step dates (the bid invitation's and the signed contract's planned dates) when the row's own columns are empty, so section 1 draws the plan line (here about 35 months) and its sentence names where the dates come from ("From the plan's step dates: bid invitation December 9, 2026, contract signed November 7, 2029"); when neither source has dates, the sentence stays as it is. Tests on the fixture (this package is in it, or add its plan row to the recorded rows), and the live proof is the orchestrator's: the package page draws the plan line on the App after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `src/strata/server/tracker.py`, `src/strata/server/steps.py`, `src/strata/tools/find_comparables.py` (the planned months), the package route in `src/strata/server/app.py`, `web/src/components/PastRange.tsx` and `StepTracker*`, DESIGN.md's package workspace rows.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] Section 1's planned months come from the same plan dates the tracker shows, in one place, with the sentence naming the source (tests on the fixture for a row with step dates only, a row with its own dates, and a row with neither).
- [ ] The plan line is drawn whenever the tracker has a planned bid invitation and a planned signing (a spec).
- [ ] On the paid workspace, /packages/KE-SDOR-KIHBT-563865-CW-RFB draws the plan line after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 21:03 PDT from the walkthrough's second capture.
