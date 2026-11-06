# 149: The Deep research tab shows the brief and prints it as the sample's PDF

**What to build:** A sixth tab on the project page, "Deep research", after Connections (`copy.projectPage.tab`, `routes.ts` `TAB_PATH`, address `/projects/:pid/research`). It shows the latest brief from `GET /api/projects/{pid}/research` (ticket 148), runs one with "Research this project" (`POST`, the answer stream's steps shown while it runs, as the ask box shows them), and prints it with "Download as PDF". The brief's look is the sample, `.notes/prism-sample/prism-deep-research-P156634-sample-v5.pdf` in the main checkout, built by `.notes/prism-sample/template/build5.py`: the same type scale, the World Bank palette only (navy, two blues, greys), markers as small numbered links, sections in the same order (the picture and the bottom line; developments newest first; by site, with the Sentinel-2 grids side by side; what people are saying; what this means for procurement; sources). On screen the sections stack in the page column with the markers opening the evidence drawer (ticket 148's reader) and each item's "Open the source" in a new tab; removed sentences show under the brief with their reasons, as answers do.

The PDF is the browser's print of the brief: a print stylesheet puts each section on its own Letter sheet with the sample's running header (project and section) and footer (Prism, the read date, the one-line disclaimer, the page number), the cover sheet first; "Download as PDF" calls `window.print()` on a view that hides the app's chrome. No server-side renderer. The copy (button, states, section titles, the one-line disclaimer, "not reached", "undated") lives in `web/src/copy.ts` under `research`, and the copy lint passes.

States: no brief yet (the button and one sentence on what the run reads); running (steps); brief shown; a source not reached (one line under the section it feeds, from the run's coverage); the service did not answer; an account that cannot read Prism's tables.

Tests on seam 4 (Playwright against the mocked API with ticket 148's recorded responses): the tab opens, the brief renders every section with its markers, a marker opens the drawer, the print view has one sheet per section with header and footer (check the DOM under `@media print` emulation), axe at WCAG 2.2 AA, keyboard reach to the button and the markers, 320 px reflow. Keep the gate under 150 seconds.

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD, against the response shapes ticket 148 fixes, with mocked responses; merge 148's branch into yours when it lands. Write every new sentence with the name Prism. No design review.

Read first: the sample brief and `build5.py` (and `report5.html` beside it, for the CSS); `web/src/pages/ProjectPage.tsx`, `pages/project/SummaryTab.tsx`, `components/Answer.tsx`, `AnswerPanel.tsx`, `EvidenceDrawer.tsx`, `lib/sse.ts`, `lib/answer.ts`, `copy.ts`, `routes.ts`; DESIGN.md sections 4, 5 and 7; `docs/agents/areas/app.md`; `docs/agents/unslop.md`.

**Blocked by:** None (can start immediately; merges after 148)

**Status:** in-progress
**Area:** app
**Phase:** P5
**Design review:** no

- [ ] The Deep research tab is the sixth tab, at `/projects/:pid/research`, and shows the stored brief with every section in the sample's order and look (Playwright).
- [ ] "Research this project" runs the stream and shows its steps; a source not reached shows as one line, not an error (Playwright on mocked streams).
- [ ] Markers open the evidence drawer and the item's source link opens in a new tab (Playwright).
- [ ] "Download as PDF" prints one sheet per section with the sample's header, footer and cover (print emulation test).
- [ ] Axe at WCAG 2.2 AA, keyboard reach and 320 px reflow pass; the copy lint passes.
- [ ] The gate passes under 150 seconds on the worktree.

## Comments

- November 5, 2026, orchestrator: opened at 18:00 PST. No design review, by the user's instruction of tonight.
