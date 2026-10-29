# 103: Drafts and a draft's page: three groups, the state in one place, and who checked it

**What to build:** Paste block 11 of `design-md.md`. The Drafts list is one panel with three groups, To check, Checked and Exported, each an `h2` with its count line and its rows (the title as a link, the project and the drafted, checked or exported line, the notes and opened count), discarded drafts folded under them; with no drafts, a Task zone row with "You have no drafts to check." and "Go to Packages"; a failed load, the error alert in the panel's place. A draft's page uses the workspace layout, as the prototype draws it from `drafts-review-notes-partial.json`: the lede as the page's finding in the `finding` style, the method sentence, the check line and the removed box in one `surface-2` block, the notes table (cards below 560 px of column, with no panel name that repeats the h1), the sources, and the draft bar held to the work's columns. The side panel "State of this draft" holds the state stepper, what the draft was made from and when it was drafted; below the workspace threshold the stepper takes one line in the head under the subtitle and the rest follows the draft. After "Mark as checked" the bar's hold line gives way to "Checked by you on {date}." (by role, `draft.tab.checkedYou`), Export to Word becomes primary and takes focus, the side panel adds the same line, and a polite status says what changed; nothing fades (fairshare's decision bar, plan 9 pattern 9). A draft that fails to load is the error alert in the alert slot, with "Drafts" as the h1 and no scope chip.

Read first: the prototype's Drafts and a draft at 1440, 1024 and 390 px, the Drafts list with the Data switch on Empty and Error, the draft with "Mark as checked" pressed and with Error; the plan's sections 7.8, 8.0 (Drafts, a draft's page) and 9; block 11 of `design-md.md`; DESIGN.md's Draft bar, State stepper and Access label rows; `web/src/pages/DraftsPage.tsx`, `DraftPage.tsx`, `DraftNewPage.tsx`; `web/src/components/DraftBar.tsx`, `StateStepper.tsx`, `AccessLabel.tsx`; `web/tests/drafts.spec.ts`; `../fairshare/web/src/components/Document.tsx` lines 292 to 307 (read only).

**Blocked by:** 98 (Home: the briefing leads, Worth knowing in a panel, Waiting for you beside it)

**Status:** done
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

- October 28, 2026, merger: merged strata/103-drafts-and-a-draft-s-page-three-groups-the-2 (head ef6be918: the work in d928503a and eb4e8067, then a merge of build/strata at d1f5efbd) into build/strata as merge commit 46db6b1b, with history, since the branch's commits hold no key-shaped line. The worktree that built it was `.claude/worktrees/wf_731410d9-1cd-2`; I remove it right after this commit and keep the branch. The merge changes 18 files (626 lines in, 271 out): `web/src/pages/DraftsPage.tsx` and `DraftPage.tsx`; the components `DraftBar`, `SidePanel` and `StateStepper`, with `SpaceLine` deleted (the side panel now holds columns 9 to 12, and DESIGN.md says so); `copy.ts`, `app.css`, the gallery (`copy.ts`, `drafts.tsx`), `web/capture/shots.ts` and `web/lint/rules.ts` (`layout` added to `NON_COPY_PROPS`); DESIGN.md (block 11); and 5 specs (`drafts`, `ppsd`, `capture`, `routes`, `space-line`). No dependency, SQL, Python or gate file changed, and the merge had no conflicts. I ran `scripts/install` before the commit, and it changed no tracked file.
  - The gate: I committed through the orchestrator's quiet-window script. Its first look, at 23:38 PDT, saw a load of 12 and waited. At 23:40 it saw a load of 5 and committed. The gate passed in 124.6 seconds and made 46db6b1b at 23:42. The fixture database was kept. The Python tests took 117.1 s and 119.9 s, Playwright 99.0 s and 103.4 s, and the secret scan 3.2 s. `git log --parents -1` shows the two parents d1f5efbd and ef6be918.
  - By hand on build/strata at 46db6b1b: the gate passed in 125.7 seconds, from 23:43:16 to 23:45:22 PDT, while the load rose from 22 to 29. The Python tests took 117.2 s and 121.0 s, Playwright 99.9 s and 102.8 s, and the secret scan 3.3 s. So the history scan has read the merged history, 24.3 seconds under the 150-second limit.
  - Notes that passed, at ef6be918:
    - The code review approved round 1 with nothing blocking and four follow-ups (`.notes/103-review.md`; the follow-ups are listed for the pm below).
    - The design lead passed it with polish and nothing blocking (`.notes/103-design.md`). axe found no WCAG 2.2 AA violation on 7 states at 3 widths.
    - The design critic did not block, and the lowest score was 4 (`.notes/103-critique.md`).
  - Verify (`.notes/103-verify.md`): pass on all four criteria and on the routed head-sticks comment, with nothing parked. The worktree's gate passed in 125.2 seconds. The ticket's spec files gave 100 passed in 13.3 s on four workers, and the ticket's own new and changed tests take about 5.4 s.
    - Criterion 1: one panel, "Your team's drafts", holds the h2s To check, Checked and Exported, each with the count line "One draft.", which matches the server's `counts` (1, 1 and 1). The count lines follow the server, not the rows: with `counts.to_check = 3` the line read "Three drafts, newest first.". The discarded fold sits inside the panel. With no drafts, one Task zone row holds its sentence and one link, "Go to Packages", to `/packages`. A failed load puts the alert in the panel's place under the h1 "Drafts".
    - Criterion 2: the side panel sits at x 989 at 1440 and x 883 at 1280, level with the column at y 96. At 1024 and 390 the stepper takes one line under the subtitle. At 390 by 844 the lede's top is at y 273. Every kind of draft's Made from, Drafted and Checked lines matched its record.
    - Criterion 3: after Mark as checked, the bar read "Checked by you on October 23, 2026." (the server's `checked.at`, 2026-10-23T14:02:00Z) in weight 600. Export to Word was the only primary button and had focus, the current step was "Checked by you", and a `role="status"` read "You marked these notes as checked. You can export them now.". There were no opacity transitions, and the check POST was the only POST. Export sent only `POST /api/drafts/draft-0001/export` to Strata's own server, and no request left the origin. PPSD rows with an owner still to set keep Export held: a click, Enter and Space sent no POST. A refused check (a 503) kept the step at Draft and showed the alert.
    - Criterion 4: the bar matched the column (x 104, width 742.66 at 1440 and 649.33 at 1280) and is sticky at bottom 0. With a 34 px safe-area inset, its bottom padding became 46 px (12 + 34). 140 Tabs and 140 Shift+Tabs at 1440 and 1280 never left focus under a sticky part. Opening a source from a note left the column's x, width and y unchanged at 1440 and 1280.
    - Routed head-sticks: the header is static at 1440 by 640 and sticks at 56 px at 1440 by 900.
    - Numbers checked against their source rows: the removed 300,000.00 is not in KE-NWWDA-541062-CW-RFQ's plan rows (280,000.00 in document 40090127 and 295,000.00 in 40132287), so removing it was right. The list's counts and note counts match `drafts-list.json`. Every date in the side panel and the decided line matches its record's `created_at` or `checked.at`. The refusal and benchmark tests passed (47).
  - Workspace results: none run and none parked. The builder named no workspace step, and the verifier parked none, since the ticket changes only the web app and every criterion ran offline on the recorded answers. Every key is set (`guard.py --env-keys`), but mergers run no workspace step. The next App redeploy from a snapshot at or after 46db6b1b carries this ticket; the orchestrator or the second session runs it.
  - Deferred to the design pass:
    - Captures: the new `draft--marked-checked` captures at 1024 and 390 px, and the gallery's `stepColumn` state. The verifier took captures at the widths the criteria name.
    - The check line and the removed box as one `surface-2` block. Ticket 105 owns it (critique 2, design O5). When 105 lands, check the draft page at 1440 and 390: one block, a hairline between the check line and the removed box, and no left border.
    - The design review's follow-ups F1 to F6 (`.notes/103-design.md`):
      1. The breadcrumb ends with the current page, and at 1280 that crumb wraps to a line of its own.
      2. The side panel's stepper repeats the panel's name for screen readers.
      3. Dates break inside "October 23, / 2026." at 390 px.
      4. The lede wraps unevenly; give it `text-balance`.
      5. The planned dates "Made from" reads as if the dates were uploaded.
      6. The discarded fold's "Show it" sits too close to its sentence and has no chevron.
    - The critique's follow-ups 1 to 6 (`.notes/103-critique.md`):
      1. The breadcrumb keeps parents only (the top change): `DraftCrumbs` and `PackageCrumbs` pass `trail={[drafts]}`.
      2. The one `surface-2` block (ticket 105).
      3. A note in the first screen at 1440 by 900: move "Show the four steps I took" after the notes, and put "Showing all 3 activities with a signal" inside the notes panel.
      4. The discarded fold's chevron.
      5. The side panel's Checked label repeats over "Checked by you on ...".
      6. A failed draft should move focus to its h1 "Drafts"; today focus stays on `body`.
    - Seen here but owned elsewhere (design O1 to O4): ticket 113's floating box covers the notes' first row at 1440 by 900; LoadError puts Try again outside the alert; the PPSD subtitle breaks inside the STEP reference; a planned dates draft scrolls 14 px sideways at 390 px. That last one already happens on build/strata at d1f5efbd and fails WCAG 1.4.10, so it should be its own ticket.
  - For the pm (from `.notes/103-review.md`):
    1. A false claim, so function rather than polish: the planned dates "Made from" says "uploaded" for a draft made from a published plan (`web/src/pages/DraftPage.tsx:261`, `web/src/copy.ts:3156`). `src/strata/drafts/step_rows.py` accepts a `plan:` source, so a direct API call gets "The dates in your plan uploaded October 9, 2026". No screen starts such a draft today (`startDates` sends only `upload:`). The fix: `source?: "upload" | "plan"` on `DraftSubject`, a `madeFromPlan` template under `copy.draft.kinds.step_rows`, and a `TextLink` to the plan check. It should land before any screen offers planned dates from a published plan.
    2. Two sentences about the sticky header read backwards (`DESIGN.md:243` and the comment above `DraftHeader` in `DraftPage.tsx`).
    3. The side panel's stepper names itself twice (`StateStepper.tsx:36`): an optional `labelled` prop, the same item as design F2.
    4. The address of the page a draft was made from is built in two places: one `madeFromHref(draft)` helper in `DraftPage.tsx`.
  - Decisions parked for the user: none. The task named none from the builder, and the review, design review, critique and verify notes each park none.
  - Coordination: ListAgents showed no session named strata-58 (only strata-e1 and 03-projects-b9), so I sent no index-busy or index-free message. The main checkout was clean before the merge.
  - Unblocks: ticket 105 (the check window and the drawer's motion), whose other blocker, 97, is done. I left its Status at `ready`, since it is not one of this wave's tickets (80, 81, 86, 87, 88); the orchestrator dispatches it.

---
- October 28, 2026, orchestrator (01:50 PDT): the App redeploy ran from d4ac8473 (the catch-up block "Tickets 102, 103 and 105, the App redeploy ran"); the page's check by eye is the owner's.
