# 11: The first 20 documents read into numbered passages and made searchable

**What to build:** Twenty documents are read into numbered passages and can be searched through the search_passages tool, as the viewer and as of any date. The twenty are text-based (Route A): for P130164, the ICR of October 10, 2019, the ICR Review of March 27, 2020 and its May 4, 2023 re-issue, and the ISRs available as text, including ISR 7 and ISR 12; for P156634, its PAD and ISRs; and Kenya water and transport ICRs, ICR Reviews and PADs to make up the number. Route A divides pages on form feeds, finds headings from each document type's template, separates numbered paragraphs, and divides any paragraph over 500 tokens at a sentence end. Each passage keeps project, document type, version, public_from, section path, paragraph number, PDF page, printed page, language and parse route, and gets the short header prepended before embedding. Vectors from text-embedding-3-large at 1,024 dimensions sit in a Delta column with a Delta Sync index on AI Search; search_passages (one registry entry) runs hybrid queries with reranking and filters on project, document type, country, sector and public date. A re-issued report replaces its earlier version for current answers, while an as-of date before the re-issue still returns the original. Each passage is scanned by Prompt Shields at ingestion and the result is stored. The run writes data readiness measures (documents and pages per route, pages whose paragraph numbering was found, passages linked to a project, freshness). Offline, a fixture search adapter over recorded embeddings lets the tool tests run without the network.

Read first: docs/PLAN.md section 5; ADRs 0002 and 0004; the blueprint's "How documents and records become evidence" section and Evidence drawer wireframe; docs/agents/areas/knowledge.md.

**Blocked by:** 05 (Fixtures for the demo plan and the showcase project); 09 (The tool registry with the as-of contract, and check_plan)

**Status:** in-progress
**Area:** knowledge
**Phase:** P1
**Design review:** no

- [ ] In the fixture run, ICR P130164 ¶54 is exactly one passage, on PDF page 23 of 66, in section III.B, with its text word for word; ¶55 and ¶78 are single passages too.
- [ ] The header prepended to ¶54 before embedding reads "ICR, P130164, India, roads, III.B, ¶54, p.23".
- [ ] search_passages for "works estimates market rates rebidding" filtered to P130164 returns ¶54 in its top three, offline and on the workspace.
- [ ] As of October 1, 2019, no ICR passage from P130164 is returned; as of January 1, 2021, ICR Review passages come from the March 27, 2020 version; with no as-of date they come from the May 4, 2023 re-issue.
- [ ] A fixture paragraph over 500 tokens becomes two or more passages divided at sentence ends, sharing its paragraph number.
- [ ] Every passage has all ten fields listed above filled, checked by a schema test.
- [ ] On the workspace, 20 documents are indexed and synced, and strata.ops shows their pages per route and the share whose paragraph numbering was found.
- [ ] Every passage has a stored Prompt Shields result, and any hit is counted in the data readiness measures rather than silently dropped.

## Comments


- October 23, 2026, orchestrator: ticket 08 already fetches a project's document list and pages (src/strata/reader/documents.py: fetch_listing, fetch_url, NotFetched) and reads a page's layout through an ai_parse_document adapter with a recorded offline parser (src/strata/reader/layout.py: PARSERS, AiParseDocument; config/models.toml's [layout] parser picks one). Build on those modules and add to them; do not write a second fetcher or a second parser adapter. The 20 documents are recorded under data/fixture/recorded/documents/<project>/ as text with page maps (ticket 05). Every live call is a workspace step.
- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/11-first-twenty-documents, as soon as ticket 09 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
