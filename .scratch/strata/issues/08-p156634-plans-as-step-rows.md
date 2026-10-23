# 08: P156634's Procurement Plans read into STEP rows

**What to build:** The Northern Water Works Development Agency's Procurement Plans for P156634 become STEP rows with planned and actual dates for every step, and every activity knows its first published planned date, so delay can be measured the way PLAN.md defines it. Plan versions come from the documents API as one series per implementing agency, each with its disclosure date as public_from. The published text, though its tables scramble, is enough to find the earliest version that lists each activity reference; only those versions, the latest one and the version before it go through the layout parser (ai_parse_document, or Content Understanding if day-one test 3 failed). Silver plan rows use STEP's own columns and values word for word (Activity Reference No., Description, Method, Market Approach, Review Type, Procurement Process, Estimated Amount (US$), Actual Amount (US$), Process Status, and each step's planned and actual dates). The method comes from the Method column, never from the reference. Data notes are produced where the record is weak (the reference's method differs from the Method column; a signed or completed row shows an Actual Amount of 0.00). Each page is parsed once, under the daily page cap, and pages read per route are recorded as data readiness measures.

Read first: docs/PLAN.md sections 3 and 5; the blueprint's Check a plan wireframe and "Words" section (step labels taken from STEP); the day-one results document.

**Blocked by:** 04 (The strata catalog and the bundle skeleton); 05 (Fixtures for the demo plan and the showcase project)

**Status:** ready-for-agent
**Area:** data
**Phase:** P1
**Design review:** no

- [ ] The October 9, 2026 plan's eight activities match the blueprint's Check a plan wireframe on reference, description, method, market approach, review type, estimated amount and process status.
- [ ] KE-NWWDA-229129-CW-RFB shows a contract signed January 3, 2022, 186 days after its first published planned date, with an Actual Amount of 1,245,092.76.
- [ ] KE-NWWDA-541055-CW-RFB shows a planned completion of July 31, 2026 and no signed contract.
- [ ] Data notes exist for KE-NWWDA-199461-GO-RFB (the reference says RFB, the Method column says Request for Quotations) and for KE-NWWDA-503455-CW-RFQ and KE-NWWDA-541061-CW-RFQ (Actual Amount 0.00).
- [ ] A second run parses no new pages, and the pages parsed per route appear in strata.ops.
- [ ] Lowering the daily page cap in configuration makes a run stop at the cap and record where it stopped.
