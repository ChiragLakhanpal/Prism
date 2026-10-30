# 133: Agency names that differ by a prefix are one agency, so a plan and its notices meet on one heading

**What to build:** On October 29, 2026 the first draft of the demo walkthrough showed that P130164's Procurement tab (India, Rajasthan roads, closed) lists two agency headings: "Public Works Department", with the plan of June 20, 2018 and its 13 activities, and "Rajasthan State Public Works Department", with "I don't have a Procurement Plan from this agency yet" and the notices. They are one agency written two ways (the plan's implementing_agency and the notices' agency), so the plan check cannot pair the plan's rows with the notices, and the whole India case reads as if the plan were missing. Plans and notices are paired by `agency_id(...)` (`src/strata/server/changes.py` line 154, from the name). Make the pairing rule live in one place (`src/strata/lakehouse/clean.py`, or the registry it reads) and treat two names within one project as one agency when they are the same after dropping a leading place name or state and the words "State", "Government of" and "the", or when one name ends with the whole of the other; the heading shows the longest name and lists the variants in its window ("Also written as Public Works Department"), and the plan check, the Procurement tab, the tracker and the agency track record all pair through the same id. Names that only share a type word stay apart (Coast Water Works Development Agency and Northern Water Works Development Agency on P156634 are two agencies). Tests on the fixture with the India names and the Kenya names; the live proof is the orchestrator's: P130164's Procurement tab shows one heading with the plan and the notices together and its plan check pairs rows with notices, recorded in the catch-up file, and the other three demo projects keep their headings.

Read first: `src/strata/server/changes.py` (`agency_id` and its callers), `src/strata/lakehouse/clean.py`, `src/strata/server/procurement.py` or the Procurement tab's route in `app.py` (the headings), `src/strata/tools/agency_track_record.py` (the same pairing), `web/src/pages/Procurement*` (the heading and its window), GLOSSARY.md (implementing agency).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The agency pairing rule lives in one place and every caller uses it (a test that lists the callers by import); the India names pair and the Kenya names stay apart (tests).
- [ ] The heading shows the longest name with the variants in its window, and the plan check, the Procurement tab, the tracker and the track record agree on the agency (fixture tests on P130164).
- [ ] On the paid workspace, P130164's Procurement tab shows one heading with the plan and the notices, its plan check pairs rows with notices, and P156634, P161305 and P155350 keep their headings (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened from the walkthrough draft's findings on the India roads screens.
