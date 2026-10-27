# 99: Projects: sub-pages in the sidebar, a shorter project head, and Summary's finding first

**What to build:** Paste block 7 of `design-md.md`. Following and All projects become sidebar items under Projects for World Bank staff, and `ProjectsTabs.tsx`'s row goes; the officer's and the public view show All projects only. All projects is a panel named "All projects" with the search field, the count line, the table, the pagination and its source as the foot strip, as the prototype draws it; long project names (104 characters in the fixture, P180287) wrap in full. A search with no match keeps the query in the field and puts the copy file's no-match sentence, its body and "Show all projects" in the panel, with no count line, table or pager; a failed load keeps the panel's name and search and puts the error alert in the list's place. Start the project page from the design lead's brief: the head gets shorter (the agency line keeps one line with "Show all agencies", the Follow control moves to the head's right, the ID, country and status in the h1's line take weight 400); the five tabs stay tabs and take their order from the copy file only; Summary opens on its finding in the `finding` style, then its fact tables, two side by side from a page area of 75rem and one column below.

Read first: the prototype's All projects at 1440, 1024 and 390 px, with the Data switch on Longest, Empty and Error, and with the View switch on Public; the design lead's brief for the project page; the plan's sections 8.0 (Projects and the project page) and 8.4; block 7 of `design-md.md`; `web/src/pages/ProjectsPage.tsx`, `FollowingPage.tsx`, `ProjectPage.tsx`, `project/SummaryTab.tsx`; `web/src/components/ProjectsTabs.tsx`, `ProjectHeader.tsx`, `FollowControl.tsx`, `FactTable.tsx`; `web/src/routes.ts` lines 140 to 144; `web/tests/projects.spec.ts`, `following.spec.ts`, `hub.spec.ts`.

**Blocked by:** 95 (The workspace layout and the task zone parts); 91 (The class sweep: every page's classes move to their roles)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] Following and All projects are sidebar items under Projects for World Bank staff, the current one carrying the mark and Projects keeping 600, the sub-tab row is gone, and the Projects item opens Following for staff and All projects for everyone else (`projects.spec.ts`, `following.spec.ts`).
- [ ] All projects is one panel with its search, count line, table, pagination and foot strip, its P-code links in 24 px boxes, a 104-character name wrapping in full, and cards below a page area of 34rem; with `projects-no-match.json` the panel keeps "atlantis" in the field and shows the no-match sentence and "Show all projects" with no table.
- [ ] On P156634 at 1440 px the project's tab row starts within 200 px of the page head's top, the agency line keeps one line with "Show all agencies", the Follow control sits at the head's right, and the tab order comes from the copy file alone (`hub.spec.ts`).
- [ ] Summary opens on its finding in the `finding` style, its fact tables sit two side by side from a page area of 75rem and in one column below, "Moderately Unsatisfactory" and "Projects API, ISR of Dec 28, 2018" each keep one line at 1280 and 1440 px, and Summary still renders from one request of at most 15 KB within the 3G budgets.

**Gate seconds added:** about +0.3 (the no-match state; the sub-tab row's tests become sidebar tests in place).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. Settles in full ticket 62's project tab order in two lists (line 66) and ticket 59's Fact table widths at 1200 and 1280 px (line 47). Specs to update: projects.spec.ts, following.spec.ts, hub.spec.ts (and sweep.spec.ts where it lists the sub-tabs). Gallery states: captures for All projects (populated, no match, error), Following, and P156634's Summary and Procurement at three widths. First wave of the page tickets.

- October 27, 2026, pm: routed from the reviews of tickets 90, 91, 92 and 94:
  - On the Procurement tab, each agency heading is an `h3` that carries `text-h2`, so it draws at 18/600, the same as the zone's `h2` "Procurement Plans" above it. Move `ProcurementTab.tsx` lines 84, 123 and 172 and skeleton line 194 to `text-h3`, the same for `DocumentsTab.tsx` line 250 where it sits under an `h2`, and choose `text-h3` for `FactTable.tsx` line 64 when the table sits under an `h2`. (ticket 90, `.notes/90-critique.md`; ticket 91, `.notes/91-critique.md`)
  - Connections keeps a hover rule outside the pointer media query: `has-[a[data-node-link]:hover]:bg-tint-hover` in `ConnectionsTab.tsx` lines 166 and 209. (ticket 90, `.notes/90-verify.md`, deferred)
  - `EvidenceTrail.tsx` line 216 measures a lane label at `type.s` with no tracking, but the label draws in `text-chart-label` (12 px, +0.02em), so a disagreement chip could sit up to about 2 px into it; measure with the chart label's size and tracking. (ticket 91, `.notes/91-verify.md` follow-up 4)
  - In the rail, the current section loses its tint and bar when one of its sub-items is the page, which breaks DESIGN.md section 2's one current mark and WCAG 1.4.1. It shows once this ticket fills the sidebar's sub-item slot (102 and 104 fill it after). The fix is the `RAIL_CURRENT` classes in `.notes/92-design.md` item 2, with a gallery-frame check. (ticket 92, `.notes/92-design.md` follow-up 2)
  - The Summary lead at 390 px ends its first line after "The project closed on", because "December 31, 2018" never breaks; leave it unless this ticket changes the sentence. (ticket 91, `.notes/91-critique.md`)
  - Beside the drawer at 1440 px the project h1 wraps to "Rajasthan Road Sector Modernization · P130164" and "· India · closed", so the second line starts with a middle dot; the shorter head this ticket builds rewrites that line. (ticket 94, `.notes/94-critique.md`)

---
