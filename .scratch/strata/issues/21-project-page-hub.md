# 21: The project page as the hub: All projects, Summary, Procurement and Documents

**What to build:** Every P-code in Strata leads to a project page that works as the hub, and every project can be found from All projects. All projects lists every ingested project with search by name, P-code and country. The project page gets its full header and tab row, with Summary, Procurement and Documents built here (Timeline and Connections appear when their tickets land). Summary renders from precomputed records before any model call: approval and closing dates and their changes, sectors, implementing agencies, commitment, disbursed and canceled amounts, the latest ratings and ESF risk, each with its source line; no model writes it. Procurement lists each implementing agency's plans (opening Check a plan) and the project's packages by STEP reference, and shows what changed between a plan and the version before it (activities added or dropped, re-dated or re-estimated). Check a plan gains "Save as the baseline", which records a check of the plan agreed at negotiations; later checks then also report delay against that baseline, alongside delay from the first published planned date. Documents lists every document by type and date with its public date. The in-app source view opens a document at a page and paragraph, shows its passages with that paragraph highlighted, and links to the World Bank's PDF at that page; the evidence drawer's "Open at page N" now opens it. A shared rule makes every P-code anywhere in the app a link to its project page.

Read first: docs/PLAN.md section 8; DESIGN.md sections 5 and 10; the blueprint's "Navigation and roles" ("The project page is the hub") and the Project timeline wireframe's header and tab row; docs/agents/areas/app.md.

**Blocked by:** 10 (Check a plan, on screen, for the NWWDA plan); 18 (The document slice, the page router's Route B and the stress shelf)

**Status:** in-progress
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] All projects lists every ingested project with a count line ("Showing 1–20 of N projects"), searches by name, P-code and country, and sets P-codes in Roboto Mono as links.
- [ ] P130164's header reads "Rajasthan Road Sector Modernization · P130164 · India · closed" with the implementing agency line, and the tabs run Summary, Procurement, Timeline, Documents, Connections in that order once built, as in the Project timeline wireframe.
- [ ] P130164's Summary renders without any request to a model route (checked by Playwright), and every value on it has a source line.
- [ ] P130164's Documents list the PAD (October 1, 2013), the ISRs, the ICR (October 10, 2019) and the ICR Review (March 27, 2020, re-issued May 4, 2023), with dates matching the ground-truth file.
- [ ] The source view opened at the ICR, page 23, paragraph 54 highlights ¶54, and the drawer's "Open at page 23" lands there.
- [ ] For the NWWDA series, the changes between the October 9, 2026 plan and the version before it match a direct comparison of the two versions' rows (activities added, dropped, re-dated and re-estimated).
- [ ] After "Save as the baseline" on a plan check, a later check of the same plan reports delay against the baseline and against the first published planned date, each labeled.
- [ ] A Playwright sweep of every route finds no P-code that is not a link to its project page.
- [ ] Tabs, tables and source lines follow DESIGN.md section 5; loading, empty and error states are captured at 1440, 1024 and 390 px; the Summary loads within its budget on a throttled 3G profile; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/21-project-page-hub, as soon as ticket 18 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
