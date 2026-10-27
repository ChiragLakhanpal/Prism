# 95: The workspace layout and the task zone parts

**What to build:** Paste block 5 of `design-md.md`. Build the parts every tab ticket uses and prove them on gallery states, not on the pages: the workspace layout (an answer panel and the work in columns 1 to 7, a side-panel slot in 9 to 12 from a frame of 75rem, the drawer filling from the work's end plus a gutter to the window's edge within 384 to 600 px while the side panel hides; one column below, with the side panel's content folded into the head or after the work as each page says); `PageHead` (the breadcrumb listing parents only, each link a 24 px line box, wrapping and never cut; the h1 at 24/32 and 20/28 below 48rem; an ID line; the purpose; one action slot; the alert slot; the facts line with its drawer button below the threshold); `SidePanel` (two columns of facts from 18rem of content; a row form when it holds only a sentence); `TaskZone` with its panel and row forms, number column, tag slot (at the header's right, or under the name when an action holds the right), Show or Hide control and its five states, opening in place at once with no motion, taking over `CollapsedSection.tsx`'s look and keeping its behavior; `FootStrip` (a line that holds a checkable number is 24 px tall); and `StageLabel`. Space falls only between shown blocks, so a hidden block leaves no gap. Add `/gallery/zones`, which shows a numbered sequence with a panel, three rows, a stage label and an opened row, an unnumbered page with a panel and an action row, a row with an action and its tag under its name, a zone whose first block failed (its error alert under the header, its second block intact), a side panel in both forms, and a page head with and without its facts line, each at its worst-case string (the 257-character description and the 35-character reference from plan 7.10). No page moves onto these parts here.

Read first: the plan's sections 7.1, 7.4, 7.6, 7.10, 8.3 and 8.5; block 5 of `design-md.md`; the prototype's package page at 1440, 1280, 1024 and 390 px with the Data switch on Real, Longest and Error (open zone 2, then open the drawer from a dot), and Home's Start here at 1440 px; `web/src/components/CollapsedSection.tsx`, `PageHeader.tsx`, `Breadcrumb.tsx`; `web/src/gallery/Gallery.tsx` and `pages.tsx`; `web/tests/gallery-components.spec.ts`, `gallery-a11y.spec.ts`.

**Blocked by:** 94 (The page frame: window margins, the wide layout, and a drawer that never moves the page)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] On `/gallery/zones` a zone with evidence is a white panel with 8 px corners and a foot strip, and a closed, sentence-only or empty zone is a row on `page` with a 1 px `line` under it; a row's number and name sit on the same x as a panel's at 1440 and 390 px, and opening a row makes it a panel in place with focus kept on its button, `aria-expanded` set and no transition measured.
- [ ] In the workspace sample the work spans columns 1 to 7 and keeps its place and width when the drawer opens, the drawer spans from the work's end plus a gutter to the window's edge within 384 to 600 px, and the side panel hides, at 1440 px open and 1280 px as a rail; at 1200 px open and 1024 px as a rail the sample is one column with its facts line.
- [ ] With the 257-character description as the h1 and the 35-character reference as the ID line, the sample's first zone starts inside the first screen at 390 by 844, nothing scrolls sideways at 320 px, and no part of the reference breaks inside itself.
- [ ] A row with an action has its tag under its name at 1440 and 390 px, a foot strip line that holds a checkable number is 24 px tall, and a zone whose first block failed shows the error alert under its header with its second block intact.
- [ ] axe finds no WCAG 2.2 AA violation on `/gallery/zones` at 1440 and 390 px, a row's Show button's focus ring never crosses its summary, and every state (open, closed, loading, error, no content) is captured at 1440 and 390 px, and open and closed at 1024 px.

**Gate seconds added:** about +0.8 (+1.2 for the new gallery page's states and axe at two widths; -0.4 because `CollapsedSection`'s own gallery states become the Task zone's).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3, as the second half of round 1's frame ticket. Settles in part ticket 62's doubled class strings in Breadcrumb.tsx (line 71). Specs to update: gallery-components.spec.ts, gallery-a11y.spec.ts, capture.spec.ts; package-steps.spec.ts and criteria.spec.ts keep passing on the old look until the package ticket. Gallery states: the new `zones` page in each zone state and at its worst case, and `skeleton` with a loading zone.

- October 27, 2026, pm: routed from the reviews of tickets 91 and 94:
  - The frozen class list now holds only `src/components/CollapsedSection.tsx` (`uppercase`). When this ticket takes over that file's look, take it off `FROZEN_CLASS_USES` in `web/lint/rules.ts` and `SHELL_TICKET_FILES` in `web/tests/lint.spec.ts`, then delete the list, `unusedKeeps` and its check in `web/lint/run.ts`, and rewrite the frozen cases in the class-lint test, whose `find(...)!` lookups throw once the file leaves the list. (ticket 91, its done comment and `.notes/91-verify.md` decisions)
  - If the list stays for any reason, `unusedKeeps` sees only files the lint reads, so a deleted listed file leaves its entry with no failure; add the `existsSync` check that `.notes/91-review.md` gives. (ticket 91, `.notes/91-review.md` follow-up 1 and `.notes/91-verify.md` follow-up 5)
  - Once the list is gone, DESIGN.md section 3's sentence about the frozen list (line 164) goes, and "Uppercase appears only with `chart-label`, inside charts." becomes true; check both in the same change. (ticket 91, `.notes/91-review.md` follow-up 3)
  - The page head: 8 px from the breadcrumb to the h1 on every page, as DESIGN.md section 4 and the prototype give it; today the plan check and a draft show 32 px and the project page 16. (ticket 94, `.notes/94-critique.md`)
  - A draft's breadcrumb wraps in the 649 px column at 1440 and 1280 px, and its second line starts with a chevron; show the trail as the prototype does ("Drafts"), or collapse it to its back link when it would wrap. (ticket 94, `.notes/94-critique.md`)

---
