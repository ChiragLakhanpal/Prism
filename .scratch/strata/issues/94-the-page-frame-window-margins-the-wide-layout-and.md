# 94: The page frame: window margins, the wide layout, and a drawer that never moves the page

**What to build:** Paste block 4 of `design-md.md`. Margins follow the window (16, 32, 40 px), never the page area. Add a size container `frame` (the window minus the sidebar), which the drawer does not change; the Frame sets `--frame-inline` from it, and the Document column is measured on it instead of `--window-inline`. On a wide page the drawer is `clamp(384px, 40vw, 560px)` and the page narrows with its left edge fixed; a page head that sets its title beside its actions does so by the page area (from 46rem), so a narrowed page stacks them. The drawer's head becomes the title and one caption sentence, with no eyebrow or middle dots (today's strings in the new places; the words are ticket 58's). The frame owns the sticky parts: `frame-top`, one scroll-padding hook for the bar and a sticky head, and `main`'s minimum height. The answer panel moves to the top of the page column under the bar, "In short" in `label` and its sentences in `lead`. The page's alert slot sits above the head; when a page's one request fails, it holds the error alert with "Try again" and the h1 names the page (plan 8.5). Pages keep their content; the workspace ticket and the tab tickets move them.

Read first: the plan's sections 7.5, 8.3 and 8.5; block 4 of `design-md.md`; the prototype's plan check at 1440 and 1024 px with a row's records open, and with the Data switch on Error; `web/src/components/Frame.tsx`, `EvidenceDrawer.tsx` (lines 2 to 4 and 665 to 677), `EvidenceCard.tsx`, `AnswerPanel.tsx`; `web/src/lib/useScrollPadding.ts` and DraftPage's own padding hook; `web/src/styles/app.css` lines 120 to 160; `web/tests/check-plan.spec.ts`, `drafts.spec.ts`, `answer.spec.ts`.

**Blocked by:** 93 (The top bar holds the box, and the stamp moves to the sidebar)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] Opening the drawer never moves a page's left edge: a test opens it on the project Summary, the plan check and a draft at 1440 and 1024 px and finds the h1's left edge unchanged to the pixel.
- [ ] A draft's document column keeps its place and width when the drawer opens at 1440 and 1280 px, measured against the frame, and `--window-inline` is gone from app.css (`drafts.spec.ts`).
- [ ] One hook in the frame sets the scroll padding for the bar and any sticky head, DraftPage's own hook and `useScrollPadding` are gone, and tabbing through the plan check and a draft never leaves the focused element under the bar or the head (`box.spec.ts`, `drafts.spec.ts`).
- [ ] No short state (not found, error, empty, no access) on All projects, the package page, Lessons, Passage reports or the review page pulls the footer into the first screen at 1440, 1024 or 390 px (`routes.spec.ts`).
- [ ] The drawer's head shows no eyebrow or middle dot on any of its views in the gallery's evidence page, and the answer panel sits at the top of the page column with "In short" in `label` (`answer.spec.ts`, and `check-plan.spec.ts`'s beside-the-drawer test at the new widths).

**Gate seconds added:** about +0.6 (the left-edge test at two widths and the short-state footer test; the two padding hooks' own tests merge into one).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. Its criteria test only pages that exist when it runs. Settles in full ticket 59's page column moving when the drawer opens (line 44) and short states pulling the footer up (line 50), and ticket 62's sticky padding rule in two hooks (line 71); in part ticket 58's drawer eyebrows and middle dots, whose words 58 writes. Specs to update: answer.spec.ts, check-plan.spec.ts, drafts.spec.ts, box.spec.ts, routes.spec.ts (and timeline-layout.spec.ts and gallery-components.spec.ts where they measure the column). Gallery states: the `evidence`, `answer-panel` and `document` pages at three widths; captures `answer--*` and `document--focus-pdf-link`.

---
