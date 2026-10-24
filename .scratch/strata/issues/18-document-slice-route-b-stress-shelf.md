# 18: The document slice, the page router's Route B and the stress shelf

**What to build:** The pilot slice's documents are read, scans and tables included, and the five hardest documents sit on a stress shelf that the Data readiness page shows. The page router now chooses per page: Route A for clean published text, Route B for scanned pages, tables (PAD risk tables and procurement annexes, the ICR data sheet, ISR ratings, Procurement Plans) and figures, sent to ai_parse_document or, if day-one test 3 failed, Content Understanding. A table becomes typed rows plus one summary passage that never backs a number. The slice file drives scope: water and transport projects in Kenya, Bangladesh, Vietnam and Pakistan approved FY2012–2025, with their PADs, ISRs, ICRs, ICR Reviews, PPARs, Project Papers for restructurings, CPFs and Procurement Plans (the latest per implementing agency and the version before it, plus the earliest versions that list each activity). Every document is parsed once under the daily page cap, only changes are embedded, and the index stays synced. ISR rating history is read from the ISRs themselves, because the projects API keeps only the latest. Notices' scope and qualification text is indexed as passages. The stress shelf holds the P130164 PAD (a 100-page scan with a garbled two-column risk annex), the longest PAD in the slice, a Procurement Plan with hundreds of rows, a completion report in French, and a document over 500 pages if one exists, divided past the parser's limit. Each has a recorded outcome, shown honestly on the Data readiness page.

Read first: docs/PLAN.md sections 3 and 5; the blueprint's "How documents and records become evidence" (including "The stress shelf") and Data readiness wireframe; DESIGN.md section 5 (Readiness tables); docs/agents/areas/knowledge.md.

**Blocked by:** 11 (The first 20 documents read into numbered passages and made searchable); 16 (Data readiness: the page and the first dashboard page); 17 (Every structured source, for every country, kept as published)

**Status:** in-progress
**Area:** knowledge
**Phase:** P2
**Design review:** yes

- [ ] The number of slice projects equals the count the slice criteria select from the projects table at run time, and any difference from PLAN.md's 128 is recorded with its reason.
- [ ] A second run parses no pages; the page cap is respected; strata.ops shows documents per type and fiscal year, pages per route and the read-well rate per route.
- [ ] The P130164 PAD's risk annex outcome is recorded as it is: its rows recovered, or the annex listed under "What holds it back" as unreadable, as the Data readiness wireframe anticipates.
- [ ] The stress-shelf Procurement Plan yields one STEP row for every activity reference found in its text.
- [ ] Passages from the French completion report carry the language fr.
- [ ] A document over 500 pages, if one exists, is read in parts under the parser's limit with correct PDF page numbers; if none exists, the shelf records that.
- [ ] Through the answer contract, a scripted claim whose number rests only on a table summary passage is removed.
- [ ] A search for "similar experience" returns notice passages with their notice ids.
- [ ] The Data readiness page gains a stress-shelf table of five rows, each with its outcome, numbers first, a badge only for Partial or Gap, and an "Open at page" link, per DESIGN.md section 5's Readiness tables and the Data readiness wireframe; it is captured at 1440, 1024 and 390 px and passes axe.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/18-document-slice-route-b-stress-shelf, as soon as ticket 16 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
