# 105: The check window and the drawer's motion

**What to build:** Paste block 13b of `design-md.md`. (1) **The check line's window**: after the check line, a flush text button "How was that checked?" opens a non-modal window titled "How I checked this answer" or "How I checked this draft". When the verifier removed a sentence, it opens on "These counts include the two sentences I removed. The check line counts only the sentences I kept." (`checkLine.howScope`), because the window counts every sentence written and the line only those on screen; then the verifier's done line, the six checks as an ordered list in the steps' own words (a draft's step 2 says "came back for this draft"), "A number passes only when a record holds it at the same rounding." and the Answer ID or "Draft ID {id}, run {run}" in mono, breaking anywhere; the check line and the removed box share one `surface-2` block. (2) **The evidence drawer**: it enters with opacity and 12 px from the right over 160 ms, closes at once, lands on the clicked row of a list view with `tint`, and keeps the opener's current mark; its placement follows the user's call in `open.md` item 3 (beside, as today, unless the user chooses over, which then takes a `line-strong` left edge with the popover shadow). New copy keys: `checkLine.how`, `checkLine.howTitle`, `checkLine.howTitleDraft`, `checkLine.howScope`, `checkLine.rounding`, `checkLine.runId`, `checkLine.draftId`, `steps.check.six.sourcesDraft`.

Read first: Home with an answer open and "How was that checked?" pressed, and a draft with "How was that checked?" pressed (`?page=draft&how=1`); the plan's sections 9 (pattern 3) and 10; block 13b of `design-md.md`; `web/src/components/Checks.tsx`, `AnswerPanel.tsx`, `Answer.tsx`, `EvidenceDrawer.tsx`; `web/src/copy.ts` lines 785 to 856 (`steps.check`); `tests/fixtures/api/drafts-review-notes-partial.json` (`checks.shown` and `checks.checked`); `../fairshare/web/src/components/Answer.tsx` lines 94 to 119 (read only).

**Blocked by:** 103 (Drafts and a draft's page: three groups, the state in one place, and who checked it); 97 (How Strata works leaves Data: each refusal gives its reason, and one window lists them all)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] Under the answer of `ask-ke-nwwda-541055-past-range.sse`, "How was that checked?" opens "How I checked this answer" with the six checks in the steps' words and the Answer ID, and no scope sentence, since nothing was removed; focus moves to its heading, and Escape returns focus to the button (`checks.spec.ts`).
- [ ] On `drafts-review-notes-partial.json` the window is "How I checked this draft", opens on the scope sentence, says "9 of 11 numbers and dates" and "came back for this draft", and ends with "Draft ID draft-0002, run run-0002"; the check line above it still says "5 of 5 numbers match records; 4 of 4 dates match records." (`drafts.spec.ts`).
- [ ] The drawer enters over 160 ms from the right and closes at once, returns focus to its opener, keeps the opener's current mark, and on a list view lands on the clicked row with `tint`; under reduced motion no window or drawer transition is measured; axe finds no new violation with a window and the drawer open at 1440 and 390 px.

**Gate seconds added:** about +0.4 (the draft's window and the drawer's motion, at two widths).

## Comments

- October 27, 2026, design-lead: the second half of round 3's citation chain ticket, split after the second critic's review. The critic found the first prototype's draft window saying "9 of 11" and "3 of 3 sources ... for this question" under a check line that said "5 of 5" and a Sources list of two; both counts are the verifier's, so the window now says which scope it counts. Settles in full ticket 59's Term and Num spacing in "In short" (line 25), the drawer stopping with a tab under its header (line 27) and the answer ID breaking after "run-" (line 30). Specs to update: checks.spec.ts, answer.spec.ts, drafts.spec.ts, gallery-components.spec.ts, capture.spec.ts. Gallery states: `checks--how-window`, `checks--how-window-draft` and `evidence--landed-row` at 1440 and 390 px. Last wave: it edits Checks and AnswerPanel, which the Drafts and refusal tickets restyle.
