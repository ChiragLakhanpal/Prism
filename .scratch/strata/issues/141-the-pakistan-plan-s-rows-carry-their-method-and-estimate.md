# 141: The Pakistan plan's rows carry their method and their estimate as the plan prints them

**What to build:** On October 29, 2026 the demo walkthrough's second capture of P155350's Procurement tab (Sindh Resilience, Pakistan; the plan of June 10, 2024, 15 activities, document read "10 of 10" pages) showed every row's estimate as "Not in the plan" and rows whose references end in -RFP (PK-SID-2962-CW-RFP to PK-SID-2969-CW-RFP) with Method "Request for Bids", while the plan's own table prints an estimated amount for each row and names Request for Proposals for those. The layout parser (`src/strata/reader/layout.py`, `src/strata/reader/step.py`) read this plan's table with its columns shifted or its method column mapped to the reference's kind. Find the cause on the stored pages of document 40132287's Pakistan counterpart (the plan's document id is in `strata.silver.plan_versions` for P155350) and fix it in the reader in one place: the estimate column is read when the table prints it, and the method comes from the plan's Method column, with the reference's kind (-RFP, -RFB) as a check that disagrees loudly in the row's data rather than silently winning. Record this plan's page as a fixture page with a test for its rows (the method, the estimate, the description), and prove the other demo plans (P156634's October 9, 2026, P130164's June 20, 2018, P161305's September 28, 2026) read as before. The live proof is the orchestrator's: after the merge, the plan rows of P155350's plan are written again from the stored pages (ticket 122's rewrite path, no fetch) and the Procurement tab shows estimates and the right methods, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `src/strata/reader/layout.py`, `src/strata/reader/step.py` (ticket 131's repair sits after the read), `src/strata/lakehouse/plans.py` (`write_rows`), the catch-up blocks of tickets 122 and 131 (the rewrite path), GLOSSARY.md (method names), `config/method_names.toml`.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** reader
**Phase:** P4
**Design review:** no

- [ ] The Pakistan plan's rows read their estimate and their method as the plan prints them (a fixture page and a test), and a reference kind that disagrees with the method column is kept as data, not used to overwrite it.
- [ ] The three other demo plans read as before (their existing tests pass unchanged).
- [ ] On the paid workspace, after the rewrite of P155350's plan rows, the Procurement tab shows estimates and Request for Proposals on the -RFP rows (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 21:03 PDT from the walkthrough's second capture.
