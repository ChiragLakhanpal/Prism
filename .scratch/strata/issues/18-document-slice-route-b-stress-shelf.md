# 18: The document slice, the page router's Route B and the stress shelf

**What to build:** The pilot slice's documents are read, scans and tables included, and the five hardest documents sit on a stress shelf that the Data readiness page shows. The page router now chooses per page: Route A for clean published text, Route B for scanned pages, tables (PAD risk tables and procurement annexes, the ICR data sheet, ISR ratings, Procurement Plans) and figures, sent to ai_parse_document or, if day-one test 3 failed, Content Understanding. A table becomes typed rows plus one summary passage that never backs a number. The slice file drives scope: water and transport projects in Kenya, Bangladesh, Vietnam and Pakistan approved FY2012–2025, with their PADs, ISRs, ICRs, ICR Reviews, PPARs, Project Papers for restructurings, CPFs and Procurement Plans (the latest per implementing agency and the version before it, plus the earliest versions that list each activity). Every document is parsed once under the daily page cap, only changes are embedded, and the index stays synced. ISR rating history is read from the ISRs themselves, because the projects API keeps only the latest. Notices' scope and qualification text is indexed as passages. The stress shelf holds the P130164 PAD (a 100-page scan with a garbled two-column risk annex), the longest PAD in the slice, a Procurement Plan with hundreds of rows, a completion report in French, and a document over 500 pages if one exists, divided past the parser's limit. Each has a recorded outcome, shown honestly on the Data readiness page.

Read first: docs/PLAN.md sections 3 and 5; the blueprint's "How documents and records become evidence" (including "The stress shelf") and Data readiness wireframe; DESIGN.md section 5 (Readiness tables); docs/agents/areas/knowledge.md.

**Blocked by:** 11 (The first 20 documents read into numbered passages and made searchable); 16 (Data readiness: the page and the first dashboard page); 17 (Every structured source, for every country, kept as published)

**Status:** done
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
- October 24, 2026, merger: merged into build/strata as merge commit a8d605c (parents c1cdf80 and ff9f46b, so the branch's history is kept). The history scan found no keys. Git merged it with no conflicts. The branch changes no package files, and `scripts/install` ran before the commit anyway. The worktree that built it was `.claude/worktrees/wf_6d34397a-5fa-5`; I removed it after this commit, and the branch stays.
  - **The gate.** Git ran it before the merge commit, and it passed in 87.6 seconds. By hand on build/strata after the merge, it passed in 67.2 seconds and finished at about 08:30: the Python tests took 53.4, the wizard and day-one tests 44.8, and Playwright 38.6. Ticket 43 is already asked to bring it back under a minute.
  - **A red gate on the way, not from this branch.** When I started, the main checkout held one uncommitted change: the credentials wizard, still running in the user's terminal, had written day-one test 7 as failed at 08:20. I committed it (85bbf91). The first merge's gate then failed in the ops lane, because two of ticket 03's tests in `ops/dayone/tests/test_results_document.py` require the committed document to be the template. I aborted that merge, undid 85bbf91 with a plain revert (c1cdf80), merged again, and put the wizard's result back in the working copy as the uncommitted change it was. See parked decision 6.
  - **Evidence.** Three rounds. Review r3 (`.notes/18-review-r3.md`) approved with 0 blocking and 12 polish findings. Design r3 (`.notes/18-design-r3.md`) passed with 0 blocking and 6 polish findings. Critique r3 (`.notes/18-critique-r3.md`) does not block, and its lowest score is 4. Verify r3 (`.notes/18-verify-r3.md`) passed all nine criteria on the fixture:
    - The criteria select 17 slice projects, counted three ways, and the measure records "111 fewer" than PLAN.md's 128, because the fixture's gold tables hold no such project for Bangladesh, Vietnam or Pakistan.
    - A second run the same day parsed 0 pages and embedded 0 passages. With the cap set to 40, both readers together stayed at 40 pages on each of two days.
    - The P130164 annex gave 8 rated risks on pages 65 to 70, matching the scan's text layer.
    - The shelf plan gave 212 STEP rows for its 212 activity references.
    - All 173 passages of the French report carry `fr`.
    - No recorded document is over 500 pages (the longest has 103). With a 40-page part size, the 103-page PAD was read in 3 parts with the same passages.
    - A number resting only on a table summary is removed with `number_only_in_table_summary`.
    - "similar experience" returns OP00118817/v1/s5 and OP00128730/v1/s6 first.
    - The shelf shows five rows at 1440, 1024, 768, 390 and 320 px, with 0 axe violations.
    - The ticket's own Python tests take 6.7 seconds and `web/tests/shelf.spec.ts` 16.8 seconds on one worker.
  - **Parked criteria.** The live halves of criteria 1, 2, 6 and 8.
  - **Workspace results.** Nothing ran. `guard.py --env-keys` showed `DATABRICKS_HOST`, `DATABRICKS_WAREHOUSE_ID` and `AI_SEARCH_ENDPOINT` set, and the Databricks token, the Azure OpenAI keys, Foundry, Genie and Application Insights missing. Day-one test 7 had also just recorded that Databricks refused the token and the service principal. I parked five steps in `docs/workspace-catchup.md`, in the order to run them. "Ticket 18, step 1 of 5" checks that `strata.gold.passage` has no `notice_url` (the builder's step 4; if it does, stop, because rule 5 and the guard rule out removing a column). Step 2 is the live slice run, step 3 the second run the same day, step 4 the same-rows check of `slice_projects.sql`, and step 5 the AI Search check. The builder named `search_live.py` for step 5, but that script asks only ticket 11's question, so the block adds a one-line override that asks `search-passages-similar-experience`.
  - **Follow-ups, not blocking.**
    1. Verify F1: a page the layout parser failed on is tried again on every later day and counts against that day's cap (decision 1).
    2. Verify F2: 10 of the shelf plan's 212 rows lost or cut their Component at row and page ends. A plan check that shows Component would show them wrong.
    3. Verify F3 and review P2: P161305's documents are listed but not fetched, and no measure says so. The "Pilot projects read" window gives a reason that is false on the fixture.
    4. Review P3 to P11: "hand count" wording in two places, four lists of document types without Project Papers and PPARs, dead window copy, the PPAR test stopping at 2.3, "1 of 17" and "three projects" asserted as literals that `values.toml` does not hold, "approved" in `values.toml`, `config/sources.toml` read again for every notice row, the page's own list of rule kinds, and DESIGN.md's dense Coverage sentence.
    5. Design P1 to P6 and the critique's copy points: the Read well window contradicts itself, the 41-word scope caption, the pilot project windows, "across 3 parts", a notice's first sentence shown as its section, skeletons shorter than their rows at 768 px, "Open at page 65" breaking at 1024 px, the parser named `pdftotext -bbox`, and the settings 500 and 30 drawn like measures.
    6. `ops/documents/search_live.py` needs a question option, so step 5 needs no override.
  - **Decisions parked for the user.**
    1. Retrying a failed parser page (verify F1). As built, it is tried again each later day and counts against the cap. Simplest: keep it, and decide before the full-slice live run whether to wait a set number of days or cap retries in `config/thresholds.toml`.
    2. The P130164 annex count. Count Annex 4's rated risks (PDF pages 65 to 70) from the page images, decide whether "Overall Implementation Risk" is a risk (7 risks plus an overall rating, or 8 rated risks), and add `expected_rows` and `counted_on` to `config/slice.toml`. Until then the row shows 8 rated risks with nothing to check them against.
    3. CPFs are left out, because a CPF is listed by country and the reader lists a project's documents. Simplest: a follow-up ticket for a country-level listing.
    4. The Project Paper's tables (review P1). Default: end the numbered body at "III. SUMMARY OF CHANGES", so those pages give no paragraph passages and leave the headline's paragraph-number count (now "70 of 264"). The other choice is to send them to the layout parser as tables.
    5. The combined "Project reports" row stays in place of one row per collection. Design-lead recommends keeping it.
    6. The wizard's results and ticket 03's tests. The wizard writes `docs/day-one-results.md`, and two of ticket 03's tests fail once that file is committed with any result in it. So the change stays uncommitted in the main checkout, and while it is there the gate refuses every commit that stages a file other than Markdown ("Some changes to tracked files are not staged"). Simplest: change those two tests to check the document's shape instead of "not run", then commit the wizard's results.
  - **What this unblocks.** Tickets 20, 21 and 29, now in-progress. Tickets 27 and 32 still wait on 25, and 31 waits on 15 and 29.
