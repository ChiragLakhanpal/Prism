# 98: Home: the briefing leads, Worth knowing in a panel, Waiting for you beside it

**What to build:** Paste block 6 of `design-md.md`. Move Home onto the workspace layout, as the prototype draws it from `tests/fixtures/api/home.json`. The h1 is the date line in `label` and the briefing's sentences in the `finding` style, each count word still opening its window; the first-run and quiet sentences, which report a state, take `lead`. The Start here strip becomes a Task zone row under the briefing (its six links, their order and Remove unchanged; Remove at the row's right; "Examples Strata set up for you" as its tag, under the name at every width). Worth knowing is a panel in columns 1 to 7 named "Worth knowing" with the tag "Fixed checks, no model" (split from today's middle-dot string; new keys `home.worth.title` and `home.worth.tag`, words ticket 58's), each line a badge, its one verb at the first row's right, its sentence and its marker, then the foot strip's source. Waiting for you is the side panel from a frame of 75rem; below it the panels stack, Worth knowing first. When an answer opens on Home, the briefing folds to the date line and its first sentence in `body` with a flush ghost "Show the briefing" (`aria-expanded`; new keys `home.briefingShow` and `home.briefingHide`), and the answer panel takes columns 1 to 7 above the head (fairshare's strip, plan 9 pattern 6). The officer's view (`home-preview-piu.json`) keeps the same shape with its own briefing, no Start here, and Waiting for you as a row; the public view (`home-preview-public.json`) has "Home" as its h1, its sentence in `lead`, and "Closed projects" with the tag "Contracts traced from public records" (new keys `home.publicView.title` and `home.publicView.tag`), with no side panel. A failed load is the error alert in the alert slot with "Home" as the h1.

Read first: the prototype's Home at 1440, 1024 and 390 px with the Data switch on Real, Empty and Error, with the View switch on Agency officer and Public, and with "Show an answer asked from Home"; the plan's sections 7.7, 8.0 (Home), 8.4 (Home) and 9; block 6 of `design-md.md`; `web/src/pages/HomePage.tsx`; `web/src/copy.ts` lines 8443 to 8640 (`home`); `config/roles.toml` line 242; `web/tests/home.spec.ts`; `web/tests/mocked.ts` lines 88 to 99; `web/capture/shots.ts` lines 226 to 236; `../fairshare/web/src/components/SummaryStrip.tsx` (read only).

**Blocked by:** 95 (The workspace layout and the task zone parts); 91 (The class sweep: every page's classes move to their roles)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] Home's h1 is the date line in `label` and the briefing's sentences in the `finding` style, inside the first screen at 390 by 844 and 1024 by 768, each count word still opens its window, and the first-run sentences render in `lead` (`web/tests/home.spec.ts`).
- [ ] Worth knowing is a panel named "Worth knowing" with the tag "Fixed checks, no model" and no middle dot, each line with one verb at its first row's right and its marker at its end; Start here's tag sits under its name at 1440 and 390 px; Waiting for you is the side panel from a frame of 75rem and follows Worth knowing below it, and the Tab order is the same at 1440, 1280, 1024 and 390 px.
- [ ] With an answer open on Home the briefing shows only its date line and first sentence, "Show the briefing" unfolds the rest in place with `aria-expanded`, and closing the answer unfolds it (`home.spec.ts` with a recorded answer stream).
- [ ] In the officer's preview Home shows the team's plan sentence, its two lines and no Start here; in the public preview it shows "Home", one `lead` sentence and "Closed projects" with no middle dot and no side panel (`home.spec.ts` with `home-preview-piu.json` and `home-preview-public.json`).
- [ ] The Start here strip is a Task zone row, only for World Bank staff in their own view today; Remove, the undo row and "Show the examples again" work as before, and Home still renders from one GET /api/home of at most 15 KB within DESIGN.md section 10's 3G budgets.

**Gate seconds added:** about +0.5 (`home--answered` at two widths and the two preview checks, each one page load).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. The prototype draws Home from the tests' own recordings, since the local app answered GET /api/home with 404. Settles in part ticket 58's middle-dot titles (the shape here, the words with 58). Specs to update: home.spec.ts, mocked.ts's staff recording, capture.spec.ts. Gallery states: `home--populated`, `home--first-run`, `home--quiet-week` at three widths, and new `home--answered`, `home--officer` and `home--public` at 1440 and 390 px. First wave of the page tickets.

---
