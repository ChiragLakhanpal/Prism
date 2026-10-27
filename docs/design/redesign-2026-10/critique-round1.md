# Critique of the shell redesign

Written October 26, 2026 by the independent design critic. I share no context with the design lead. I judged what renders in `prototype.html`, and I read `plan.md`, `design-md.md`, `tickets.md` and `open.md` for intent and build risk. I changed nothing in the lead's folder or the repo.

## What I looked at

My own captures, all in `/tmp/scratchpad/redesign/critique/`:

- `proto-1440.png`, `proto-1024.png`, `proto-390.png` (first screens, as asked)
- `proto-1440-full.png`, `proto-1280-full.png`, `proto-390-full.png` (whole page)
- `proto-1440-drawer-dot.png`, `proto-1440-drawer-plan.png`, `proto-1024-drawer-dot.png`, `proto-390-drawer-dot.png` (drawer open)
- `proto-1440-rail.png`, `proto-390-menu.png`, `proto-1440-loading.png` (rail, Menu sheet, loading)
- `zoom-dot-opened.png`, `zoom-1280-chart.png`, `zoom-current-1024-chart.png` (close-ups)
- `measure.cjs` and `axe-check.cjs`, the two probes I ran with the repo's Playwright

For comparison, I used the current app's screenshots in `/tmp/scratchpad/redesign/current/`.

Measurements from `measure.cjs` (the top of the finding and the chart's width):

| Window | Finding's top | Chart width | Current app's chart |
|---|---|---|---|
| 1440 x 900 | 377 px | 563 px | about 820 px |
| 1280 x 800 | 401 px | 470 px | |
| 1024 x 768 | 433 px | 423 px | about 813 px |
| 390 x 844 | 932 px (below the first screen) | 324 px | |

axe with WCAG 2.2 AA tags found no violation in six states: 1440 and 390 px, each with the page alone, the drawer open, and the rail (1440) or the Menu sheet (390).

## First impression

At 1440 px the redesign is a real step up from the current app. The tabs left the navy bar for a calm grey sidebar. The bar now carries the box. The finding "2 of 49 comparable packages, fewer than 1 in 10, were signed within the plan's 1.5 months." is the largest type on the page, where today "1 · How long it took" outranks it. The plan row's facts sit in their own panel, and every evidence block ends in a grey strip with its note and source. The eye goes from the bar to the h1 to the finding, which is the right order.

The biggest opportunity is that the result holds at 1440 px only. At 1024 px the chart is about half as wide as today's. At 390 px the finding falls below the first screen. Below zone 1, four zones look like the same white card. The prototype also draws one page out of the nine that the tickets rebuild.

## Scores

From 1 to 5, where 5 is best. For build risk, 5 means low risk.

| Line | Score | Short reason |
|---|---|---|
| Hierarchy | 3 | The finding leads at 1440 px, starts late at 1024 px and falls below the first screen at 390 px |
| Distinctiveness | 3 | One specific bold move (the light finding). The rest is a stock sidebar app with identical zone cards and middle-dot labels in the drawer |
| Fit to the World Bank language | 4 | Navy only in the logo's bar, worldbank.org's blues, Open Sans, the light cut from the 2016 guide, a source line on every block |
| Task flow | 3 | Only the package workspace is drawn. The plan check, Packages, Lessons, Drafts, Data and Home are prose only |
| Progressive disclosure | 4 | Closed zones with a summary, the foot strip, "Show the table", sub-items only under the current section |
| Accessibility | 4 | No axe violation. Focus is visible on the bar and in the sheet. Two standalone links are 20 px tall |
| Copy | 4 | Plain and in Strata's voice. The drawer keeps its eyebrow and middle-dot strings |
| Build risk | 2 | DESIGN.md lands before the build, the frame ticket can't pass its own criteria, Task zone is built after two tickets that use it, the deck is missing from the token sweep |

## Evidence for each score below 4

### Hierarchy, 3

- At 390 x 844 the finding starts at 932 px, below the first screen (`proto-390-full.png`). The first screen holds a two-row navy bar (about 130 px), the breadcrumb, a three-line h1, the STEP reference, the purpose sentence and the whole "From the plan row" panel. The cause is in `design-md.md`'s Side panel row, which says "Below a frame of 60rem it is the first panel after the page head". This breaks the plan's own first principle, "The answer leads".
- At 1024 x 768 the finding starts at 433 px (`proto-1024.png`). Above it, KE-NWWDA-541055-CW-RFB appears three times: in the box's chip, in the breadcrumb's last crumb (wrapped onto its own line) and under the h1.
- In the sidebar, Start here's numbered list (1 to 6) sits beside the zones' numbers (1 to 5). Both use the same muted digits, so two different sequences share one screen (`proto-1440.png`).
- At 1440 px it works: h1 at 116 px, finding at 377 px, and the finding is the largest type.

### Distinctiveness, 3

The one bold move is specific to this subject. The finding is set in Open Sans Light, after the 2016 guide's light openers ([WBG Branding and Visual Identity Guidelines, February 2016](https://thedocs.worldbank.org/en/doc/723361567518322252-0060022019/original/WBGBrandingandVisualIdentityGuidelinesFebruary2016.pdf), pages 20 to 22). The foot strip and the PPSD section tags are the subject's own devices too. The rest falls back on defaults from the frontend-design skill's calibration list:

- Item 4, the card kit. In `proto-1440-full.png`, zones 2 to 5 are four white cards with 8 px corners on grey, 85 to 190 px tall, and they differ only in their text. Zone 4 has nothing to open, yet it looks the same as zone 2, which does. The plan says open and closed zones "look different by their content, not by decoration". On screen, that means they look the same.
- Item 5, template chrome. The drawer still opens on "What · record" over the reference, then "Water and Sanitation Development Project (P156634) · Kenya", then a "What" eyebrow above "Specific procurement notice" (`proto-1440-drawer-dot.png`). These strings come from today's copy file (`web/src/copy.ts` lines 1000 and 1238), but the plan's no-eyebrow rule stops at the package sections.

### Task flow, 3

- `prototype.html` draws one page, the package workspace. Nine of the eleven tickets rebuild pages that exist only as prose in plan section 8.4. Among them is the wide layout, which the lists, the plan check and Data use and the prototype never shows. The user's own note says "the prototype is what they judge in the morning" (`../user-additions.md`, item 4).
- The plan check is Start here's first example, and the plan calls it "the Packages flow's second step". Its route is `/projects/:pid/procurement/:agencyId`, and today it lights Projects (`current/first-screen/plan-check-nwwda-1440-first.png`). No ticket says which sidebar item is current there. So a person who presses "Check a plan" under Packages may land on a page where Projects is lit.
- The journey this tool exists for is never drawn end to end. It runs from a plan check row to the package, then to "Suggest n PPSD risk rows", then to the draft.

### Build risk, 2

- **DESIGN.md lands ahead of the build.** The tokens ticket pastes sections 1, 4 and 10 of `design-md.md` into DESIGN.md. These carry principle 7 (the sidebar and the side panel), the Page layouts row that replaces the Document column, the Shell row and the shell's accessibility bullets, and none of those things exist yet. Meanwhile polish tickets 56 to 63 read DESIGN.md as the rule for today's screens. No ticket says who pastes section 5's Top bar, Sidebar, Menu sheet, Page head, Task zone, Foot strip, Stage label or Side panel rows.
- **The frame ticket can't pass its own criteria.** Its first two checks open the drawer on "the package workspace and a draft" and measure "a workspace page". But those pages move onto the workspace layout only in the package and Drafts tickets, which come after the frame.
- **The frame ticket is more than a night.** It sets window-based margins and adds a `frame` container. It builds two layouts, drawer sizing for each, the Side panel and the Page head, and restyles the breadcrumb. It merges two scroll-padding hooks, sets `main`'s minimum height, moves the answer panel and edits six specs.
- **Task zone comes after its users.** The package workspace ticket builds the Task zone, Foot strip and Stage label. The Lessons and Data tickets use zones but are blocked only by the frame ticket, so they can run first, or in parallel, with no Task zone to use.
- **The sidebar ticket needs the boot paint.** It must read the open-or-rail choice "before the first paint". But `web/index.html` paints only the bar and the band today, and the bar ticket that follows is the one that rewrites `index.html`. Until then the page shifts right when the sidebar mounts, and the first-paint test in `shell.spec.ts` (line 63) no longer matches.
- **The token sweep misses the deck.** It is large: `text-title` appears 141 times in 60 files, `uppercase` 32 times in 24 files, and `rounded-pill` or `rounded-full` 77 times. The new lint rule refuses `uppercase` outside chart components, which would hit the slide eyebrows in `web/src/deck/Deck.tsx` (lines 204 and 440). `slides.tsx` uses `text-title` five times. The ticket names neither `deck.spec.ts` nor the /present captures.

What the tickets do well: each one keeps its page's function, names its specs and gallery states, and lists the ticket 56 to 63 items it settles. Every spec and source file they name exists in the repo.

## What must change before tickets are opened

Each item names its fix and the part of the user's brief it serves.

1. **Draw the wide layout before the page tickets open.** Brief: panels as sequential task zones, easier for the user. Add the plan check to `prototype.html` at 1440 and 390 px: its sticky head with "Draft review notes", its finding, its marked rows and the drawer open on a row. Add Lessons or the Drafts list too, with the sidebar's sub-items showing. Use the same tokens. The tokens, sidebar, bar and frame tickets can open now. The seven page tickets wait for the drawing.

2. **Put the finding in the first screen at every width.** Brief: a real type hierarchy, progressive disclosure. Below a frame of 60rem, fold "From the plan row" into one caption line under the h1 ("Request for Bids, Open - National, Post, 1,230,000.00 US$" in STEP's words) with a "Show the plan row" disclosure, instead of a full panel before zone 1. Show the STEP reference once in the head. The box's chip already names it, so drop it from the breadcrumb's last crumb. Change `design-md.md`'s Side panel row to match. Add a criterion to the package workspace ticket: the finding's top is inside the first screen at 390 x 844 and 1024 x 768.

3. **Keep the chart wide.** Brief: easier for the user, a rail for the tabs. The workspace layout cuts the past range from about 813 px to 423 px at 1024, and to 470 px at 1280. At 1280 px the middle half of the signed packages (3.3 to 7.9 months) fits in about 115 px, with dots stacked seven high, and every dot opens the drawer (`zoom-1280-chart.png`). The fix is to apply the workspace layout only from a frame of 75rem. Below that, the work takes all 12 columns and the drawer narrows the page as it does today. Also make the rail the default below 1440 px, so a 1280 px laptop gets the 1440 layout (a 649 px work column). The user asked for a "rail sort of a thing", and the toggle still wins. The package workspace ticket then measures the chart's width at 1280 and 1024 px.

4. **Each ticket lands its own DESIGN.md rows.** Brief: the World Bank language, which DESIGN.md records ("A deviation needs a line here first"). The tokens ticket takes sections 2 (the new pairs) and 3, section 4's Space, Radius and Elevation rows, and section 5's Buttons and Cards. The sidebar ticket takes Sidebar, Menu sheet, Tabs and the shell's section 10 bullet. The bar ticket takes Top bar, Scope chip and Freshness stamp. The frame ticket takes Grid, Breakpoints, Shell, Page layouts, Page head, Side panel, Evidence drawer, Answer panel and the sticky-parts bullet. The package workspace ticket takes Task zone, Foot strip, Stage label, Collapsed section, Package header and principles 6 and 7. Home, Projects and Packages each take their own rows.

5. **Fix the order, and make the frame two tickets.** Brief: panels as task zones, with one zone component for every tab. The frame ticket becomes two. (a) is the frame: window margins, the `frame` container, the wide layout, a drawer that never moves the page, one scroll-padding hook and `main`'s minimum height. (b) is the workspace: the layout, Side panel, Page head, Task zone, Foot strip and Stage label, proven on gallery states rather than on the package or a draft. Block Home, the package workspace, Lessons, Drafts and Data on (b). Move the sidebar's boot paint (an inline read of the stored choice and a painted sidebar frame) and its first-paint test into the sidebar ticket.

6. **Name the deck in the token sweep.** Brief: a real type hierarchy that keeps every page working. Either keep `web/src/deck/` out of the sweep and the uppercase lint, since slides follow DESIGN.md's slide frame rules, or bring it in and add `deck.spec.ts` and the /present captures to the ticket's specs. Whichever you pick, write it in the ticket.

## The one change that would most raise the craft

Draw a panel only around open evidence. A closed zone, or one with only a summary (zones 2, 4 and 5 here, and zone 3 while it is empty), becomes a row on the page grey with its number, name, summary and "Show" button, and a 1 px line under it. Only an open zone with evidence gets the white panel with 8 px corners and the foot strip. That makes the plan's principle 7 literal ("the frame is grey, the work is white"). Open and closed zones then differ in form as well as in content. The stack below zone 1 reads as the steps of a PPSD worksheet instead of four matching cards, and a reader can scan the whole sequence in one screen. It costs one variant in the Task zone component.

## Polish

These can follow the tickets and need no change to the plan's structure.

- In the prototype, give the opened dot the 2 px ring that DESIGN.md already asks for ("the opened dot keeps a 2px `selection1` ring"). Today no dot is marked while the drawer shows its record (`zoom-dot-opened.png`), so the panel can't see which dot is open.
- Extend the no-eyebrow rule to the drawer: "What · record", "· Kenya" and the "What" label above a card title. This is copy, so it belongs to ticket 58.
- Start here: drop the numbers, or fold the group to one row ("Start here, 6 examples") after the first visit, so it stops competing with the zones' numbers. This sits with `open.md` item 5.
- Side panel: six facts with each label over its value make a panel about 500 px tall at 1440 px. Use two columns of facts from a panel width of 320 px, as the 390 px layout already does.
- The stage labels "Planning" and "Tender design" (13 px, 600, muted) almost vanish. Give each a 1 px line to its right, so a change of stage reads at a glance.
- The stamp link in the sidebar's foot and the breadcrumb links are 20 px tall and not inside a sentence. DESIGN.md section 10 asks for 24 px ([WCAG 2.2, 2.5.8 Target Size (Minimum)](https://www.w3.org/TR/WCAG22/#target-size-minimum)). Give them a 24 px line box.
- The sidebar ticket should name the current item on cross-section pages. One rule: the item named by the breadcrumb's first crumb, so the plan check reached from Packages lights Packages.
- `design-md.md`'s Page head row says the line under the h1 is "either the purpose or an object's ID". Its Package header row, and the prototype, show both. Make the two rows agree.
- Buttons with 4 px corners depart from worldbank.org's button token, which the lead's study reads as a pill (`--loop-button-border-radius`, in [components-variable.css](https://www.worldbank.org/ext/styles/components-variable.css)). Mark the Buttons bullet "Strata", not "WB", and give the reason.
- Test Open Sans Light at 28 px on the demo laptop before the tokens ticket merges (`open.md` item 10).
- "Advertised again" answers a different question from "How long it took". Consider giving it its own zone, with the Experimental badge in that zone's header.
- The seven page tickets all edit `web/src/copy.ts`, `web/capture/shots.ts` and the sidebar's sub-item slot. Run them in two waves rather than seven at once, to cut merge conflicts.
- The "TIME ESTIMATE FOR THIS PACKAGE" lane label holds a full abstention sentence, so it reads as a section heading. Keep the lane label, and set the abstention under the chart in `body`.
