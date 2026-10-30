# 143: The plan check says "the earliest plan I have read", and the disagreements list names a package once with its records

**What to build:** On October 30, 2026 the demo walkthrough's midnight capture showed two sentences that say more or less than the records, after ticket 134 fixed the Procurement tab's wording: (a) the Kenya water plan check (P156634, the plan of October 9, 2026) still reads "This is the earliest plan I have from this agency" while the Documents tab lists 240 Procurement Plan versions for the project, most "Not read"; the honest sentence is "This is the earliest plan I have read from this agency", with the Documents tab's link as on the Procurement tab (ticket 134's rule, applied to the plan check's change line and to `copy.checkPlan` keys that say "I have" for a plan); (b) the Timeline tab's "Where the records disagree" list (P156634: "Six pairs"; P161305: "Two pairs") lists a package once per record that disagrees with the plan, so KE-NWWDA-199471-GO-RFQ appears twice with the same dates and "six pairs" is four packages; the list should name each package once with its records under it ("KE-NWWDA-199471-GO-RFQ: the plan's September 20, 2021 against the notice's March 3, 2021 and the award record's April 2, 2021") and the count say "four packages, six records" (the tool's rows stay as they are; the grouping is the page's, in `src/strata/server/timeline.py` next to ticket 136's groups). Tests on the fixture for both; the live proof is the orchestrator's after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds; no design review.

Read first: `web/src/copy.ts` (the checkPlan and timeline keys that say "I have"), `src/strata/server/changes.py` (the change line), `src/strata/server/timeline.py` (the package disagreements list, ticket 136's groups), `web/src/components/TimelineTab.tsx`, ticket 134's done comment.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** web
**Phase:** P4
**Design review:** no

- [ ] Every sentence on the plan check that says Strata "has" a plan says it has read it, with the Documents tab's link where other versions are listed unread (a test on P156634).
- [ ] The timeline's package disagreements list names each package once with its records under it, and its count names packages and records (tests on P156634 and P161305).
- [ ] On the paid workspace, both pages read so after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 30, 2026, orchestrator: opened at 03:08 PDT from the walkthrough's midnight capture.
