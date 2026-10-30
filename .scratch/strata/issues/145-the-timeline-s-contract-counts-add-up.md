# 145: The timeline's contract counts add up: the contracts held, the ones placed by year and the ones left out are one sum

**What to build:** On October 30, 2026 the demo walkthrough's final capture showed, on three Timeline tabs, a note that does not add up with the lane above it: P155350 "I hold 164 contracts... leaves out 31 from the contract awards since fiscal 2020 and six and two from award notices" while the records lane's yearly labels sum to 122 (164 minus 39 is 125); P156634 "I hold 262 contracts... leaves out six... and two" while the lane sums to 244 (262 minus 8 is 254); P161305 "I hold 121 contracts... leaves out 22" while the lane sums to 88 (121 minus 22 is 99). The records lane (`src/strata/server/timeline.py`, `sql/timeline/signings.sql`) counts contracts placed by their signing year within the chart's span, and the note (ticket 138's one definition of a project's contracts) counts the contracts held and the ones without a STEP reference, so contracts outside the chart's years, without a signing date, or whose package the lane could not place are counted in neither sentence. Make the three numbers one sum in one place: the note says how many contracts Strata holds, how many the lane places by year, and how many it leaves out and why (no STEP reference, no signing date, signed outside the chart's years), so that held = placed + left out, with the lane's labels summing to "placed". Tests on the fixture for the three demo projects and a planted case with a contract outside the chart's years; the live proof is the orchestrator's: the three Timeline tabs add up on the App after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds; no design review.

Read first: `src/strata/server/timeline.py` (the records lane and the note), `src/strata/server/sql/timeline/signings.sql`, ticket 138's done comment (the definition both tabs share), `config/sources.toml` (the contract sources).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The note names the contracts held, the contracts placed by year and the contracts left out with their reasons, and held = placed + left out, with the lane's labels summing to placed (tests on the fixture's three demo projects and a planted out-of-span contract).
- [ ] The Connections tab's count stays the "held" number (a test that both tabs agree, from ticket 138, keeps passing).
- [ ] On the paid workspace, the P155350, P156634 and P161305 Timeline tabs add up after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 30, 2026, orchestrator: opened at 03:50 PDT from the walkthrough's final capture; ready to launch on the owner's word.
