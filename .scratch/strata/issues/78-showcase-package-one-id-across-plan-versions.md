# 78: The showcase package keeps one id across plan versions, or the October 9 plan's RFQ suffix is read right

**What to build:** The October 9, 2026 Procurement Plan of P156634 (document 40132287) names the showcase package as KE-NWWDA-229129-CW-RFQ in `strata.silver.plan_rows` (Signed, 300,000.00 estimated, 1,245,092.76 actual, method_original "Request for Bids", method_mapped false), while the three earlier plan versions (33014836, 40031468, 40090127) and `strata.gold.package` name it KE-NWWDA-229129-CW-RFB. On the workspace on October 26, 2026 this is why `tests/ground_truth/delay_from_first_published_planned_date.sql` and `agency_track_record_nwwda_2026_10_09.sql` return no rows, and why `ops/demo/ready.py`'s P156634 recheck reports "Signed far above its estimate: KE-NWWDA-229129-CW-RFQ fired on the workspace and not in the fixture" and the RFB one "no longer fired". Settle it from the recorded copy of document 40132287 under `data/fixture/recorded` (the fixture database holds the reader's rows for it): if the PDF writes RFB and the reader read RFQ, fix the reader and the test that pins its output; if STEP renamed the package (RFQ in the PDF, with the method still "Request for Bids"), make the package id follow the activity across versions, so `strata.gold.package`, the two ground-truth queries and the demo recheck see one package with its history, and say in the done comment which it was. Either way the recheck on the fixture and on the workspace must agree on the showcase package.

Read first: `src/strata/reader/` and `src/strata/lakehouse/plans.py` (the plan reader and where `plan_rows` is written; the activity id and method columns from tickets 08 and 42), the gold package SQL under `src/strata/lakehouse/gold/`, `tests/ground_truth/delay_from_first_published_planned_date.sql` and `agency_track_record_nwwda_2026_10_09.sql`, `ops/demo/ready.py` step 4, the catch-up file's blocks 48-2 and 48-3 of October 26.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P2
**Design review:** no

- [ ] The recorded October 9 plan settles the id, with the page and the row quoted in the done comment; the fixture's `plan_rows` and `gold.package` agree on the showcase package's id, and the ground-truth queries that name it return their expected rows on the fixture.
- [ ] A test pins the settled reading (the reader's output for that plan version, or the package's history across the four versions), and the existing plan and ground-truth tests pass.
- [ ] After the second session's next bronze_to_gold run from a snapshot, the two ground-truth queries return rows on the warehouse, and the demo recheck reports the showcase package the same way on the fixture and on the workspace (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 02:56 PDT from the second session's demo-ready runs (48-2 and 48-3). On the demo path: the showcase question's package must read the same on the fixture and on the workspace.
