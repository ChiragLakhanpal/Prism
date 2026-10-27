# 86: The passage reader fetches and parses one document at a time, so the first passage lands minutes into the task

**What to build:** On the paid workspace's first run of the nightly task `parse_and_embed` alone (run 564462742591748, October 27, 2026, 00:27 to 01:31 UTC), the plan reader finished P130164's 15 plan versions in 12 minutes, and the passage reader then spent the rest of the night's 60-minute document budget (`ingestion.document_host_minutes` in `config/thresholds.toml`) fetching P156634's whole document list and its 163 texts (193 MB into `strata.bronze.document_texts`, 16,746 pages into `document_pages`) and stopped at 01:30:35 UTC with the note "I stopped reading documents on October 27, 2026, after the night's 60 minutes for the document host" before it had parsed one document: `strata.silver.documents`, `strata.silver.passages`, `strata.gold.passage` and `strata.ops.documents_read` all held 0 rows. Ticket 72's per-document writer covers the parse and the write, not the fetch that comes before them, and the offline fixture never showed the gap because its documents are recorded. Change the reader so it works one document at a time: fetch a document's text, parse it, write its passages and its `documents_read` row, then fetch the next, with the budget checked between documents and between pages as ticket 72 asks, so a stopped run keeps every document it finished and the first passage lands minutes into the task. Keep the same rows, the same `public_from` and the same dedup rule, so a rerun writes nothing twice, and keep the paced fetcher from ticket 66. Prove it on the fixture with a fake host that counts fetches: after the first document's parse, its passages are in the table before the second fetch starts, and a budget that expires after two documents leaves two documents written and the rest listed as not read; the existing documents and plan tests pass unchanged. The live proof is the next `parse_and_embed` run on the paid workspace that has documents to fetch (a project added to `config/slice.toml`, or the texts bronze already holds being parsed inside one budget), with `strata.gold.passage` holding rows at the end, recorded in the catch-up file.

Read first: `src/strata/lakehouse/readers.py` (the passage reader's loop and the budget), `src/strata/reader/documents.py` (`LiveDocuments`, the fetch of a project's list and texts), `src/strata/lakehouse/passages.py` (the per-document writer from ticket 72), `ops/documents/run_live.py`, `tests/test_documents_run.py` and `tests/test_passages.py`, the catch-up file's block for ticket 72 (the first live reading on October 27).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P4
**Design review:** no

- [ ] On the fixture with a fake host that counts fetches, the first document's passages are written before the second document's text is fetched, and a budget that expires after two documents leaves two documents written, the rest listed as not read, and a rerun writing nothing twice; the existing documents and plan tests pass unchanged.
- [ ] The budget is checked between documents and between pages, and the task's run record names the documents written and the documents left.
- [ ] On the paid workspace, the next `parse_and_embed` run that reads documents ends with rows in `strata.gold.passage` inside its budget (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 21:05 PDT with the user's go-ahead for the overnight build, from the second session's reading of run 564462742591748. Tonight's second reader pass parses the texts bronze already holds, so the demo has passages before this lands; the ticket is for every later project.
