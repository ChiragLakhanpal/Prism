# 154: Three more research sources a procurement specialist reaches for: site conditions, the agencies' own statements, and the sanctions check

**What to build:** The user's instruction of November 5, 2026 at 20:15 PST: beyond news, complaints, satellite and field photos, add what helps a procurement specialist, still pre-seeded. Three sources in `config/research.toml`, each a reader in `src/strata/research/sources/` with ticket 147's interface and item shape, recordings for the seed, and their place in the brief:

1. `site_conditions`, kind `site_condition`: disasters at the project's sites from GDACS, `https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH?country=<country name>&fromDate=<approval date or two years back>&toDate=<today>` (answered 200 on November 5 with Kenya's drought alerts of 2025 and 2026: event type, name, dates, alert level and the report's address). One item per event whose name or area includes the project's country, with `observed` as the event's start, the alert level in the text, and the report as `url`. Attribution: GDACS, the Global Disaster Alert and Coordination System of the European Commission and the United Nations. ReliefWeb's API needs an approved appname (403 on November 5), so it is listed as not connected with that reason. Record Kenya's and India's answers tonight for the seed.
2. `agency_statements`, kind `agency_statement`: the implementing agencies' own news pages, listed in the registry under `[[sources.agency_statements.pages]]` by the agency's short name with the page's address (to start: NWWDA `https://nwwda.go.ke/index.php/news-events`, which answered 200 on November 5 with dated entries such as the Eldas town water supply commissioning of June 2, 2026; CWWDA `https://cwwda.go.ke/news`, whose entries are mostly PDF notices; add KeNHA's and the Kwale and Mombasa water companies' pages if they answer the named client). The reader lists the page's entries (title, date from the entry or its address, link) for the agencies the project record names, fetches each entry's page with the named client, and keeps it as an item with the agency as `author`. A page that refuses gives `reached = false`.
3. `sanctions`, kind `sanctions`: the World Bank's listing of ineligible (debarred and sanctioned) firms and individuals, cross-checked against every supplier on the project's contracts (`strata.gold.contract_supplier` and `strata.gold.contract` for the project), by exact name and by a normalised name (case, punctuation, legal suffixes). The list's API needs a subscription key (401 on November 5), so the reader reads a copy downloaded from the page's export, placed at `data/research/sanctions/<yyyy-mm-dd>.xlsx` or `.csv` (public data, committed when present), and names the copy's date in its items. It emits one summary item per run ("<n> suppliers checked against the list of <date>; <m> on it") and one item per hit with the firm, the grounds and the dates as the list prints them; with no copy present it gives `reached = false` with the note "the list needs a download from the page", so the brief's "could not see" says the sanctions check did not run. `research_evidence`'s summary record gains `suppliers_checked` and `suppliers_sanctioned`. Add to docs/STATUS.md's morning lines, in your report, the one line the user can run to download the list later (the page's export, by hand in a browser), without changing STATUS.md yourself.

The writer's instruction (`src/strata/agent/instructions/research_brief_writer.md`) gains three short rules: a site condition is written as a condition at a site with its dates and alert level, never as a cause of a delay unless a source says so; an agency statement is the agency's side, named as such; the sanctions line states the count checked and the count found, and nothing about a firm not on the list. The registry also lists `tender_disputes` (the Public Procurement Administrative Review Board's decisions) as not connected, with the reason that Kenya Law's and PPRA's pages did not answer the named client on November 5.

Tests (network off, on recordings): each reader turns its recording into items of the shape; the sanctions reader finds a planted exact and a planted normalised match and reports the counts, and gives `reached = false` with no file; the writer's recorded answer for the seeded P156634 run still replays (extend the seed's items with the new kinds only where the sample file lists them). Keep the gate under 180 seconds.

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD. Essentials only. Commit with plain-English messages and no trailers. Do not change ticket files, docs/STATUS.md or anything under .scratch. Report: branch and worktree, the registry entries, the recordings, each criterion's evidence, the gate's time, and the workspace steps (the App needs a redeploy; the seed picks the new kinds up).

**Blocked by:** None (can start immediately; merges after 152)

**Status:** in-progress
**Area:** knowledge
**Phase:** P5
**Design review:** no

- [ ] `site_conditions` gives GDACS events for the project's country as items with dates, alert level and report link (tests on tonight's recordings for Kenya and India).
- [ ] `agency_statements` lists and reads the agencies' own news entries for the agencies the project names (tests on tonight's recordings).
- [ ] `sanctions` cross-checks the project's suppliers against a downloaded list, reports the counts, and says when no list is present (tests with a planted list).
- [ ] The writer's instruction carries the three rules, and the seeded P156634 run still replays.
- [ ] The gate passes under 180 seconds on the worktree.

## Comments

- November 5, 2026, orchestrator: opened at 20:30 PST from the user's instruction of 20:15; probes of the same hour: GDACS 200, ReliefWeb 403 (appname), the sanctions API 401 (key), PPRA 000, Kenya Law 202 empty, NWWDA 200, CWWDA 200.
