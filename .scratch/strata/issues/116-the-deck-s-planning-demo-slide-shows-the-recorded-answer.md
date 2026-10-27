# 116: The deck's planning demo slide shows the recorded answer on one press, as the backup for the live App

**What to build:** On the deck's planning demo slide (the slide that opens the package KE-NWWDA-541055-CW-RFB in the App), a button "Show the recorded answer" that draws the demo package's recorded past range with the app's own RangeFigure, from the recorded answers that ticket 47's step 2 writes into web/public/deck/data.json (the recording of docs/proposal/demo-package.json made on the paid workspace by `ops/proposal/record_demo_live.py`), with the recording's date and the same check line and source line the app shows. The button appears only when the deck data holds the recorded answers; without them the slide is as it is today. No number is typed into a slide: every figure comes from the data file, and the number check (docs/proposal/number_check.toml) passes with no new allow entry. The reason, from the user on October 27, 2026: the demo is live on the deployed App, which the platform stopped twice that day, so the slide needs a one-press fallback that shows the same answer. Built by the deck session on a new branch from build/strata in its worktree after ticket 106 merges, with the gate in a window the orchestrator gives, then this ticket's review and merge; the time box is 02:00 Pacific on October 28, 2026, after which the ticket is dropped and the final redeploy goes without it.

Read first: `web/src/deck/` (the second draft's slides and the demo slides, after ticket 106), `web/src/components/RangeFigure.tsx` or the figure the package page draws the past range with, `src/strata/proposal/deck.py` (what the data file holds; the recorded answers' shape), `ops/proposal/record_demo_live.py`, `docs/proposal/number_check.toml`, `web/tests/deck.spec.ts`, `web/src/copy.ts`.

**Blocked by:** 106 (The deck's second draft at /present lands: a topic tracker, a press per point, navy openers and redrawn figures)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] With the recorded answers in the deck data, the planning demo slide shows "Show the recorded answer", and one press draws the recorded past range with the app's RangeFigure, the recording's date, the check line and the source line; the numbers equal the recording file's (a screen test on a fixture data file).
- [ ] Without the recorded answers, the button is absent and the slide is unchanged (a screen test).
- [ ] The number check passes with no new allow entry, the copy is in web/src/copy.ts at a 10th-grade level, and the gate adds at most one second.
- [ ] The design critic finds the slide consistent with the deck's second draft (the tracker, the footer, the navy openers) at 1440 and 390 px.

## Comments

- October 27, 2026, orchestrator: opened at 14:59 PDT on the orchestrator's judgment after the user's rule of the same hour ("if you think things will be ready then we don't need the button, and vice versa"): a cheap fallback on the slide against the one failure the night cannot prevent. Time-boxed to 02:00 Pacific on October 28.
