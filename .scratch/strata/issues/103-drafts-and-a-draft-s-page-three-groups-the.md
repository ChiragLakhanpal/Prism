# 103: Drafts and a draft's page: three groups, the state in one place, and who checked it

**What to build:** Paste block 11 of `design-md.md`. The Drafts list is one panel with three groups, To check, Checked and Exported, each an `h2` with its count line and its rows (the title as a link, the project and the drafted, checked or exported line, the notes and opened count), discarded drafts folded under them; with no drafts, a Task zone row with "You have no drafts to check." and "Go to Packages"; a failed load, the error alert in the panel's place. A draft's page uses the workspace layout, as the prototype draws it from `drafts-review-notes-partial.json`: the lede as the page's finding in the `finding` style, the method sentence, the check line and the removed box in one `surface-2` block, the notes table (cards below 560 px of column, with no panel name that repeats the h1), the sources, and the draft bar held to the work's columns. The side panel "State of this draft" holds the state stepper, what the draft was made from and when it was drafted; below the workspace threshold the stepper takes one line in the head under the subtitle and the rest follows the draft. After "Mark as checked" the bar's hold line gives way to "Checked by you on {date}." (by role, `draft.tab.checkedYou`), Export to Word becomes primary and takes focus, the side panel adds the same line, and a polite status says what changed; nothing fades (fairshare's decision bar, plan 9 pattern 9). A draft that fails to load is the error alert in the alert slot, with "Drafts" as the h1 and no scope chip.

Read first: the prototype's Drafts and a draft at 1440, 1024 and 390 px, the Drafts list with the Data switch on Empty and Error, the draft with "Mark as checked" pressed and with Error; the plan's sections 7.8, 8.0 (Drafts, a draft's page) and 9; block 11 of `design-md.md`; DESIGN.md's Draft bar, State stepper and Access label rows; `web/src/pages/DraftsPage.tsx`, `DraftPage.tsx`, `DraftNewPage.tsx`; `web/src/components/DraftBar.tsx`, `StateStepper.tsx`, `AccessLabel.tsx`; `web/tests/drafts.spec.ts`; `../fairshare/web/src/components/Document.tsx` lines 292 to 307 (read only).

**Blocked by:** 98 (Home: the briefing leads, Worth knowing in a panel, Waiting for you beside it)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The Drafts list shows To check, Checked and Exported as three groups in one panel with their count lines, discarded drafts folded, and, with no drafts, one row with its sentence and "Go to Packages" (`drafts.spec.ts`).
- [ ] A draft's page keeps its state stepper, origin and dates in the side panel at 1440 and 1280 px, and the stepper on one line in the head at 1024 and 390 px, where the lede's top is inside the first screen at 390 by 844.
- [ ] After "Mark as checked" the bar reads "Checked by you on {date}.", Export to Word is the primary button and has focus, the stepper's current step is "Checked by you", and a polite status announces the change; Export to Word still sends nothing (`drafts.spec.ts`, `ppsd.spec.ts`).
- [ ] The draft bar sticks to the bottom held to the work's columns with `env(safe-area-inset-bottom)` padding, Tab through it never leaves focus under it, and opening a source from a note leaves the document column's left edge and width unchanged at 1440 and 1280 px.

**Gate seconds added:** about +0.3 (`draft--checked` at two widths).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. Settles in full ticket 59's draft header state with no fixed place (line 87). Ticket 59's draft frame probe and skeleton items (lines 85 and 86) stay with 59. Specs to update: drafts.spec.ts, ppsd.spec.ts, capture.spec.ts (and uploads.spec.ts where it opens a draft). Gallery states: captures for the Drafts list (empty, grouped and error) and a draft in each state at three widths, with a new `draft--checked`. Second wave: it waits for the Home ticket because Home's Waiting for you lists the same drafts from the same copy block.

- October 27, 2026, pm: routed from the reviews of ticket 93:
  - On a draft page at 1440 by 640 the bar (56 px), the draft header (157 px) and the draft bar (141 px) leave the notes 286 px; stick the header only from 50rem of window height with a `head-sticks` variant in `app.css`, and check in `drafts.spec.ts` that it is static at 1440 by 640 and sticks at 56 px at 1440 by 900. The note names ticket 102 for this; Drafts is this ticket. (ticket 93, `.notes/93-design.md` follow-up 6)

---
