# Critique of the shell redesign, round 3

Written October 27, 2026 at 1:12 AM PDT by the independent design critic. I share no context with the design lead. I judged what renders in `prototype.html` and read `plan.md`, `design-md.md`, `tickets.md` and `open.md` for intent and build risk. I changed nothing in the lead's folder or in the repo, and I did not touch the local app.

Checklists, in the order read: the frontend-design skill's calibration list (`frontend-design/SKILL.md` lines 38 to 45), `design-critique/SKILL.md`, `accessibility-review/SKILL.md`, `emil-skills/review-animations.SKILL.md`, the failure signatures in `emil-skills/break-ui.SKILL.md` (lines 95 to 115), DESIGN.md, `user-additions.md` and `fairshare/notes.md`.

## What I looked at

The CLI shots the orchestrator asked for, all in `<scratchpad>/redesign/critique/`:

- `r3-1440.png`, `r3-1024.png`, `r3-390.png` (the package page, the prototype's default)
- `r3-1440-long.png`, `r3-390-long.png` (`?data=long`, the worst-case switch)
- `r3-1440-switches.png` (`?rail=icons&pane=over&drawer=dot&page=package`, the comparison switches on)

My own captures, 117 files in `<scratchpad>/redesign/critique/r3/`, taken by the scripts beside this file (`r3-shoot.cjs`, `r3-probe.cjs`, `r3-zoom.cjs`, `r3-words.cjs`, `r3-sheet.cjs`):

- Every page (home, packages, plancheck, package, projects, lessons, drafts, draft) at 1440, 1024, 390 and 320 px, each with `data=long` and `data=empty` at 1440 and 390 px: `r3/<page>-<width>[-long|-empty].png`
- Whole pages: `r3/package-1440-full.png`, `r3/plancheck-1440-full.png`, `r3/home-1440-full.png`, `r3/draft-1440-full.png`, `r3/package-390-full.png`
- States: `r3/package-1440-tip-finding.png`, `r3/package-1440-tip-dot.png`, `r3/home-1440-tip.png`, `r3/press2-1440.png`, `r3/press2-390.png`, `r3/package-1440-drawer-dot.png`, `r3/package-1440-drawer-dot-over.png`, `r3/package-390-drawer-dot.png`, `r3/plancheck-1440-drawer-row.png`, `r3/plancheck-1440-drawer-over.png`, `r3/home-1440-answer.png`, `r3/home-1440-answer-how.png`, `r3/draft-1440-how.png`, `r3/draft-1440-checked.png`, `r3/menu-390-open.png`, `r3/package-1440-loading.png`, `r3/package-1280-auto.png`, `r3/package-1280-labels.png`, `r3/package-1440-icons.png`
- Close-ups and sheets: `r3/zoom-plancheck-1024-table.png`, `r3/zoom-plancheck-1440-long.png`, `r3/sheet-390.png`, `r3/sheet-1024.png`, `r3/sheet-long.png`, `r3/sheet-long-390.png`, `r3/sheet-shell.png`, `r3/sheet-current.png`
- Numbers: `r3/measure.tsv` (finding top, sideways scroll and axe per state), `r3/words.txt` (words broken inside themselves)

For comparison I used the current app's screenshots in `<scratchpad>/redesign/current/`.

## Scores

From 1 to 5, where 5 is best. For build risk, 5 means low risk. Every score below 4 has its evidence in the section after the blocking list.

| Line | Score | Short reason |
|---|---|---|
| Hierarchy | 4 | The finding is the largest type on every page that has one, inside the first screen at 1440, 1024 and 390 px |
| Distinctiveness | 3 | No generic default, but the list pages share one admin silhouette and the bold move is a font weight |
| Fit to the World Bank language | 4 | Navy only in the bar, worldbank.org's blues and greys, Open Sans and Roboto Mono, the chart guide's labels, a source line under every block |
| Task flow | 4 | Each drawn page opens on the right thing for staff; the officer and public views are words only |
| Progressive disclosure | 4 | Closed rows with a one-sentence summary, the drawer, windows on count words, "Show them" |
| Delight | 3 | The three moments `morning.md` tells the user to try each miss |
| Motion | 4 | Short, origin-aware, transitions not keyframes, nothing under reduced motion |
| Accessibility | 4 | axe found nothing in 21 states; focus, Escape and reduced motion work; two small gaps |
| Copy | 3 | Plain and first person, but the first tooltip the user is sent to names the wrong number and the draft's window says "for this question" |
| Worst-case data | 3 | Long strings hold, but the plan check breaks two words at 1024 px and four pages have no empty, few or error state |
| Build risk | 3 | Eight serial layers before the last page lands, and five tickets each touch seven or more specs |

## The one change

Make the number chain land exactly. Give every number its own tooltip sentence, show the rows a count counts first and in view when it is pressed, and make the check window count what the check line counts. The user asked for delight that puts the right thing where the reader looks. The three moments `morning.md` sends the user to first ("hover 49 then 2", "press 2", "How was that checked?" on a draft) are that delight, and today each one shows the wrong thing or shows it off screen. Fixing them is small, and it turns the fairshare chain from a description into something the panel feels.

## What must change before the tickets open

Each item names the evidence and the fix. Items 1 to 4 lift delight and copy; items 5 and 7 lift worst-case data; item 8 lifts build risk; item 9 is distinctiveness's.

1. **"49" carries the tooltip of "2".** Both numbers in the finding use `tip-id="tip-within"` (`prototype.src.html` lines 1019 and 1314), so hovering or focusing 49 says "Packages signed in 1.5 months or less, out of all 49, including the 4 still open." (`r3/package-1440-tip-finding.png`). A screen reader hears the same description on both. Fix: one `What` template per number. For 49: "All comparable packages in the past range, including the 4 still open." Its action line then says what its click does ("Select to see all 49."). Add to the citation chain ticket a criterion that no two numbers in one sentence share a `What` sentence unless they open the same rows.

2. **Pressing "2" lands on three unmarked rows.** The page scrolls so the count line sits at 440 px and takes focus, but the two marked rows are at 939 and 1253 px in a 900 px window, and at 1049 and 1455 px in an 844 px window (`r3-probe.cjs`; `r3/press2-1440.png`, `r3/press2-390.png`). What is on screen are three still-open packages marked "Not yet", the opposite of what was pressed. fairshare scrolls to the rows themselves (`fairshare/notes.md` line 132). Fix: when a count marks rows, the table shows the marked rows first under the count line ("Showing the 2 marked of 49. Show all 49." from the copy file), or scrolls the first marked row into view under the count line. Change the package ticket's third criterion to require the first marked row inside the window at 1440 by 900 and 390 by 844.

3. **The draft's "How I checked this draft" window disagrees with its own check line.** The check line says "5 of 5 numbers match records; 4 of 4 dates match records." The window under it says "9 of 11 numbers and dates matched a record or a quote." and "3 of 3 sources I cited came back for this question.", while the page's Sources list holds two (`r3/draft-1440-how.png`). Both counts are the verifier's (`tests/fixtures/api/drafts-review-notes-partial.json` has `checks.shown` 5 of 5 and 4 of 4, and `checks.checked` 9 of 11, `checks.sources` 3 of 3), so nothing is made up, but the two scopes sit side by side with no sentence that joins them. DESIGN.md section 7 rule 15 asks for one denominator per comparison. Fix: one copy-file sentence at the top of the window, "These counts include the two sentences I removed. The line above counts only what I kept.", or show the `shown` counts in the window too. Give the draft its own step 2 ("came back for this draft") and add the draft's ID label ("Draft ID {id}, run {run}") to plan section 8.6's new keys; today 8.6 lists only `checkLine.runId` "Answer ID".

4. **A dot's tooltip has no source line and no action line, though its click opens the drawer.** `r3/package-1440-tip-dot.png` shows the reference, "3.5 months" and "Kenya. Signed Jan 3, 2022. Its notice was published Sep 17, 2021." `design-md.md` block 13 lists Dot as a variant whose click opens the package's records (line 504), and its own rule says the action line shows whenever a click does something. Fix: add the `num.from.*` line ("From Procurement Notices and Contract Awards, through October 13, 2026.") and "Select to see its records." to the dot's tooltip, and name dots in the citation chain ticket's gate test, which today opens only "every number whose tooltip has an action line" and so would skip them.

5. **The plan check breaks "Review" and "Implementation" inside the word at 1024 px.** With the rail, the page area is 896 px (56rem) and the table still draws six columns, so the Review head is 72 px and Process status 107 px wide; "Pending Implementation" wraps as "Implementa / tion" (`r3/zoom-plancheck-1024-table.png`, `r3/sheet-1024.png`). `r3-words.cjs` scanned all eight pages at five widths with real and longest data, and this is the only place a word breaks inside itself. It is break-ui's "Long word breaks mid-word" signature (`break-ui.SKILL.md` line 104), it cuts a STEP value that rule 17 keeps word for word, and it contradicts the Packages ticket, which asks for six columns only from a page area of 60rem (`tickets.md` line 191). Fix: draw three columns below 60rem in the prototype as the ticket says, and add to the Packages ticket "no word in the table breaks inside itself at 1024, 1280 and 1440 px".

6. **A tooltip on Home shows a number the page does not show.** "1.23" in the first Worth knowing line opens "Estimated Amount (US$) in the plan row: 1,230,000.00, written in millions." (`prototype.src.html` line 1330). The value is the record's own, so Prism's rule 1 holds, but `design-md.md` block 13's Don't column says "Show a number the page does not show" (line 518). Fix: decide which rule wins. Either the tooltip names the field without its value ("check_plan's amount in millions, from the plan row's Estimated Amount (US$)"), or block 13 allows the record's own unrounded value and says so.

7. **Four pages have no empty, few or error state drawn.** `?data=empty` leaves the plan check, the package page, All projects and a draft unchanged (the same page heights in `r3/measure.tsv`), and no page draws an error state. The package page's finding slot has no rule for when Prism holds back: with fewer than 20 comparable packages, rule 15 forbids the "2 of 49 ... fewer than 1 in 10" sentence, so what takes the light 28 px line? break-ui asks for the empty and the one cases (`break-ui.SKILL.md` lines 64 to 70). Fix: before the Packages and package tickets open, draw the plan check with no signals ("None of the 9 checks found anything." from `copy.ts` line 1611), a package with fewer than 20 comparables (the first-person holding-back sentence as the finding, with the counts under it), All projects with no match, and one error state per layout.

8. **The build is eight serial layers deep, and five tickets are bigger than a night.** Tokens, then the sidebar, then the bar, then the frame, then the workspace parts, then wave one, wave two, and the citation chain. The sidebar ticket rewrites eight specs and 22 gallery shots and adds a boot-paint script; the package ticket names nine specs; the Data ticket removes a route, moves `WhatIDontDo`, changes two components' refusal notes and rewrites seven specs; the citation chain edits eight components and adds a gate test that opens every number on four pages. No ticket says how many seconds it adds to the gate, which CLAUDE.md rule 6 holds under 150. And `open.md` item 6 proposes starting the tokens ticket now, but its class sweep ("move every use to its role") edits page files that the functional tickets are editing tonight. Fix: split the tokens ticket into tokens, fonts and lint (start now) and the class sweep (after the functional tickets merge); split the Data ticket into "How Prism works leaves, with the refusal window" and "Data lays out by the page area"; split the citation chain into the number tooltip with its gate test, and the check window with the drawer's motion; give every ticket a "gate seconds added" line.

9. **Distinctiveness (3).** Either the design lead records in plan section 6 that World Bank fit outranks a stronger visual identity for this panel, or gives the most characteristic thing in this subject more room: the past range of 49 real packages is 563 px wide at 1440 px while about 400 px of grey sits empty beside it below the side panel (`r3/package-1440-full.png`). Either answer is fine; it needs to be written down.

## Evidence for each score below 4

**Distinctiveness, 3.** The plan avoids every item on the calibration list (see "Generic defaults" below), and the light finding grounded in the 2016 guide's Andes ExtraLight is a real choice. But at thumbnail size (`r3/sheet-1024.png`, `r3/sheet-long.png`) Packages, All projects, Drafts and Lessons share one shape: a bold h1, a grey purpose, one white panel, a table. Only the four pages with a finding look like Prism. The one bold move is a weight change, and the subject's most telling picture, the past range, is the narrowest thing in its column (563 px of 649).

**Delight, 3.** The pieces are right: the three-part tooltip, the window on count words, "How was that checked?", the removed box kept in view, the decided line after "Mark as checked" (`r3/draft-1440-checked.png`), the drawer that keeps the opener's mark (`r3/plancheck-1440-drawer-row.png`). But the moments a first-time user is sent to fail as blocking items 1 to 4 show: 49's tooltip describes 2; pressing 2 shows three unmarked rows; the draft's window contradicts its check line and its Sources; a dot's tooltip promises nothing though its click opens a record.

**Copy, 3.** New strings carry two errors on screens the user is told to open: the 49 tooltip (item 1) and "came back for this question" on a draft (item 3). Older strings from `copy.ts` now render larger or nearer the eye and break section 7: rule 12 in "Show the 3 packages and their reasons" (`copy.ts` line 4692) and "None of the 3 projects" (line 4429); rule 13 in the dot tooltip's "Signed Jan 3, 2022. Its notice was published Sep 17, 2021." (line 3722), a sentence in the table form; and "This is the Kaplan-Meier method." in a tooltip (line 3759) is not 10th-grade. The finding "One needs a look and two are worth watching; three have data notes." drops its noun, which matters more at 28 px. Strings not yet in a key: the draft's ID label (item 3).

**Worst-case data, 3.** What held: the 257-character h1 wraps in six lines at 1440 px and the finding still starts at 545 px; the 35-character reference keeps one row in the box at 1440 px and its own row at 390 px; the 104-character project name wraps; 232,524,000.00 never wraps (`r3/zoom-plancheck-1440-long.png`); nothing scrolls sideways in any of the 92 states I measured. What broke: item 5 (words broken inside at 1024 px) and item 7 (four pages with no empty, few or error state, and no rule for the finding when Prism holds back). The 320 by 640 package page puts the finding at 637 px, just under the first screen; the plan already reports it.

**Build risk, 3.** See item 8, and the table in "Build risk by ticket" below.

## Design critique

### First impression

The eye goes to the bold object name, then to the light finding, then to the evidence. That is the right order for a work page. Compared with the current app (`current/plan-check-nwwda-1440.png`), the plan check's finding grows from 18 px bold to 28 px light, the baseline box moves from above the table to the last row, the middle dots leave the column heads, and each row has one way into its records instead of two links. Home goes from "I have nothing to brief you on yet." in a lone card to a briefing sentence, the day's signals and what waits for you (`current/home-1440.png` against `r3/home-1440-full.png`).

### Usability

| Finding | Severity | Recommendation |
|---|---|---|
| Pressing a count lands on unmarked rows | Critical | Blocking item 2 |
| "49" tooltip describes "2" | Critical | Blocking item 1 |
| Draft window and check line count different things | Moderate | Blocking item 3 |
| The view switch has `aria-haspopup="dialog"` and opens nothing in the prototype | Minor | Draw its popover or drop the attribute in the prototype, so the morning walk does not dead-end |
| The number tooltip under a word in a three-line finding covers the next two lines of that sentence (`r3/package-1440-tip-finding.png`, `r3/home-1440-tip.png`) | Minor | For a number inside the finding, open the tooltip under the whole finding block, still left aligned with the number |
| Start here's tag floats beside its name, while Worth knowing's tag sits at the right (`r3-zoom.cjs`: tag at x 495 to 680 against Worth knowing's 748 to 888) | Minor | Put the tag under the name, as at 390 px, since Remove holds the right |

### Visual hierarchy

- What draws the eye first: the h1 on object pages, the finding on Home, Lessons and a draft. Correct.
- Reading flow: breadcrumb, h1, ID, purpose, stage label, zone name, finding, chart, foot strip. The zone name (18/600) never outranks the finding (28/300).
- Emphasis: right, with one caution. On Lessons' first visit and Home's first run the finding style carries a status sentence ("This is your first visit to Lessons. The library has no lessons yet."). That spends the bold move on an empty state; consider `lead` there.

### Consistency

| Element | Issue | Recommendation |
|---|---|---|
| Number tooltips | Three forms: three parts (2, 49), "From" as the What (1.5, `tip-plan`), no From and no action (dots) | One form, blocking items 1 and 4, and give 1.5 a What sentence |
| Zone tags | Right aligned in Worth knowing, beside the name in Start here | As in Usability |
| Inline number lines | "49 of 65" in the foot strip sits in a 20 px line box | DESIGN.md section 10 line 408 keeps an inline number's line 24 px tall; give caption lines that hold a number 24 px |

### What works well

- One finding per page, left aligned, balanced lines, the only light text; it reads as the World Bank's large light sentence and nothing else on the page competes with it.
- A panel only around open work. Zones 2 to 5 as rows with one-sentence summaries make the package page short to scan (`r3/package-1440-full.png`).
- The foot strip gives provenance one fixed place under each block.
- The drawer beside the plan check keeps the clicked row marked with `tint` and its 3 px bar, and the table keeps three columns (`r3/plancheck-1440-drawer-row.png`). "Over" covers "Draft review notes (3 rows)" (`r3/plancheck-1440-drawer-over.png`), which supports the lead's pick.
- "Mark as checked" turns the held "Export to Word" primary, gives it focus, and the bar and side panel both say "Checked by you on October 27, 2026." with nothing fading.
- Empty states are first-person sentences with one link (`r3/home-1440-empty.png`, `r3/drafts-390-empty.png`).

## Accessibility audit

Standard: WCAG 2.2 AA (https://www.w3.org/TR/WCAG22/). Date: October 27, 2026.

Summary: axe with the tags wcag2a, wcag2aa, wcag21a, wcag21aa and wcag22aa found no violation in 21 states (all eight pages at 1440 and 390 px, the drawer from a dot at 1440 and 390 px, a plan check row's records, an answer on Home, the Menu sheet). Issues I found by hand: one Major, two Minor.

| # | Issue | Criterion | Severity | Fix |
|---|---|---|---|---|
| 1 | "49" is described by the sentence for "2", so a screen reader hears the wrong description | 1.3.1, 4.1.2 | Major | Blocking item 1 |
| 2 | After pressing "2", focus lands on the count line, but a sighted keyboard user must scroll past three rows to find what is marked | 2.4.3 | Minor | Blocking item 2 |
| 3 | "49 of 65" is a 49 by 20 px target in a 20 px line | 2.5.8 (inline exemption holds, DESIGN.md's own 24 px line does not) | Minor | 24 px line box |

Contrast, computed from the hex values:

| Element | Foreground | Background | Ratio | Needs | Pass |
|---|---|---|---|---|---|
| Finding | `#012740` | `#ffffff` | 15.38 | 4.5 | Yes |
| Check line, held button | `#4b5e71` | `#e7edf3` | 5.67 | 4.5 | Yes |
| Labels, stamp, captions on the frame | `#4b5e71` | `#f5f7f9` | 6.23 | 4.5 | Yes |
| Secondary text in a marked row | `#4b5e71` | `#e9f7fd` | 6.11 | 4.5 | Yes |
| Chart labels | `#666666` | `#ffffff` | 5.74 | 4.5 | Yes |
| "How was that checked?" | `#004370` | `#e7edf3` | 8.74 | 4.5 | Yes |
| Current sidebar item | `#012740` | `#e9f7fd` | 14.05 | 4.5 | Yes |
| Focus ring on the check block | `#b6490c` | `#e7edf3` | 4.51 | 3 | Yes |
| Focus ring on the current item | `#b6490c` | `#e9f7fd` | 4.86 | 3 | Yes |
| Focus ring on the bar | `#f5926c` | `#002244` | 7.02 | 3 | Yes |
| Opened dot's ring | `#0071bc` | `#ffffff` | 5.14 | 3 | Yes |
| Panel edge | `#dae3eb` | `#f5f7f9` | 1.21 | none (decorative) | n/a |

The panel edge is decorative under 1.4.11 (https://www.w3.org/TR/WCAG22/#non-text-contrast) because a panel is not a control; the white fill and the zone name carry the grouping.

Keyboard (`r3-probe.cjs`): the skip link comes first, then the wordmark, the scope chip's remove button (24 by 24), the box, the view switch, the sidebar, the breadcrumb, the side panel, then the finding's numbers. Focus on "49" shows its tooltip within 30 ms; Escape closes it. Every focus ring measured is 2 px solid in `focus`, or `focus-on-dark` on the bar. Rail items show their label on hover and on focus (`r3/sheet-shell.png`). The Menu sheet at 390 px moves focus to the current item (`r3/menu-390-open.png`). Under emulated reduced motion the tooltip, window, drawer, buttons and Menu sheet all measure a 0 s transition.

## Motion review

Against `emil-skills/review-animations.SKILL.md`, from the prototype's CSS (`prototype.src.html` lines 194 to 276 and 566 to 645).

| Before | After | Why |
|---|---|---|
| `.btn` press and release both 120 ms on `transform` | Keep the press at 120 ms; let the release snap (80 ms or none) | Standard 9 asks for asymmetric timing on a press and release; minor |
| Reduced motion: every transition `none` | Keep as is, and name it as a deliberate deviation in `design-md.md` block 1 | Standard 8 prefers keeping opacity under reduced motion; DESIGN.md section 10 says "none", and plan 5.7 explains the choice |
| Drawer "over" with `0 5px 25px rgba(160,158,143,.25)` | A stronger left edge (the 1 px `line` plus the shadow) if the user picks "over" | At 1440 px the over drawer reads like the beside one (`r3/package-1440-drawer-dot-over.png`); only matters if "over" wins |

Verdict by tier:

1. Feel-breaking: none. Nothing uses `ease-in` or `scale(0)`; tooltips and windows grow from 0.97 at their trigger's corner.
2. Missed simplifications: none. The sidebar width no longer animates; route changes, rows and numbers never move.
3. Performance: only `opacity`, `scale`, `translate` and `transform` move.
4. Interruptibility: transitions with `@starting-style`, not keyframes; closes are instant.
5. Origin and cohesion: the tooltip's origin follows the side touching its number; the Menu sheet leaves the way it came, 200 ms in and 120 ms out.
6. Accessibility: hover rules sit inside `(hover: hover) and (pointer: fine)` (line 600); reduced motion stops everything.

Decision: passes, with the two minor rows above.

## Worst-case data

### What broke

| # | Severity | Field | Worst-case value | What happens | Fix |
|---|---|---|---|---|---|
| 1 | Broken | Plan check Process status and Review head at 1024 px | "Pending Implementation", "Review" | Broken inside the word | Blocking item 5 |
| 2 | Broken | Package page finding | Fewer than 20 comparable packages | Not drawn; no rule for what takes the finding style | Blocking item 7 |
| 3 | Fragile | Plan check, package page, All projects, a draft | Zero signals, no match, an error | `data=empty` does not change them | Blocking item 7 |
| 4 | Ugly | Start here header | Name, tag and Remove | The tag floats mid-row | Polish |

### Decisions for the lead

- On Lessons' first visit and Home's first run, does a status sentence take the finding style? I would use `lead`, so the light 28 px line always holds a finding.
- When a count is pressed, filter the table to the marked rows or sort them first? I would filter, with "Show all 49" one press away, because the reader asked about those rows.

### What held up

The 257-character description, the 35-character reference with spaces, the 104-character and all-capitals project names, the 54-character agency name in the sticky head, 232,524,000.00, "One draft." and "Showing 1 package or plan" (no "1 packages"), and no sideways scroll at 320 px on any page.

## The fairshare patterns against Prism's rules

| Pattern | Every number from a tool at its rounding | Every claim cited | Strings only in the copy file | Verdict |
|---|---|---|---|---|
| 1. The number that explains itself | Yes, except the open question in item 6 | The From line names the record set and its date | New `num.from.*` keys are listed in 8.6 | Keeps the rules; fix items 1 and 4 |
| 2. Click a number, land on its rows | The rows are the tool's own | Yes | Needs one new count-line key for item 2 | Keeps the rules; misses its point (item 2) |
| 3. "How was that checked?" | The verifier's counts | n/a | The draft variant and the draft ID label are missing (item 3) | Keeps the rules; contradicts on a draft |
| 4. Removed sentence in view | Removed text has no Num and no marker | Its reason is shown | `copy.ts` | Keeps the rules |
| 5. Tooltip promises only what the click does | n/a | n/a | n/a | Broken for dots (item 4) |
| 6. Briefing folds to a strip | Repeats the server's first sentence | Its count word still opens its window | New keys listed | Keeps the rules |
| 7. Worth knowing, one verb each | check_plan's values | Each line ends in its marker | Middle-dot title split into name and tag | Keeps the rules |
| 8. Loading as shape | No number while loading | n/a | n/a | Keeps the rules (`r3/package-1440-loading.png`) |
| 9. The decided bar | The date is the server's | n/a | `draft.tab.checkedYou`, by role | Keeps the rules |

Left out, rightly: the typing effect, the seconds counter and timed hints (a duration on screen would be a number no tool returned, plan 9.3), sliding views and staggered rows.

## Generic defaults

Checked against the calibration list (`frontend-design/SKILL.md` lines 38 to 45) in the plan, the tokens and every capture.

- Cream and serif with a clay accent: no. The page is `#f5f7f9`, the face is Open Sans.
- Near-black with one acid accent: no.
- Broadsheet hairlines with zero radius: no. Stage labels sit over a hairline rule, which the plan grounds in the World Bank's Procurement Framework page; panels keep 8 px corners.
- The SaaS card kit: no. Panels and rows differ by role, no shadow under panels, no gradient.
- Template chrome: no arrows appended to links (0 in the source), no middle dots (0 in the source), no `text-transform` in the source. Uppercase appears only inside charts, set at render from sentence-case copy (`prototype.src.html` lines 1914, 1937, 1965), as the World Bank chart guide sets chart labels (https://worldbank.github.io/data-visualization-style-guide/chartelements). Roboto Mono is for IDs only, as worldbank.org's `--fixed-font-family` (DESIGN.md section 3). `#111111` appears only as the chart guide's chart text (DESIGN.md section 2). Each is pinned by the brief, not a default.

## Build risk by ticket

| Ticket | Night-sized? | Why |
|---|---|---|
| Tokens, type, space, shape, motion | No | Tokens, fonts and lint are a night; the class sweep across every page is another, and it collides with tonight's functional merges |
| Sidebar and rail | Tight | Eight specs, 22 gallery shots and a boot-paint script |
| Top bar | Yes | Seven specs, mostly geometry |
| Page frame | Yes | Five criteria, all measurable |
| Workspace parts | Yes | Gallery only; no page moves |
| Home | Yes | One page, one recording |
| Projects | Tight | Two pages, and the project page has no drawing yet (needs the brief) |
| Packages and plan check | Tight | Fix item 5 first, or the builder copies the six-column breakpoint |
| Package workspace | No | Nine specs; item 7's states are not drawn |
| Lessons | Yes | |
| Drafts | Yes | |
| Data | No | A route removal, a component move, two refusal notes, container queries and seven specs |
| Citation chain | No | Eight components, a new gate test across four pages, seven specs |

## Polish

- Rule 12 and 13 strings from `copy.ts` that now render larger (Copy evidence above), for ticket 58.
- "One needs a look and two are worth watching; three have data notes." could read "One activity needs a look ...", for ticket 58.
- Give 1.5 in the finding a What sentence ("The plan's months from notice to signed contract.") before its From line.
- Open a finding number's tooltip under the whole finding, so it does not cover the sentence being read.
- Start here's tag under its name at every width.
- A 24 px line box for caption lines that hold a number.
- Draw the agency officer's Home and the public view's Projects before those tickets, since the user's principle names "to whom".
- Use `lead`, not the finding style, for first-visit and first-run status sentences.
- The release of a pressed button can snap.
- If the user picks "over", give the drawer a visible left edge.
- Below the side panel on the package page, about 2,000 px of the right column is empty grey at 1440 px; if item 9 is answered with "room for the chart", that is where it comes from.

## Compared with the current app

The redesign is better on every page it draws. The current app puts five tabs and the view pill in the bar and the box in a white band (`current/packages-1440.png`); the redesign moves the tabs to a sidebar and the box into the bar, which gives the page back the band's height. The plan check's finding becomes the largest line on the page instead of a bold 18 px line. Middle dots in column heads and drawer titles are gone. The two blockers that matter most, items 1 and 2, are not regressions from today: they appear because the redesign rightly makes those numbers do more.
