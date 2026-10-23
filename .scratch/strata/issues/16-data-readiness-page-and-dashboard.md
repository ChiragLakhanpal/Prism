# 16: Data readiness: the page and the first dashboard page

**What to build:** Users and the data team can see how fit each source is to support answers, on the Data readiness page in the app and on the first page of the AI/BI dashboard, both read from the same strata.ops measures. The data_readiness_for tool (one registry entry) returns the measures for a source or for the sources behind an answer. The Data tab gets its three tabs. Data readiness opens with a headline sentence built from the measures (no model writes it), then "What you can ask" (what each kind of question is ready for and what holds it back), then one row per source with the number first in each cell, a badge only for Partial or Gap, definitions in the column headers and freshness such as "Oct 22 · daily", then fixes ranked by what they would unlock. Opened from a coverage line, it shows only the sources behind that answer, with "Show all sources". Known gaps declared in the source registry, such as the FY2017–19 contract awards no dataset publishes, appear as Gap rows. Sources and licenses gives each dataset's attribution in the World Bank's format, the terms of use, the sentence on Strata's own changes and the data caveat, with the exact dataset names checked as PLAN.md section 18 asks. How Strata works states its purpose until the deck ticket fills it. The dashboard's Data readiness page is built from code and deployed with the bundle: coverage by source and fiscal year, link rates, pages read well by route, freshness, and fixes ranked by what they unlock.

Read first: DESIGN.md sections 5 (Readiness tables, Coverage line), 6 and 8; the blueprint's Data readiness wireframe and its "why" panels, and "The dashboard for the people who run Strata"; docs/PLAN.md section 9.

**Blocked by:** 06 (The app shell, deployed as a Databricks App that acts as the viewer); 07 (Kenya's procurement records, bronze to gold); 11 (The first 20 documents read into numbered passages and made searchable)

**Status:** ready-for-agent
**Area:** app
**Phase:** P1
**Design review:** yes

- [ ] Every number on the page equals its measure in strata.ops: Playwright checks the page against recorded measures, and on the workspace a direct query matches the page's Kenya award rows and STEP-reference link rate.
- [ ] Badges appear only on Partial and Gap cells, no composite score appears anywhere, definitions sit in the column headers and freshness reads like "Oct 22 · daily", per DESIGN.md section 5's Readiness tables and the Data readiness wireframe.
- [ ] The FY2017–19 awards row shows as a Gap with "none published".
- [ ] Opening the page from a coverage line shows only the sources behind it and a "Show all sources" link that restores the full table.
- [ ] Sources and licenses lists every ingested dataset with the line "The World Bank: [Dataset name]: [Data source]. License: CC BY 4.0.", the terms-of-use link, the changes sentence and the data caveat word for word from DESIGN.md section 8, and the checked dataset names are recorded in the source registry.
- [ ] The dashboard deploys from code with one command, its Data readiness page shows the same numbers as the app for the same date, and its charts use DESIGN.md section 6's colors (category colors in order, text variants for essential marks).
- [ ] Loading, empty, error and filtered states are captured at 1440, 1024 and 390 px; below 768 px the tables become cards; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: ticket 11 landed in build/strata (merge commit e0721da) and asked for one reading rule here. The Data readiness page reads the latest row for each source, subject and measure of `strata.ops.data_readiness` (the newest `as_of`), never a sum or an average over runs; ticket 07 wrote the measure shape (a nullable count and denominator, `as_of` and a detail sentence) and tickets 08 and 11 write their measures the same way. Ticket 11 also noted that `contact_details_removed` reads 0 of 0 on every run after the first, so the page must show a measure whose latest row is 0 of 0 without calling it a failure; the first run's row is the one that counts, and ticket 43 fixes the measure itself.
