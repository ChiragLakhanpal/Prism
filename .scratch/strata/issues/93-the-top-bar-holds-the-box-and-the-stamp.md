# 93: The top bar holds the box, and the stamp moves to the sidebar

**What to build:** Paste block 3 of `design-md.md`. Merge the white band into the navy bar. From 1024 px one 56 px row that sticks: the logo (same file, hash and size), the wordmark, the one box from the page's content edge (or 32 px after the wordmark with the rail) up to 640 px wide on `surface` with 4 px corners and `focus-on-dark` around it, and the view switch 24 px from the right edge as a 32 px control with 4 px corners. The box keeps one row; its scope chip drops "Within" below a box width of 35rem. Below 1024 px the bar does not stick and the box takes its own row; with a chip the box's search icon hides, so the chip and the text each take a row; below 360 px the icon always hides; below 768 px the view switch moves to the Menu sheet's foot, the "/" hint hides, and the placeholder takes its short form, "Open a project or package, or ask" (new key `box.placeholderShort`), while the field's name keeps the whole sentence. The data stamp moves to the sidebar's foot under Data, to the Data item's tooltip in the rail, and to the Menu sheet's foot, in a 24 px line box. The skip link shows below the bar, over the page. Repaint `web/index.html`'s bar to match. The view switch's popover keeps ticket 40's rows, past-date field and language choice; the prototype draws its rows and date field (`?view-open=1`).

Read first: the plan's sections 7.2, 8.2 and 7.10 (the box's worst case); block 3 of `design-md.md`; the prototype at 1440, 1024 and 390 px, at 390 px with the Data switch on Longest (a 35-character reference in the chip), and with the view switch's popover open; `web/src/components/BoxBand.tsx`, `IntentBox.tsx`, `TopNav.tsx`, `SkipLink.tsx`; `web/index.html`; `web/tests/shell.spec.ts` lines 23 to 83, `gallery-frame.spec.ts`, `box.spec.ts`.

**Blocked by:** 92 (The sidebar and the rail replace the tabs in the bar)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] From 1024 px the bar is one 56 px navy row that sticks: the logo (same hash, 120 by 24), the box from x = 264 at 1440 px with the sidebar open and x = 244 at 1280 px with the rail, at most 640 px wide, and the view switch ending 24 px from the right edge; no band sits under it (`shell.spec.ts` at 1440, 1280 and 1024 px).
- [ ] On `/packages/KE-NWWDA-541055-CW-RFB` the box keeps one row from 1024 px with the chip's reference and "Ask about this package" uncut, every view switch label fits beside it at 1024 px with WCAG 1.4.12 text spacing, and no route scrolls sideways (`gallery-frame.spec.ts`).
- [ ] Below 1024 px the box has its own row; at 390 and 320 px the placeholder's measured width is less than the field's on Home and on a package page, and a chip with the reference "KE-UASIN GISHU COUNTY-571338-CW-RFB" takes its own row with the text under it (`box.spec.ts`).
- [ ] The stamp shows its five states at the sidebar's foot with its link to the Data page, and its words in the Data item's tooltip as a rail; `web/index.html` paints the new bar, `shell.spec.ts`'s first-paint test still matches at 1440, 1280, 800 and 390 px, and the focused skip link covers neither the logo nor the wordmark.

**Gate seconds added:** about +0.2 (one new test, the long chip at 390 px; the band's own tests are rewritten in place).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. The prototype measured the default placeholder at 333 px against a 318 px field at 390 px, so round 2's claim that it fit was wrong; the short form measures 250 px. Settles in full ticket 60's 37 px sideways scroll at 1024 px with text spacing and the wordmark touching Menu at 320 px (line 47), and the skip link covering the logo (line 46); in part ticket 58's plan-mode placeholder cut at 390 px (line 83), since plan mode's own placeholder may still need a short form that 58 writes, and ticket 58's two dates on one screen (line 72). Specs to update: shell.spec.ts, gallery-frame.spec.ts, box.spec.ts, views.spec.ts, capture.spec.ts. Gallery states: `navigation--focus-box`, `--hover-box`, `--focus-stamp`, `--hover-stamp`, `--hover-pill`, `--focus-pill`, `--view-open`, `--320` at three widths, and a new `navigation--long-chip` at 390 px.
- The deck's navy slides: the deck ticket (`../deck-ticket.md`) says whichever of the deck branch and "the redesign's tokens ticket" merges second adds the clause about the deck's navy slides to DESIGN.md's navy rule. In this wave the navy rule's text lands here (block 3) and in the frame ticket's principle 2 (block 4), not in the tokens ticket, so these two tickets carry the clause if the deck has merged and the user kept the navy slides (`design-md.md`, the notes under both).

---
