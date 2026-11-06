# Ticket drafts for the shell redesign, in build order

Sixteen drafts in the form of `.scratch/strata/issues/NN-*.md`, round 3, finished after the second critic's review (`../critique/round3.md`). Each number is "XX" until the orchestrator files it, and a `Blocked by` line names an earlier draft by its title. The order is the one asked for, with three splits the second critic asked for so that every ticket fits a night: the tokens first, now in two tickets (tokens, fonts and lint, which can start now; the class sweep, after the functional tickets merge); then the shell in four tickets (the sidebar and the rail, the top bar, the page frame, the workspace parts); then one or two tickets per tab in the demo's order; and the citation chain in two tickets (the number tooltip with its gate test; the check window with the drawer's motion). The number tooltip and How Prism works leaving no longer wait for the page tickets: each edits files the shell does not, so they run beside it.

Each ticket pastes only its own block of `design-md.md` into DESIGN.md in the same change, so DESIGN.md always describes the app as it is. The prototype draws Home, Packages, the plan check, the package page, All projects, Lessons, Drafts and a draft's page, each in its real, longest, empty or few, and error states, and Home, All projects and the plan check in the officer's and the public views too. It does not draw a project's page or Data; those tickets start from the design lead's brief, `<NN>-brief.md`, which draws the page at 1440 and 390 px in the prototype's tokens before a builder begins.

The design sources every ticket reads, by absolute path (the orchestrator may copy them into the notes folder when it files the tickets):

- Plan: `<scratchpad>/redesign/design/plan.md`
- DESIGN.md text, by ticket: `<scratchpad>/redesign/design/design-md.md`
- Prototype: `<scratchpad>/redesign/design/prototype.html` (its CSS custom properties are the tokens; `?page=`, `?data=` and `?view=` pick a page, a data state and a view, and plan.md section 13 lists every state the address can set)

## Build order and gate time

The gate (CLAUDE.md rule 6) ran 121.9 to 145.4 seconds against its 150-second cap in wave 4q (`docs/STATUS.md` line 577), so this wave has about 4.6 seconds of room. "Gate seconds added" in each ticket is an estimate from the gate's own figures: its two Playwright lanes run about 716 tests in 53 to 68 seconds beside the other lanes, five workers each (`gates/steps.toml` lines 128 to 141), so a new screen test costs about 0.2 seconds of gate time, and one that loads three widths with axe about 0.6. Every new check opens a page once per width and state, as `gates/steps.toml` asks. Together the sixteen tickets add about 7.2 seconds and take back about 3.0, about 4.2 net. So the orchestrator times the gate after each merge, and a ticket whose gate passes 145 seconds waits for ticket 56's cuts, where the status file says cuts land.

| # | Ticket | Blocked by | Runs beside | Gate seconds |
|---|---|---|---|---|
| 1 | Tokens, fonts and lint | None (can start now; `open.md` item 6) | the functional tickets | +0.5 |
| 2 | The class sweep | 1, and every functional ticket merged | 3 to 6 | 0 |
| 3 | The sidebar and the rail | 1 | 2 | -0.4 |
| 4 | The top bar | 3 | 2, 7, 8 | +0.2 |
| 5 | The page frame | 4 | 7, 8 | +0.6 |
| 6 | The workspace parts | 5 | 7, 8 | +0.8 |
| 7 | The number tooltip, with its gate test | 2 | 4 to 6 | +0.8 |
| 8 | How Prism works leaves Data | 2 | 4 to 6 | -0.8 |
| 9 | Home | 6, 2 | 10, 11 | +0.5 |
| 10 | Projects | 6, 2 | 9, 11 | +0.3 |
| 11 | Packages and the plan check | 6, 2 | 9, 10 | +0.5 |
| 12 | The package workspace | 11, 7 | 13, 14, 15 | +0.2 |
| 13 | Lessons | 10 | 12, 14, 15 | 0 |
| 14 | Drafts | 9 | 12, 13, 15 | +0.3 |
| 15 | Data readiness by the page area | 10, 8 | 12, 13, 14 | +0.3 |
| 16 | The check window and the drawer's motion | 14, 8 | 12, 13, 15 | +0.4 |

The longest chain is eight tickets: 1, 3, 4, 5, 6, 9, 14, 16. The shell must land in that order, because each of its tickets edits the same frame files (`TopNav.tsx`, `Frame.tsx`, `web/index.html`). Every ticket fits a night: the largest now name four or five specs, not seven to nine.

---

# XX: Tokens, fonts and lint for the redesigned shell

**What to build:** Paste block 1 of `design-md.md` into DESIGN.md, except the one sentence marked for the class sweep (section 2's contrast rows and the deck note, section 3, section 4's Space, Radius and Elevation rows, the new Motion subsection and Phone baseline row, section 5's Buttons and Cards bullets, section 10's motion bullet), and apply it to `web/src/styles/app.css`'s `@theme static` block. Type: the new scale (`finding` 28/36 light with -0.01em, `h1` 24/32 and 20/28 below 48rem, `h2` 18/600, `h3` 16/600, `lead`, `label` 13/600, `chart-label` 12/600 uppercase, `button` 600), Open Sans 300 self-hosted. `--text-title` stays as an alias with `h2`'s values, so every page that still uses it draws at the new size until the sweep. Shape: radius by role (4 for controls, 8 for containers, the pill for data), applied in the shared components only: `Button.tsx`, the inputs, selects, `ListSearch.tsx` and the Key hint take 4 px corners, while badges, markers and chips keep the pill. Motion: the two curves (`--ease-out` cubic-bezier(0.23, 1, 0.32, 1) and `--ease-drawer` cubic-bezier(0.32, 0.72, 0, 1)), the six `--motion-*` durations, `--tooltip-width`; app.css's `fade-in`, `menu-in`, `sheet-in` and `settle` keyframes (lines 96 to 120) become transitions with `@starting-style`; the default transition curve (line 93) becomes `ease` for color; primary and secondary buttons scale to 0.98 while pressed, with the transition set only on `:active` so the release snaps; every hover rule moves inside `@media (hover: hover) and (pointer: fine)`; reduced motion stays "none" (lines 296 to 303). Phone baseline: no tap flash, `touch-action: manipulation`, 16 px inputs, `100dvh` with a `100vh` fallback. Lint: the class lint's new rule allows `uppercase` only with `text-chart-label`, with two named exemptions in `web/lint/rules.ts`: `web/src/deck/` (the deck's branch, below) and a frozen list of the files that use `uppercase` today, which the class sweep empties; a new use anywhere else fails. **This ticket edits no page file** (nothing under `web/src/pages/`), so it can run while the functional tickets merge. **Nothing under `web/src/deck/` changes**: `--text-title` and `--radius-box` stay as deprecated aliases until the deck branch moves its last uses. No copy string, number, route or layout changes.

Read first: DESIGN.md sections 2 to 5 and 10; the plan's sections 5 and 6, 5.7 above all; `web/src/styles/app.css` (lines 88 to 120 and 280 to 303); `web/tests/tokens.spec.ts`; `web/lint/rules.ts` (the class lint's lists); `web/src/components/Button.tsx`, `StatusBadge.tsx`, `CitationMarker.tsx`, `Card.tsx`, `Popover.tsx`; the gallery pages `buttons`, `badges`, `cards`, `citations`, `table`; `<scratchpad>/redesign/emil-skills/emil-design-eng.SKILL.md` lines 62 to 145 and 234 to 345.

**Blocked by:** None (can start immediately; the user decides in `open.md` item 6 whether it starts before the functional tickets merge)

**Status:** ready
**Area:** design
**Phase:** P4
**Design review:** yes

- [ ] DESIGN.md carries block 1 of `design-md.md` but the sweep's sentence, and `web/tests/tokens.spec.ts` passes against it: the built app's `:root` has every new type, radius and motion token at its value, `--text-title` only with `h2`'s values, and `--radius-box` only as the alias.
- [ ] Open Sans 300 is self-hosted from `@fontsource/open-sans/300.css`, and `web/tests/fonts.spec.ts` proves text in the `finding` style renders in Open Sans at weight 300 with no request to a font host.
- [ ] Buttons, inputs, selects and key hints have 4 px corners, status badges, citation markers and chips keep the pill, and cards and popovers 8 px, on the gallery's buttons, badges, cards, citations and table pages at 1440, 1024 and 390 px; a pressed primary button measures `scale(0.98)`, a released one has no transform transition, and an emulated `prefers-reduced-motion: reduce` measures no transition (`web/tests/gallery-components.spec.ts`, `gallery-a11y.spec.ts`'s motion check).
- [ ] The class lint refuses `uppercase` without `text-chart-label` in a file on neither exemption list, and `web/tests/lint.spec.ts` proves the refusal and both exemptions; `git diff --stat` shows no file under `web/src/deck/` or `web/src/pages/`, and `web/tests/deck.spec.ts` and the four /present captures still pass.
- [ ] axe finds no new WCAG 2.2 AA violation on any gallery page at 1440 and 390 px, every target is at least 24 px and every button 44 px tall, and every focus ring is still 2 px at a 2 px offset (`web/tests/gallery-a11y.spec.ts`).

**Gate seconds added:** about +0.5 (one font test and two lint cases; the pressed-button and reduced-motion checks ride on gallery pages the specs already open).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3; split after the second critic's review so this half can start now and the class sweep, which edits page files, waits for the functional tickets. Settles in full ticket 59's three empty states in two body sizes (line 60); in part ticket 59's section name outranking the finding (line 61), which the package ticket finishes, and ticket 60's wrapped link's focus ring (line 45) if the global focus rule takes `box-decoration-break: clone`. Specs to update: tokens.spec.ts, fonts.spec.ts, lint.spec.ts, gallery-components.spec.ts, gallery-a11y.spec.ts. Gallery states and captures: the buttons, badges, cards, citations and table pages; `buttons--*`, `links--*`, `cards--*` at three widths, with a pressed button.
- The deck branch's follow-up, for the session that owns `deck/second-draft` (lines as of 494a176b), so the aliases and the deck exemption can go: `web/src/deck/ramp.ts` lines 38 to 49, the reading view's `PAGE` map: `head: "text-title"` (line 44) becomes `text-h2`, and the `text-h1` and `text-h2` roles (lines 39 to 42 and 46) now read 24/700 and 18/600, so the deck may map `title`, `figureTitle`, `topic` and `result` to `text-h1`; `label: "text-label"` (line 48) is now 13/600 in sentence case. `web/src/deck/Deck.tsx` lines 925 and 969, `text-title`, become `text-h2`; line 699, `text-h3` (now 16/600), may become `text-h2`. `web/src/deck/AwardChart.tsx` line 86, `uppercase` at 13 px inside the chart, takes `text-chart-label`. `web/src/deck/layouts.tsx` line 146, `rounded-box`, becomes `rounded-sm`; `Deck.tsx` lines 41 and 600 and `layouts.tsx` lines 158 and 186 use `rounded-pill` on controls, which the deck may move to 4 px to match the app's controls (open.md item 5). The second draft has no slide eyebrows, so round 2's Deck.tsx lines 204 and 440 are gone. When this lands, the two alias lines and the `web/src/deck/` exemption leave DESIGN.md, app.css and `web/lint/rules.ts` in the same change.

---

# XX: The class sweep: every page's classes move to their roles

**What to build:** After the functional tickets merge, move every use in the page files to its role so no page loses its hierarchy before its own ticket: `text-title` becomes `text-h2` (141 uses in 60 files), a `text-h3` that holds a finding becomes `text-lead`, `uppercase` leaves every class but `text-chart-label` (32 uses in 24 files), and a page's own `rounded-pill` on a control becomes `rounded-sm` while badges, markers and chips keep the pill. Empty the class lint's frozen list of files that used `uppercase` as each one is fixed, then delete the list. Paste the one sentence of block 1 marked for the class sweep. Leave the files the shell tickets rewrite (`TopNav.tsx`, `BoxBand.tsx`, `IntentBox.tsx`, `Frame.tsx`, `PageHeader.tsx`, `Breadcrumb.tsx`, `CollapsedSection.tsx`, `EvidenceDrawer.tsx`'s head) to those tickets, and leave `web/src/deck/` to its branch. No copy string, number, route or layout changes.

Read first: block 1 of `design-md.md`; the plan's section 5.3; `web/lint/rules.ts`; the class lint's report of today's uses; `web/tests/` specs that assert classes (grep for `text-title` and `uppercase`).

**Blocked by:** XX (Tokens, fonts and lint for the redesigned shell); and every functional ticket merged, as the user's rule of October 25, 2026 asks

**Status:** ready
**Area:** design
**Phase:** P4
**Design review:** yes

- [ ] No file outside `web/src/deck/` uses `text-title`, the frozen uppercase list is gone, and the class lint passes with only the deck exemption.
- [ ] Every page's finding sentence that used `text-h3` uses `text-lead` (or the `finding` style where its page ticket has landed), and no section name outranks its finding on the package page, the plan check and Data readiness at 1440 and 390 px.
- [ ] Every Playwright spec passes unchanged in count, the captures differ only in type size, case and corners, and `git diff --stat` shows no file under `web/src/deck/` and none of the shell tickets' files.

**Gate seconds added:** about 0 (no new test; it updates class assertions in place).

## Comments

- October 27, 2026, design-lead: the second half of the tokens ticket, split after the second critic's review because it edits the same page files the functional tickets edit tonight. Specs to update: the ones that assert `text-title` or `uppercase`. Captures: every page's, once, after the sweep.

---

# XX: The sidebar and the rail replace the tabs in the bar

**What to build:** Paste block 2 of `design-md.md`. From 1024 px a `nav` named "Main" beside the page on `page` grey with a hairline edge: Home, then the applied view's sections in `SECTIONS` order (Packages, Projects, Lessons, Drafts), and at its foot Data and "Collapse the sidebar". 224 px open from 1440 px and a 64 px rail of icons from 1024 to 1439 px; a person's choice is kept in local storage. The width changes at once, never animated. Rail items show their label in a tooltip on hover and keyboard focus. The current item is `matchRoute`'s section, with `aria-current="page"` on the section's page and `"true"` on a page inside it. Add a slot for a section's own pages under its item, shown only while it is current (the tab tickets fill it), and hide the sections and sub-items the applied view hides (`config/roles.toml` lines 182 to 191). Below 1024 px the same content is the Menu sheet, a modal dialog from the left that slides in over 200 ms on `ease-drawer` and out over 120 ms. Add an inline script to `web/index.html` that reads the stored choice and the width before any script loads, and paint the sidebar's frame there, so nothing shifts when React mounts. The bar keeps the logo, the wordmark and the view switch, and the band keeps the box and the stamp; the next ticket moves them. New copy keys: `nav.home`, `nav.collapse`, `nav.expand`, `nav.menuClose`. Icons from lucide: `house`, `package`, `folder-open`, `book-open`, `file-pen-line`, `database`, `panel-left-close`, `panel-left-open`.

Read first: the plan's sections 7.2, 7.3 and 8.1; block 2 of `design-md.md`; the prototype at 1440, 1280 and 390 px, with its "Rail at rest" switch on By width, Labels and Icons, the Menu open at 390 px, and the View switch on Public; `web/src/components/TopNav.tsx` (`SECTIONS`, the Menu panel, the focus hand-offs at 466 to 479); `web/src/components/Frame.tsx`; `web/src/App.tsx` (`navMode.tabs`, `projectsHref`); `web/src/routes.ts`; `web/index.html` lines 8 to 25; `web/src/gallery/Gallery.tsx`; `web/tests/shell.spec.ts` (lines 61 to 83), `gallery-frame.spec.ts`, `routes.spec.ts`.

**Blocked by:** XX (Tokens, fonts and lint for the redesigned shell)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] From 1024 px the sections are a sidebar named "Main" beside the page, 224 px wide from 1440 px and 64 px from 1024 to 1439 px by default, Home first and each section of the applied view once, and the bar holds no section link; `shell.spec.ts` and `gallery-frame.spec.ts` prove the order, the widths and `aria-current` at 1440, 1280 and 1024 px.
- [ ] "Collapse the sidebar" turns it into the rail and "Expand the sidebar" back, the choice survives a reload, each rail item's tooltip shows its label on hover and on keyboard focus, and a test finds no transition on the sidebar's width.
- [ ] `web/index.html` paints the sidebar's frame at the stored or default width before any script runs, and `shell.spec.ts`'s first-paint test finds the painted and mounted sidebar, bar and band boxes equal at 1440, 1280, 800 and 390 px.
- [ ] Below 1024 px the labelled Menu button opens the Menu sheet as a modal dialog named "Menu" with the page and the bar inert; Escape, "Close the menu" and the scrim close it and return focus to the Menu button; when the window narrows past 1024 px, focus on a sidebar item moves to the Menu button.
- [ ] Every route still opens from its item and focuses its h1 (`routes.spec.ts`), the public view shows Home, Projects, Lessons and Data only and the officer's view no Following and no reviewer pages (`views.spec.ts`), and axe, reflow at 320 px and the target sizes pass on every route.

**Gate seconds added:** about -0.4 (+0.4 for the rail tooltip and width tests; -0.8 because the 22 `navigation--*` and `views--*` shots become about 16 states, each captured once per width).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. The width no longer animates (plan 5.7: width is a layout property, and the motion adds wait without news). Settles in full ticket 58's Menu label at 320 px (line 129); in part ticket 60's wordmark touching the Menu button at 320 px (line 47), which the bar ticket finishes. Specs to update: shell.spec.ts, gallery-frame.spec.ts, routes.spec.ts, views.spec.ts, capture.spec.ts (and languages.spec.ts, sweep.spec.ts and gallery-a11y.spec.ts where they name the tabs). Gallery states: sidebar open, rail, rail tooltip, focus and hover on an item, the sheet open, a sheet row focused, 320 px, and the public view's sidebar. Ticket 57's two whitespace items in specs this ticket edits may ride along.

---

# XX: The top bar holds the box, and the stamp moves to the sidebar

**What to build:** Paste block 3 of `design-md.md`. Merge the white band into the navy bar. From 1024 px one 56 px row that sticks: the logo (same file, hash and size), the wordmark, the one box from the page's content edge (or 32 px after the wordmark with the rail) up to 640 px wide on `surface` with 4 px corners and `focus-on-dark` around it, and the view switch 24 px from the right edge as a 32 px control with 4 px corners. The box keeps one row; its scope chip drops "Within" below a box width of 35rem. Below 1024 px the bar does not stick and the box takes its own row; with a chip the box's search icon hides, so the chip and the text each take a row; below 360 px the icon always hides; below 768 px the view switch moves to the Menu sheet's foot, the "/" hint hides, and the placeholder takes its short form, "Open a project or package, or ask" (new key `box.placeholderShort`), while the field's name keeps the whole sentence. The data stamp moves to the sidebar's foot under Data, to the Data item's tooltip in the rail, and to the Menu sheet's foot, in a 24 px line box. The skip link shows below the bar, over the page. Repaint `web/index.html`'s bar to match. The view switch's popover keeps ticket 40's rows, past-date field and language choice; the prototype draws its rows and date field (`?view-open=1`).

Read first: the plan's sections 7.2, 8.2 and 7.10 (the box's worst case); block 3 of `design-md.md`; the prototype at 1440, 1024 and 390 px, at 390 px with the Data switch on Longest (a 35-character reference in the chip), and with the view switch's popover open; `web/src/components/BoxBand.tsx`, `IntentBox.tsx`, `TopNav.tsx`, `SkipLink.tsx`; `web/index.html`; `web/tests/shell.spec.ts` lines 23 to 83, `gallery-frame.spec.ts`, `box.spec.ts`.

**Blocked by:** XX (The sidebar and the rail replace the tabs in the bar)

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

# XX: The page frame: window margins, the wide layout, and a drawer that never moves the page

**What to build:** Paste block 4 of `design-md.md`. Margins follow the window (16, 32, 40 px), never the page area. Add a size container `frame` (the window minus the sidebar), which the drawer does not change; the Frame sets `--frame-inline` from it, and the Document column is measured on it instead of `--window-inline`. On a wide page the drawer is `clamp(384px, 40vw, 560px)` and the page narrows with its left edge fixed; a page head that sets its title beside its actions does so by the page area (from 46rem), so a narrowed page stacks them. The drawer's head becomes the title and one caption sentence, with no eyebrow or middle dots (today's strings in the new places; the words are ticket 58's). The frame owns the sticky parts: `frame-top`, one scroll-padding hook for the bar and a sticky head, and `main`'s minimum height. The answer panel moves to the top of the page column under the bar, "In short" in `label` and its sentences in `lead`. The page's alert slot sits above the head; when a page's one request fails, it holds the error alert with "Try again" and the h1 names the page (plan 8.5). Pages keep their content; the workspace ticket and the tab tickets move them.

Read first: the plan's sections 7.5, 8.3 and 8.5; block 4 of `design-md.md`; the prototype's plan check at 1440 and 1024 px with a row's records open, and with the Data switch on Error; `web/src/components/Frame.tsx`, `EvidenceDrawer.tsx` (lines 2 to 4 and 665 to 677), `EvidenceCard.tsx`, `AnswerPanel.tsx`; `web/src/lib/useScrollPadding.ts` and DraftPage's own padding hook; `web/src/styles/app.css` lines 120 to 160; `web/tests/check-plan.spec.ts`, `drafts.spec.ts`, `answer.spec.ts`.

**Blocked by:** XX (The top bar holds the box, and the stamp moves to the sidebar)

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

# XX: The workspace layout and the task zone parts

**What to build:** Paste block 5 of `design-md.md`. Build the parts every tab ticket uses and prove them on gallery states, not on the pages: the workspace layout (an answer panel and the work in columns 1 to 7, a side-panel slot in 9 to 12 from a frame of 75rem, the drawer filling from the work's end plus a gutter to the window's edge within 384 to 600 px while the side panel hides; one column below, with the side panel's content folded into the head or after the work as each page says); `PageHead` (the breadcrumb listing parents only, each link a 24 px line box, wrapping and never cut; the h1 at 24/32 and 20/28 below 48rem; an ID line; the purpose; one action slot; the alert slot; the facts line with its drawer button below the threshold); `SidePanel` (two columns of facts from 18rem of content; a row form when it holds only a sentence); `TaskZone` with its panel and row forms, number column, tag slot (at the header's right, or under the name when an action holds the right), Show or Hide control and its five states, opening in place at once with no motion, taking over `CollapsedSection.tsx`'s look and keeping its behavior; `FootStrip` (a line that holds a checkable number is 24 px tall); and `StageLabel`. Space falls only between shown blocks, so a hidden block leaves no gap. Add `/gallery/zones`, which shows a numbered sequence with a panel, three rows, a stage label and an opened row, an unnumbered page with a panel and an action row, a row with an action and its tag under its name, a zone whose first block failed (its error alert under the header, its second block intact), a side panel in both forms, and a page head with and without its facts line, each at its worst-case string (the 257-character description and the 35-character reference from plan 7.10). No page moves onto these parts here.

Read first: the plan's sections 7.1, 7.4, 7.6, 7.10, 8.3 and 8.5; block 5 of `design-md.md`; the prototype's package page at 1440, 1280, 1024 and 390 px with the Data switch on Real, Longest and Error (open zone 2, then open the drawer from a dot), and Home's Start here at 1440 px; `web/src/components/CollapsedSection.tsx`, `PageHeader.tsx`, `Breadcrumb.tsx`; `web/src/gallery/Gallery.tsx` and `pages.tsx`; `web/tests/gallery-components.spec.ts`, `gallery-a11y.spec.ts`.

**Blocked by:** XX (The page frame: window margins, the wide layout, and a drawer that never moves the page)

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

---

# XX: The number tooltip: what a number is, where it came from, and what a click does, with its gate test

**What to build:** Paste block 13a of `design-md.md`. Every Num, Measure number and range chart dot shows three parts: what the number is (a copy-file sentence for that number alone, `pastRange.explain.*` and the others in plan 8.6), where it came from with its date (new `num.from.*` templates, one per kind of number), and what a click does, in words that name what opens (`num.act.*`), only when a click does it. Two numbers in one sentence never share a What sentence unless they come from the same record and open the same thing: "2" and "49" in the package finding say different things, and so do 3.3 and 7.9 against 4.4 and 9.1. A rounded amount's tooltip may give the record's own unrounded value (DESIGN.md's Signal line); no tooltip shows any other number the page does not show. A dot's tooltip keeps its reference, months and one sentence, now with full dates (rule 13), and gains the From line and "Select to see its records." Timing: it opens 150 ms after a pointer rests and at once on keyboard focus, opens at once with no movement within 300 ms of another closing, enters over 160 ms from the side touching the number, stays while hovered, hides 100 ms after the pointer leaves, and Escape hides it; it never opens because the page scrolled a number under a resting pointer. Placement: under the number and left aligned with it, or, for a number inside the page's finding, under the whole finding. It is a light surface at most 20rem wide, the number's description, never its name, and holds no link. A number with no tooltip and nothing to open is plain text with no underline. Add a gate test that, on the package page, the plan check, Home and a draft, opens every number and every dot whose tooltip has an action line, one page load per page, and checks that the rows, record or window it names opened. Each later ticket that adds a click adds its action line and keeps the gate test passing. New copy keys: `num.from.*`, `num.act.*`, `pastRange.explain.*` (replacing `counts` and `quantiles`, and dropping "This is the Kaplan-Meier method."), `pastRange.chart.tipSigned` and `tipOpen` rewritten.

Read first: the prototype's package page (hover "49", then "2", then "1.5"; focus a dot and press the arrow keys), Home (hover "1.23" and "two"), and the plan's sections 9 and 10; block 13a of `design-md.md`; `web/src/components/Num.tsx`, `MeasureNum.tsx`, `Popover.tsx`, `RangeChart.tsx` (the dot tooltip); `web/src/copy.ts` lines 560 to 700, 3700 to 3770 (`pastRange.chart` and `explain`); `../fairshare/web/src/components/Num.tsx`, `Term.tsx` and `web/e2e/smoke.spec.ts` lines 118 to 128 (read only); `<scratchpad>/redesign/emil-skills/emil-design-eng.SKILL.md` lines 234 to 267.

**Blocked by:** XX (The class sweep: every page's classes move to their roles)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] On the package page, hovering "49" shows nothing at 60 ms and by 260 ms shows "All comparable packages in the past range, including the four still open.", its From line and "Select to see all 49."; moving to "2" within 300 ms shows its own sentence at once; no two numbers in one sentence on the package page, the plan check, Home and a draft share a What sentence unless they share a record and an opener; keyboard focus shows a tooltip at once; Escape hides it until the focus leaves; and under reduced motion no tooltip transition is measured (`web/tests/num.spec.ts`, new).
- [ ] A dot's tooltip shows its reference, its months, one sentence with full dates, the From line and "Select to see its records.", sits above or below every dot in the lane, and stays hidden from screen readers while the dot's name says the same.
- [ ] A number inside the page's finding opens its tooltip under the whole finding, left aligned with the number, at 1440 and 390 px; after a press scrolls the page, no tooltip opens under the resting pointer until it moves.
- [ ] The gate test opens every number and every dot whose tooltip has an action line on the package page, the plan check, Home and a draft, and finds what each one names; no number without an action line carries one, and Home's "1.23" tooltip names 1,230,000.00 as the plan row's own value.
- [ ] axe finds no new violation with a tooltip open at 1440 and 390 px.

**Gate seconds added:** about +0.8 (+1.2 for num.spec.ts's five tests and the gate test's four page loads; -0.4 because the tooltip checks in answer.spec.ts and data.spec.ts that the gate test covers go).

## Comments

- October 27, 2026, design-lead: the first half of round 3's citation chain ticket, split after the second critic's review. It no longer waits for the page tickets: it edits Num, MeasureNum, Popover and the dot tooltip, which they do not, and runs beside the shell. Settles in full ticket 59's tooltips that split a date (line 35) and numbers with an underline that open nothing (lines 36 and 39); ticket 60's dot tooltip after Escape or a click (lines 40 and 41) and the missing capture of a number's tooltip in an answer (line 71). Specs to update: num.spec.ts (new), answer.spec.ts, package.spec.ts, data.spec.ts (the measure tooltips), gallery-components.spec.ts, capture.spec.ts. Gallery states: `numbers--tooltip`, `numbers--tooltip-dot`, `numbers--tooltip-finding` at 1440 and 390 px.

---

# XX: How Prism works leaves Data: each refusal gives its reason, and one window lists them all

**What to build:** Paste block 12a of `design-md.md`. How Prism works stops being a page, as the user asked (the deck at /present shows its figures). Remove `web/src/pages/data/HowStrataWorks.tsx`'s page and its sub-tab; move `WhatIDontDo` to `web/src/components/` as the body of a non-modal window, "What I turn down". Each refusal in the answer panel now says its own reason in place, as a third sentence after what I don't do and what I can do instead, from `copy.refusals[key].why`; the caption under it becomes a flush ghost, "See everything I turn down" (`answer.refusalAll`, replacing `refusalNote` and `refusalLink`), which opens that window; `CheckCriteria.tsx`'s refusal note does the same. The address `/data/how-strata-works` opens Data readiness through a replace. Leave `web/src/figures/` alone: the deck branch shares it. Data readiness's layout is the next Data ticket's.

Read first: the plan's section 8.4 (the table of where How Prism works' content goes, and the routes and tests that change); block 12a of `design-md.md`; `web/src/routes.ts` lines 61 to 64 and 133; `web/src/RoutePage.tsx` line 85; `web/src/pages/data/DataPage.tsx`, `HowStrataWorks.tsx`; `web/src/components/AnswerPanel.tsx` lines 46 and 471 to 490, `CheckCriteria.tsx` lines 18 and 205 to 215; `web/src/copy.ts` lines 15 to 60 (`REFUSALS`), 918 to 920 and 5601 to 5624; `web/src/gallery/pages.tsx` lines 87 and 1506 and `web/src/gallery/copy.ts` lines 279 and 1078 to 1079; `web/tests/data.spec.ts`, `checks.spec.ts`, `answer.spec.ts`, `sweep.spec.ts`.

**Blocked by:** XX (The class sweep: every page's classes move to their roles)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] `/data/how-strata-works` lands on Data readiness with the address replaced, Data's sub-tabs list Data readiness and Sources and licenses only, and no route, gallery page or capture links to the old address (`data.spec.ts` line 72's list and line 81's title updated, lines 780 to 847 removed; `sweep.spec.ts` lines 112 to 113 removed).
- [ ] A refusal in the answer panel shows its lead, what I can do instead and its reason, each from the copy file's refusal key, and "See everything I turn down" opens a window that lists every refusal's lead and reason, with Escape returning focus to the button (`checks.spec.ts` lines 216 to 227 and `answer.spec.ts` lines 317 to 318 rewritten; the gallery's `what-i-dont-do` sample moves to the answer panel's page).
- [ ] `git diff --stat` shows no file under `web/src/figures/` or `web/src/deck/`.

**Gate seconds added:** about -0.8 (+0.2 for the window test; -1.0 for the How Prism works test and its route-table row, the two sweep rows and two captures).

## Comments

- October 27, 2026, design-lead: the first half of round 3's Data ticket, split after the second critic's review. The user's addition of October 26, 2026 (21:40 PDT) settles round 2's open item on How Prism works. It runs beside the shell: it touches AnswerPanel.tsx only in the refusal note (lines 471 to 490), while the frame ticket moves the panel's wrapper; whichever merges second rebases. Captures: `web/capture/shots.ts` line 1746's `refusal--how-strata-works` becomes `refusal--why`, and line 1973's `data("how", ...)` goes.
- The deck branch's follow-up for this ticket, lines on `deck/second-draft` at 494a176b: `web/src/deck/copy.ts` lines 1, 6 and 503 name How Prism works in comments; `web/src/figures/order.ts` line 17's `PAGE_ORDER` is then used by nothing in the app, so the deck keeps or removes it.

---

# XX: Home: the briefing leads, Worth knowing in a panel, Waiting for you beside it

**What to build:** Paste block 6 of `design-md.md`. Move Home onto the workspace layout, as the prototype draws it from `tests/fixtures/api/home.json`. The h1 is the date line in `label` and the briefing's sentences in the `finding` style, each count word still opening its window; the first-run and quiet sentences, which report a state, take `lead`. The Start here strip becomes a Task zone row under the briefing (its six links, their order and Remove unchanged; Remove at the row's right; "Examples Prism set up for you" as its tag, under the name at every width). Worth knowing is a panel in columns 1 to 7 named "Worth knowing" with the tag "Fixed checks, no model" (split from today's middle-dot string; new keys `home.worth.title` and `home.worth.tag`, words ticket 58's), each line a badge, its one verb at the first row's right, its sentence and its marker, then the foot strip's source. Waiting for you is the side panel from a frame of 75rem; below it the panels stack, Worth knowing first. When an answer opens on Home, the briefing folds to the date line and its first sentence in `body` with a flush ghost "Show the briefing" (`aria-expanded`; new keys `home.briefingShow` and `home.briefingHide`), and the answer panel takes columns 1 to 7 above the head (fairshare's strip, plan 9 pattern 6). The officer's view (`home-preview-piu.json`) keeps the same shape with its own briefing, no Start here, and Waiting for you as a row; the public view (`home-preview-public.json`) has "Home" as its h1, its sentence in `lead`, and "Closed projects" with the tag "Contracts traced from public records" (new keys `home.publicView.title` and `home.publicView.tag`), with no side panel. A failed load is the error alert in the alert slot with "Home" as the h1.

Read first: the prototype's Home at 1440, 1024 and 390 px with the Data switch on Real, Empty and Error, with the View switch on Agency officer and Public, and with "Show an answer asked from Home"; the plan's sections 7.7, 8.0 (Home), 8.4 (Home) and 9; block 6 of `design-md.md`; `web/src/pages/HomePage.tsx`; `web/src/copy.ts` lines 8443 to 8640 (`home`); `config/roles.toml` line 242; `web/tests/home.spec.ts`; `web/tests/mocked.ts` lines 88 to 99; `web/capture/shots.ts` lines 226 to 236; `../fairshare/web/src/components/SummaryStrip.tsx` (read only).

**Blocked by:** XX (The workspace layout and the task zone parts); XX (The class sweep: every page's classes move to their roles)

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

# XX: Projects: sub-pages in the sidebar, a shorter project head, and Summary's finding first

**What to build:** Paste block 7 of `design-md.md`. Following and All projects become sidebar items under Projects for World Bank staff, and `ProjectsTabs.tsx`'s row goes; the officer's and the public view show All projects only. All projects is a panel named "All projects" with the search field, the count line, the table, the pagination and its source as the foot strip, as the prototype draws it; long project names (104 characters in the fixture, P180287) wrap in full. A search with no match keeps the query in the field and puts the copy file's no-match sentence, its body and "Show all projects" in the panel, with no count line, table or pager; a failed load keeps the panel's name and search and puts the error alert in the list's place. Start the project page from the design lead's brief: the head gets shorter (the agency line keeps one line with "Show all agencies", the Follow control moves to the head's right, the ID, country and status in the h1's line take weight 400); the five tabs stay tabs and take their order from the copy file only; Summary opens on its finding in the `finding` style, then its fact tables, two side by side from a page area of 75rem and one column below.

Read first: the prototype's All projects at 1440, 1024 and 390 px, with the Data switch on Longest, Empty and Error, and with the View switch on Public; the design lead's brief for the project page; the plan's sections 8.0 (Projects and the project page) and 8.4; block 7 of `design-md.md`; `web/src/pages/ProjectsPage.tsx`, `FollowingPage.tsx`, `ProjectPage.tsx`, `project/SummaryTab.tsx`; `web/src/components/ProjectsTabs.tsx`, `ProjectHeader.tsx`, `FollowControl.tsx`, `FactTable.tsx`; `web/src/routes.ts` lines 140 to 144; `web/tests/projects.spec.ts`, `following.spec.ts`, `hub.spec.ts`.

**Blocked by:** XX (The workspace layout and the task zone parts); XX (The class sweep: every page's classes move to their roles)

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

---

# XX: Packages and the plan check: the plan check under Packages, and rows that open their records

**What to build:** Paste block 8 of `design-md.md`. The Packages head holds "Check a plan" (primary) and "Plan a package" (secondary) at its right, and its list is one panel with the title sentence in `lead`, the count line, the table and its source as the foot strip; "Last worked on" opens its definition in a window from the column head. Empty: a Task zone row with "You have no packages or checked plans yet." Error: the error alert in the list's place. The plan check moves to the Packages section in `routes.ts` (its address does not change) and its breadcrumb starts at Packages; in a view without Packages (the public view) it stays lit as Projects with its breadcrumb at the project. It opens on its finding in the `finding` style; its head (the agency as h1, wrapping in full, the plan's date, the check pill and "Draft review notes (n rows)" with its caption) sticks under the bar from 1024 px. With no signal to draft from (no activity marked, or the public view's held-back signals), the head holds the check pill and no action and does not stick, and only the data-note rows are marked. Its order becomes the activities panel, "What changed" as a closed row that "See what changed" opens, and the baseline as a row (not in the public view). A row's reference opens the row's records in the drawer (the reason, "What I checked", the plan row, its source, "Open the activity" and "See the past range"); the row keeps the current mark while they show; the finding's count words mark the rows they count and move focus to the first one's reference. The table has six columns from a page area of 60rem, three (Activity, Estimated (US$), What Prism found) below it, so 1024 px with the rail draws three, and cards below 40rem; Estimated (US$) never wraps, and no word breaks inside itself. "What Prism found" opens its definition in a window. The check line loses its 48 px indent. A failed check is the error alert in the alert slot with "Procurement Plan" as the h1. New copy keys: `checkPlan.activitiesTitle`, `checkPlan.columns.method`, `checkPlan.changes.show` and `hide`, `checkPlan.rowChecked`, `checkPlan.rowPlan`, `evidence.planRowCaption`.

Read first: the prototype's Packages and plan check at 1440, 1024 and 390 px, with a row's records open, with a count word pressed, with the Data switch on Longest, Empty and Error, and with the View switch on Public; the plan's sections 7.5, 8.0, 8.4 and 8.5; block 8 of `design-md.md`; `web/src/pages/PackagesPage.tsx`, `CheckPlanPage.tsx`; `web/src/components/PlanCheck.tsx`, `Checks.tsx` (line 97), `EvidenceDrawer.tsx` (the What-record view); `web/src/routes.ts` lines 146 to 149; `web/tests/check-plan.spec.ts`, `box.spec.ts`; `tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09-public.json`.

**Blocked by:** XX (The workspace layout and the task zone parts); XX (The class sweep: every page's classes move to their roles)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The Packages head holds its two buttons at its right when the page area allows and under the purpose otherwise, each still puts the box in its mode with focus in the box, and "Last worked on" opens its definition from the column head at 1440 and 390 px (`box.spec.ts`, `planned-package.spec.ts`).
- [ ] On the Northern Water Works Development Agency plan of October 9, 2026 the sidebar lights Packages, the breadcrumb starts at Packages, the page opens on its finding in the `finding` style, and the first marked row starts inside the first screen at 1440 by 900 and 1024 by 768 (`check-plan.spec.ts`); in the public preview it lights Projects, the breadcrumb starts at the project, the finding holds the signals back and the head holds no action and does not stick.
- [ ] A row's reference opens its records in the drawer with the reason, what I checked, the plan row, its source and both links; the row keeps the current mark; Escape returns focus to the reference; pressing "two" marks the two Watch rows and focuses the first one's reference; at 1440 px with the sidebar open the table keeps three columns beside the drawer.
- [ ] The table draws six columns at 1280 and 1440 px and three at 1024 px with the rail, and a scan of every table cell finds no word broken inside itself at 1024, 1280 and 1440 px in the real and longest data (`check-plan.spec.ts`).
- [ ] A landing on any row leaves no row cut under the bar and the head at 1440 by 900, 1440 by 700, 1024 by 768 and 320 by 568, the check line starts on its panel's text edge at 1440 and 390 px, and with a 54-character agency name and a 232,524,000.00 estimate nothing scrolls sideways at 320 px (`check-plan.spec.ts`, `checks.spec.ts`).

**Gate seconds added:** about +0.5 (the word scan, one page load at each of three widths; the public preview's check).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. The second critic found round 3's first prototype drawing six columns at 1024 px, which broke "Review" and "Pending Implementation" inside the word; the 60rem threshold here was already right. Settles in full ticket 59's check line indent (line 29). Ticket 59's landing item (line 26) stays with 59, but its test must use the bar's offset. Specs to update: check-plan.spec.ts, box.spec.ts, checks.spec.ts, planned-package.spec.ts (and routes.spec.ts and sweep.spec.ts where they name the plan check's section). Gallery states: `plan-check`, `six-checks` and `table--cards-below-lg` at three widths, and a new `evidence--plan-row-check` view. First wave of the page tickets.

---

# XX: The package workspace as numbered task zones, with its facts in a side panel

**What to build:** Paste block 9 of `design-md.md`. Move the package workspace and the planned package onto the workspace layout and the zone parts. Sections 1 to 5 become Task zones numbered 1 to 5 with the stage labels "Planning" (before 1) and "Tender design" (before 5) and the PPSD sections as tags; the uppercase eyebrows and middle-dot headings go. Zone 1 is a panel that opens on its finding in the `finding` style; each block's Note, coverage line and source line move into its foot strip, and "Advertised again" stays its second block. Zones 2 and 5 are closed rows; zones 3 and 4 are rows while they hold only their sentence, panels when they have risks or options (zone 3 then holds "Suggest n PPSD risk rows", the page's one primary action for staff). The time estimate's abstention moves under the chart in `body`. The facts become the side panel "From the plan row" from a frame of 75rem, and one facts line with "Show the plan row" below it. The package head no longer sticks; its h1 wraps in full however long. A number in the finding or the summary opens "Show the table" filtered to the rows it counts, scrolls the table's title under the bar and moves focus to the count line, which repeats the pressed number and is followed by "Show all {total}" (keys `pastRange.table.shown.*` and `pastRange.table.showAll`); each number's action line says so ("Select to see the two packages."). Below 20 comparable packages, the first-person sentence that holds back is zone 1's finding in the `finding` style, the count follows in `body`, the chart keeps its dots and plan line with no band, middle or 8-in-10 line, and the table opens with the page. A failed past range is the error alert in zone 1's body under its header, with "Advertised again" intact. In a card the row's name is its heading. The planned package puts "What I understood" in an unnumbered panel before zone 1. New copy keys: `packagePage.factsTitle`, `packagePage.factsShow`, the facts line's template, `risks.ppsdTag`, `approach.ppsdTag`, `evidence.package.caption`, `pastRange.table.shown.*`, `pastRange.table.showAll`.

Read first: the prototype's package page at 1440, 1280, 1024 and 390 px, with the drawer open from a dot and from the plan row, with "2", "49" and "9.1" pressed in turn, and with the Data switch on Longest, Empty or few and Error; the plan's sections 6, 7.4, 7.6, 7.10, 8.4 and 8.5; block 9 of `design-md.md`; `web/src/pages/PackagePage.tsx`, `PlannedPackagePage.tsx`; `web/src/components/PackageFacts.tsx`, `PastRange.tsx`, `RangeChart.tsx`, `RebiddingBlock.tsx`, `StepsSection.tsx`, `RisksSection.tsx`, `ApproachOptions.tsx`, `CheckCriteria.tsx`, `Criteria.tsx`; `web/src/copy.ts` lines 3577 to 3800 and 4320 to 4800; `tests/fixtures/api/comparables-ke-nwwda-541055-prior.json` and `rebidding-ke-nwwda-541055-prior.json`.

**Blocked by:** XX (Packages and the plan check: the plan check under Packages, and rows that open their records); XX (The number tooltip: what a number is, where it came from, and what a click does, with its gate test)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The five sections are Task zones numbered 1 to 5, with "Planning" before zone 1, "Tender design" before zone 5 and the PPSD sections as tags; zone 1 is a panel and the closed or sentence-only zones are rows; no section shows an uppercase eyebrow or a middle-dot heading at 1440, 1024 or 390 px.
- [ ] On KE-NWWDA-541055-CW-RFB zone 1 opens on "2 of 49 comparable packages, fewer than 1 in 10, were signed within the plan's 1.5 months." in the `finding` style, and the finding's top sits inside the first screen at 390 by 844 and 1024 by 768.
- [ ] Pressing "2" opens the table filtered to KE-WAJWASCO-372776-CW-RFB and KE-WAJWASCO-356671-CW-RFB, with "Showing the 2 of 49 packages signed within 1.5 months." focused and "Show all 49" after it, and the first of those rows inside the window at 1440 by 900 and 390 by 844; "Show all 49" shows the first 20 of 49 with the count line focused; no count line states a number the tool did not return (`package.spec.ts`, `time-estimate.spec.ts`).
- [ ] With `comparables-ke-nwwda-541055-prior.json` (seven comparables), zone 1's finding is "I'm not giving a range: only seven comparable packages. Here are all seven." in the `finding` style, the chart draws seven dots with no band, middle or 8-in-10 line, and the table is open; with the past range's request failing, zone 1 shows the error alert under its header and "Advertised again" still shows.
- [ ] The past range's chart is at least 560 px wide at 1440 px with the sidebar open and at 1280 px as a rail, and at least 800 px at 1024 px as a rail; the opened dot keeps its 2 px `info-icon` ring while the drawer shows it; from a frame of 75rem the facts are the side panel "From the plan row", its marker opens the plan row in the drawer, the drawer takes the side panel's place, and the zones keep their left edge and width at 1440 and 1280 px; below it the facts line's "Show the plan row" opens the same record.
- [ ] package.spec.ts, planned-package.spec.ts, package-risks.spec.ts, package-steps.spec.ts, package-rebidding.spec.ts, criteria.spec.ts, time-estimate.spec.ts and ppsd.spec.ts pass, with no new axe violation at 1440, 1024 and 390 px in the loading, ready, few, abstention, empty and error states.

**Gate seconds added:** about +0.2 (+0.6 for the press at two widths and the few state; -0.4 for the eyebrow and middle-dot heading checks that go).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. The second critic found that pressing "2" in round 3's first prototype marked rows in the unfiltered table and left three still-open packages on screen; the filter puts the two counted rows under the count line. Settles in full ticket 59's planned package header (line 64) and finishes ticket 59's section name outranking the finding (line 61). Ticket 59's chart, skeleton and rebidding items (lines 54 to 77) stay with 59 and must be measured again on the new widths. Specs to update: the eight named above plus box.spec.ts. Gallery states: `past-range` at three widths, filtered and in the few state; captures for the package page in loading, ready, drawer open, few, error and the planned package's reading state. Second wave: it waits for the Packages ticket because both edit the What-record view of a plan row and the Packages copy blocks, and for the number tooltip because it adds action lines to its numbers.

---

# XX: Lessons: the digest leads, zones in order, reviewer pages in the sidebar

**What to build:** Paste block 10 of `design-md.md`. The digest sentence becomes the page's finding in the `finding` style, with its count words still opening what they count, followed by its caption and the sources note; on a first visit its status sentence takes `lead`. Then the zones in order: "Changed where you used it", "New", "Your reports", "The library" (with its filters), each a panel when it holds lessons or reports and a row when it holds only its sentence; the library's empty row no longer repeats the finding. The reviewer pages (Waiting for review, Passage reports, Judging) become sidebar items under Lessons, with their counts in a badge hidden at zero, for the roles that have them, and the sub-tab row in `LessonsPages.tsx` goes. A review page uses the workspace layout, with its history list in the side panel where the page has one. A failed load is the error alert in the alert slot.

Read first: the prototype's Lessons at 1440, 1024 and 390 px, with the Data switch on Error; the plan's sections 8.0 (Lessons, a lesson's page) and 8.4; block 10 of `design-md.md`; `web/src/pages/LessonsTab.tsx`, `LessonsPages.tsx`, `ReviewPage.tsx`, `PassageReportsPages.tsx`, `JudgingPages.tsx`; `web/src/copy.ts` lines 5859 to 5900 and 6354 to 6431; `web/tests/lessons.spec.ts`, `lessons-page.spec.ts`.

**Blocked by:** XX (Projects: sub-pages in the sidebar, a shorter project head, and Summary's finding first)

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

# XX: Drafts and a draft's page: three groups, the state in one place, and who checked it

**What to build:** Paste block 11 of `design-md.md`. The Drafts list is one panel with three groups, To check, Checked and Exported, each an `h2` with its count line and its rows (the title as a link, the project and the drafted, checked or exported line, the notes and opened count), discarded drafts folded under them; with no drafts, a Task zone row with "You have no drafts to check." and "Go to Packages"; a failed load, the error alert in the panel's place. A draft's page uses the workspace layout, as the prototype draws it from `drafts-review-notes-partial.json`: the lede as the page's finding in the `finding` style, the method sentence, the check line and the removed box in one `surface-2` block, the notes table (cards below 560 px of column, with no panel name that repeats the h1), the sources, and the draft bar held to the work's columns. The side panel "State of this draft" holds the state stepper, what the draft was made from and when it was drafted; below the workspace threshold the stepper takes one line in the head under the subtitle and the rest follows the draft. After "Mark as checked" the bar's hold line gives way to "Checked by you on {date}." (by role, `draft.tab.checkedYou`), Export to Word becomes primary and takes focus, the side panel adds the same line, and a polite status says what changed; nothing fades (fairshare's decision bar, plan 9 pattern 9). A draft that fails to load is the error alert in the alert slot, with "Drafts" as the h1 and no scope chip.

Read first: the prototype's Drafts and a draft at 1440, 1024 and 390 px, the Drafts list with the Data switch on Empty and Error, the draft with "Mark as checked" pressed and with Error; the plan's sections 7.8, 8.0 (Drafts, a draft's page) and 9; block 11 of `design-md.md`; DESIGN.md's Draft bar, State stepper and Access label rows; `web/src/pages/DraftsPage.tsx`, `DraftPage.tsx`, `DraftNewPage.tsx`; `web/src/components/DraftBar.tsx`, `StateStepper.tsx`, `AccessLabel.tsx`; `web/tests/drafts.spec.ts`; `../fairshare/web/src/components/Document.tsx` lines 292 to 307 (read only).

**Blocked by:** XX (Home: the briefing leads, Worth knowing in a panel, Waiting for you beside it)

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

---

# XX: Data readiness by the page area, with its pages in the sidebar

**What to build:** Paste block 12b of `design-md.md`. Data readiness and Sources and licenses become sidebar items under Data and the sub-tab row goes. Convert every window breakpoint in `web/src/pages/data/DataReadiness.tsx` and `web/src/components/ReadinessTable.tsx` to the page area's container queries. The headline becomes the page's finding in the `finding` style; "What you can ask" and "Sources" are panels; the last three sections are closed rows with their one-sentence summaries. Every number keeps its window. Start from the design lead's brief, which draws Data readiness at 1440 and 390 px.

Read first: the design lead's brief for this ticket; the plan's section 8.4 (Data); block 12b of `design-md.md`; `web/src/pages/data/DataPage.tsx`, `DataReadiness.tsx`, `SourcesAndLicenses.tsx`; `web/src/components/ReadinessTable.tsx`, `MeasureNum.tsx`; `web/tests/data.spec.ts`, `shelf.spec.ts`, `sources.spec.ts`.

**Blocked by:** XX (Projects: sub-pages in the sidebar, a shorter project head, and Summary's finding first); XX (How Prism works leaves Data: each refusal gives its reason, and one window lists them all)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The sidebar under Data lists Data readiness and Sources and licenses only, and Data's sub-tab row is gone (`data.spec.ts`).
- [ ] No window breakpoint remains in `DataReadiness.tsx` or `ReadinessTable.tsx`, and a test opens Data readiness beside the drawer at 1024 px and finds its tables laid out as at a 550 px page area.
- [ ] The headline is the page's finding in the `finding` style; "What you can ask" and "Sources" are panels, the last three sections are closed rows that open in place with focus kept on their button, and Data readiness at 390 px is at least 30 percent shorter than the 11,205 px of `current/data-390.png`.

**Gate seconds added:** about +0.3 (the beside-the-drawer test).

## Comments

- October 27, 2026, design-lead: the second half of round 3's Data ticket, split after the second critic's review. Settles in full ticket 59's Data pages laid out by the window (line 40), and ticket 59's numbers that carry an underline but open nothing on Data readiness (lines 36 and 39) if the number tooltip ticket has not taken them. Specs to update: data.spec.ts, shelf.spec.ts, sources.spec.ts, capture.spec.ts. Captures: `readiness` at three widths. Second wave: it waits for the Projects ticket because both fill the sidebar's sub-item slot.

---

# XX: The check window and the drawer's motion

**What to build:** Paste block 13b of `design-md.md`. (1) **The check line's window**: after the check line, a flush text button "How was that checked?" opens a non-modal window titled "How I checked this answer" or "How I checked this draft". When the verifier removed a sentence, it opens on "These counts include the two sentences I removed. The check line counts only the sentences I kept." (`checkLine.howScope`), because the window counts every sentence written and the line only those on screen; then the verifier's done line, the six checks as an ordered list in the steps' own words (a draft's step 2 says "came back for this draft"), "A number passes only when a record holds it at the same rounding." and the Answer ID or "Draft ID {id}, run {run}" in mono, breaking anywhere; the check line and the removed box share one `surface-2` block. (2) **The evidence drawer**: it enters with opacity and 12 px from the right over 160 ms, closes at once, lands on the clicked row of a list view with `tint`, and keeps the opener's current mark; its placement follows the user's call in `open.md` item 3 (beside, as today, unless the user chooses over, which then takes a `line-strong` left edge with the popover shadow). New copy keys: `checkLine.how`, `checkLine.howTitle`, `checkLine.howTitleDraft`, `checkLine.howScope`, `checkLine.rounding`, `checkLine.runId`, `checkLine.draftId`, `steps.check.six.sourcesDraft`.

Read first: Home with an answer open and "How was that checked?" pressed, and a draft with "How was that checked?" pressed (`?page=draft&how=1`); the plan's sections 9 (pattern 3) and 10; block 13b of `design-md.md`; `web/src/components/Checks.tsx`, `AnswerPanel.tsx`, `Answer.tsx`, `EvidenceDrawer.tsx`; `web/src/copy.ts` lines 785 to 856 (`steps.check`); `tests/fixtures/api/drafts-review-notes-partial.json` (`checks.shown` and `checks.checked`); `../fairshare/web/src/components/Answer.tsx` lines 94 to 119 (read only).

**Blocked by:** XX (Drafts and a draft's page: three groups, the state in one place, and who checked it); XX (How Prism works leaves Data: each refusal gives its reason, and one window lists them all)

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
