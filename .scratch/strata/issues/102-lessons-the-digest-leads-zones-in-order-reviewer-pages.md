# 102: Lessons: the digest leads, zones in order, reviewer pages in the sidebar

**What to build:** Paste block 10 of `design-md.md`. The digest sentence becomes the page's finding in the `finding` style, with its count words still opening what they count, followed by its caption and the sources note; on a first visit its status sentence takes `lead`. Then the zones in order: "Changed where you used it", "New", "Your reports", "The library" (with its filters), each a panel when it holds lessons or reports and a row when it holds only its sentence; the library's empty row no longer repeats the finding. The reviewer pages (Waiting for review, Passage reports, Judging) become sidebar items under Lessons, with their counts in a badge hidden at zero, for the roles that have them, and the sub-tab row in `LessonsPages.tsx` goes. A review page uses the workspace layout, with its history list in the side panel where the page has one. A failed load is the error alert in the alert slot.

Read first: the prototype's Lessons at 1440, 1024 and 390 px, with the Data switch on Error; the plan's sections 8.0 (Lessons, a lesson's page) and 8.4; block 10 of `design-md.md`; `web/src/pages/LessonsTab.tsx`, `LessonsPages.tsx`, `ReviewPage.tsx`, `PassageReportsPages.tsx`, `JudgingPages.tsx`; `web/src/copy.ts` lines 5859 to 5900 and 6354 to 6431; `web/tests/lessons.spec.ts`, `lessons-page.spec.ts`.

**Blocked by:** 99 (Projects: sub-pages in the sidebar, a shorter project head, and Summary's finding first)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The digest sentence is the page's finding in the `finding` style with each count word still opening its items, the first-visit sentence renders in `lead`, and the zones follow as "Changed where you used it", "New", "Your reports" and "The library", each a panel or a row by what it holds (`lessons-page.spec.ts`).
- [ ] Waiting for review, Passage reports and Judging are sidebar items under Lessons with their counts in a badge hidden at zero, only for the roles that have them, and the sub-tab row is gone (`lessons.spec.ts`).
- [ ] A review page uses the workspace layout at 1440 and 1280 px and one column at 1024 and 390 px, and its decision form keeps its focus rules and its single-key shortcuts inside its own panel.
- [ ] lessons.spec.ts, lessons-page.spec.ts, retrieval-pages.spec.ts and feedback.spec.ts pass, and the capture has the Lessons, review and judging shots at 1440, 1024 and 390 px with no load error.

**Gate seconds added:** about 0 (the sub-tab tests become sidebar tests in place).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. Settles in full ticket 59's Lessons purpose above the sub-tab row (line 81) and ticket 60's shell captures with a load error on /lessons (line 72). Ticket 59's queue and review skeleton items (line 82) stay with 59. Specs to update: lessons.spec.ts, lessons-page.spec.ts, retrieval-pages.spec.ts, feedback.spec.ts, capture.spec.ts. Gallery states: captures for Lessons first visit, populated and error, a review page, Passage reports and Judging. Second wave: it waits for the Projects ticket because both fill the sidebar's sub-item slot.

---
