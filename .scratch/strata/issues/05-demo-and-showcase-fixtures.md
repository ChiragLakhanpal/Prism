# 05: Fixtures for the demo plan (P156634) and the showcase project (P130164)

**What to build:** A small, real, offline copy of the evidence behind the demo and the showcase, which every seam's tests run on. Record the source pages and documents for: the Kenya Water and Sanitation Development Project (P156634), including the Northern Water Works Development Agency's Procurement Plan versions up to and including October 9, 2026, the August 17, 2026 plan that first lists KE-CWSB-567630-CW-DIR, award notices for its activities, its loan history (closing-date changes), its ISRs and its PAD; the India Rajasthan Road Sector Modernization project (P130164), including the PAD scan, ISRs 7 and 12 (and the rest of the ISR series if available), the ICR of October 10, 2019, the ICR Review of March 27, 2020 and its May 4, 2023 re-issue, and the award notice for IN-RRSMP-7431-CW-RFB; at least 25 comparable works packages whose notices and signed contracts join on the STEP reference, at least 3 still open; and the project, IEG rating, loan, CPIA and WGI records for Kenya and India.

Alongside, write a ground-truth file that lists each expected value with where it came from (the values in the spec's Testing Decisions, plus the plan rows shown in the blueprint's Check a plan wireframe), and make sure the fixture contains the awkward cases the lakehouse must handle on purpose. A recording command refetches everything and shows a diff, so the fixture can be refreshed deliberately, for example on demo day.

Read first: docs/PLAN.md section 3; the blueprint's Check a plan, Evidence drawer and Project timeline wireframes; the spec's Testing Decisions.

**Blocked by:** 01 (Repo scaffold with fairshare's rules, hooks, shell and the offline gate)

**Status:** in-progress
**Area:** data
**Phase:** P0
**Design review:** no

- [ ] The fixture loads with the network off and stays small enough that the gate remains under two minutes (its size is printed by the gate).
- [ ] The ground-truth file lists every value named in the spec's Testing Decisions with its source (document type, project, date, paragraph and page, or record id), including ICR P130164 ¶54, ¶55 and ¶78, and a test confirms each quoted string occurs word for word in the recorded text on the stated page, for example "108 of 328 cases had to go through rebidding" in ICR P130164 on PDF page 23.
- [ ] The October 9, 2026 NWWDA plan's eight activities are present with the amounts, methods, market approaches, review types and statuses shown in the blueprint's Check a plan wireframe.
- [ ] At least 25 comparable works packages with notice and signed-contract dates join on the STEP reference, at least 3 of them still open, and one documented criteria variant leaves fewer than 20.
- [ ] The fixture includes at least one notice with a contact name, email and phone number; a loan number in each of its four forms; a joint-venture award; an "INDIVIDUAL CONSULTANT" row; a document dated in the future; a signed plan row with an Actual Amount of 0.00; and a reference whose method differs from the Method column.
- [ ] The recording command refetches every source and prints a diff, overwriting only when asked.
- [ ] Every recorded file carries its source and its license line (CC BY 4.0).

## Comments
- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/05-demo-and-showcase-fixtures. Credentials are still missing, so anything that needs the workspace is parked in docs/workspace-catchup.md. Sources are fetched from the World Bank's public sites and APIs.
