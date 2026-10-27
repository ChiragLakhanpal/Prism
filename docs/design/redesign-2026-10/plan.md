# Strata's shell redesign: the design plan

Written October 26 and 27, 2026 by the design lead, for the user to judge on the morning of October 27. This is round 3, finished after the second critic's review (`../critique/round3.md`, October 27, 2026 at 1:12 AM). Round 2's files are kept in `round2/`, and round 3's first pass, the one that critic judged, in `round3-first/`. The build is `prototype.html` in this folder; the DESIGN.md text is `design-md.md`, the ticket drafts are `tickets.md`, the calls that stay with the user are in `open.md`, and `morning.md` is the note to read first.

The plan changes no number, claim, tool contract or route contract, with one exception the user asked for: the address `/data/how-strata-works` stops being a page (section 8.4). It rests on the studies in the folder above this one: `notes.md` (the current app, screenshots in `current/`), `wb-language/world-bank-design-language-notes.md`, `references/reference-apps.md`, `fairshare/notes.md` (the user's earlier app) and the skills in `emil-skills/`. A fact the studies did not have is named as missing in section 12, not filled in.

## 0. What changed in round 3 and why

Round 3 ran in two passes. The first pass folded in the user's additions and the four new inputs (0.2). The second critic then judged that pass and asked for nine changes before the tickets open, and eleven smaller ones (`../critique/round3.md`). Section 0.1 answers each of them. The second critic's one change was "make the number chain land exactly", and it is the first thing to try in the morning: hover 49, then 2, on the package page; press 2; press "How was that checked?" on a draft.

### 0.1 The second critic's review, answered

Blocking points, each fixed in the files, not only here.

| # | The critic's point | What I changed | Where |
|---|---|---|---|
| 1 | "49" carried the tooltip of "2", so a screen reader heard the same description twice | Every number has its own What sentence. 2: "Comparable packages signed within 1.5 months of their notice." 49: "All comparable packages in the past range, including the four still open." 1.5, 3.3 and 7.9, 4.4 and 9.1 each have their own, and the Kaplan-Meier sentence is gone. The number tooltip ticket now asks that no two numbers in one sentence share a What sentence unless they come from the same record and open the same thing | Prototype; plan 10; design-md block 13a; the number tooltip ticket |
| 2 | Pressing "2" landed on three unmarked rows | A pressed number filters the past range's table to the rows it counts. The count line repeats the pressed number ("Showing the 2 of 49 packages signed within 1.5 months.") and "Show all 49" sits after it, and the page scrolls the table's title under the bar. The first marked row's top is at 134 px at 1440 by 900 and 118 px at 390 by 844 (`work/shoot4.cjs`). I chose filtering over sorting first, as the critic would, because the reader asked about those rows. The count line never counts rows itself | Prototype; plan 7.4 and 9.1; design-md block 9; the package ticket's third criterion |
| 3 | The draft's "How I checked this draft" window disagreed with its check line and its Sources | The window opens on "These counts include the two sentences I removed. The check line counts only the sentences I kept." when the verifier removed any, step 2 reads "came back for this draft", and the keys are in 8.6 with "Draft ID {id}, run {run}" | Prototype; plan 8.6 and 9.1; design-md block 13b; the check window ticket |
| 4 | A dot's tooltip had no source line and no action line | It has all three parts now: the reference and months, "Kenya. Its notice was published September 17, 2021, and its contract was signed January 3, 2022.", the From line and "Select to see its records." Dots are named in the gate test | Prototype; design-md block 13a; the number tooltip ticket |
| 5 | The plan check broke "Review" and "Implementation" inside the word at 1024 px | The table draws six columns only from a page area of 60rem, so at 1024 px with the rail (56rem) it draws three. A scan of every page at five widths in all four data states finds no word broken inside itself (`work/words4.cjs`, `work/words-twin.cjs`); the past range's open table needed its Months column widened for the same reason. The Packages ticket now asks for that scan at 1024, 1280 and 1440 px | Prototype; the Packages ticket |
| 6 | Home's "1.23" tooltip showed 1,230,000.00, which block 13's Don't column forbade | DESIGN.md's own Signal line row already says a rounded amount's popover gives the record's exact Estimated Amount, so that rule wins: block 13a now allows the record's own unrounded value behind a rounded number, and nothing else the page does not show | Design-md block 13a; plan 9.1 pattern 1 |
| 7 | Four pages had no empty, few or error state, and no rule said what takes the finding when Strata holds back | The Data switch now has Empty or few and Error. Empty draws a staff plan check with no signals (no fixture has one, so the copy file's finding sits over the fixture's three data-note rows, and the page says so), All projects with no match ("atlantis", `projects-no-match.json`), and the package compared with prior-review packages only (seven comparables, `comparables-ke-nwwda-541055-prior.json`), where the first-person "I'm not giving a range: only seven comparable packages. Here are all seven." takes the finding style, the count follows in `body`, the chart keeps its dots and plan line, and the table opens with the page. Error draws every page's failure in the copy file's own words with "Try again": in the alert slot for a page that failed, in the zone for a block that failed. A draft has no empty state and says so | Prototype; plan 8.5; design-md blocks 5, 8 and 9 |
| 8 | The tickets ran eight serial layers deep, five were bigger than a night, none said what it costs the gate, and the tokens ticket's sweep would collide with tonight's merges | Sixteen tickets now. Tokens split into "tokens, fonts and lint" (can start now; it edits only app.css, the lint, the fonts and four components) and "the class sweep" (after the functional tickets merge). Data split into "How Strata works leaves, with the refusal window" and "Data lays out by the page area". The citation chain split into "the number tooltip with its gate test", which now waits only for the class sweep, and "the check window with the drawer's motion". The class sweep leaves the files the shell tickets rewrite. Every ticket has a "Gate seconds added" line. Together they add about 7 seconds and take back about 3, so about 4 net, which is all the headroom the gate has: it ran 121.9 to 145.4 seconds against its 150-second cap (`docs/STATUS.md` line 577). So the orchestrator times the gate after each merge, and a ticket that would push it past 145 seconds waits for ticket 56's cuts. The longest chain is still eight tickets, because the shell lands in order, but the class sweep, the number tooltip and How Strata works leaving now run beside the shell instead of after it | `tickets.md`, its build order table |
| 9 | Distinctiveness scored 3: record that World Bank fit outranks a stronger identity, or give the chart more room | Recorded in section 6: World Bank fit and the drawer's place outrank a wider chart. The grey beside the chart at 1440 px is where the evidence drawer opens, so a dot and its records share one screen; a chart in that space would be covered or would move when the drawer opens. The chart is 810 px at 1024 px with the rail, and the user can try the Icons rail (647 px at 1440 px) | Plan 6 |

Polish, all taken.

| # | The critic's point | What I changed |
|---|---|---|
| 1 | Copy-file strings that break rules 12 and 13 now render larger | "Show the three packages and their reasons", "None of the three projects", the dot tooltip's full dates, and no "Kaplan-Meier" in a tooltip. Listed for ticket 58 in 8.6 and section 14 |
| 2 | "One needs a look ..." drops its noun | "One activity needs a look and two are worth watching; three have data notes.", for ticket 58 |
| 3 | 1.5 had no What sentence | "The plan's months from notice to signed contract.", then its From line |
| 4 | A number's tooltip inside a three-line finding covered the sentence | A number inside the finding opens its tooltip under the whole finding, left aligned with the number |
| 5 | Start here's tag floated beside its name | The tag sits under the name at every width, since Remove holds the right |
| 6 | "49 of 65" sat in a 20 px line | A caption line that holds a checkable number is 24 px tall |
| 7 | Draw the officer's Home and the public view's Projects | The view switch now works in the prototype. The agency officer's Home is drawn from `home-preview-piu.json`, the public Home from `home-preview-public.json`, the public view's sidebar and All projects, its plan check (signals held back, `check-plan-...-public.json`, lit as Projects with its breadcrumb at the project), and its hidden pages ("This page isn't part of the public view.") |
| 8 | Use `lead` for first-visit and first-run status sentences | Done on Lessons and Home; the finding style holds a finding or Strata holding back, never a status sentence (design-md principle 6) |
| 9 | The view switch opened nothing | Its popover is drawn: "See Strata as" with the three views as link rows, the current one marked, and "See Strata as of a past date" |
| 10 | A pressed button's release can snap; name reduced motion's "none" as a deviation | The press takes 120 ms and the release is instant. Design-md block 1 names "none" as a deliberate departure from review-animations standard 8 |
| 11 | "Over" needs a visible left edge | The over drawer has a `line-strong` left edge with the popover shadow |

Looking at the new screenshots changed six more things (section 13 lists them). The two a reader would feel: after a press scrolls the page, a number that slid under the resting pointer opened its tooltip, so a number tooltip now waits for the pointer to move after any scroll, as DESIGN.md's evidence card already waits for the pointer to leave and come back; and the officer's P-code outweighed the light finding around it, so an ID inside the finding takes Roboto Mono 400.

### 0.2 The first pass

The user added three things while round 2 ran (`../user-additions.md`), and the orchestrator added four inputs: the fairshare study, Emil Kowalski's design engineering skills, the design plugin's skills and the deck's fixed colors. Each change below names its input.

| What changed | Why | Where |
|---|---|---|
| A page-by-page table of what to show, where, and to whom | The user's principle: "what to show where to who; not blast them with info but have the information right where they logically need it ... and make it delightful" (`../user-additions.md`, item 2) | 8.0; principle 8 in 7.1 |
| How Strata works leaves Data. Each refusal now gives its own reason in place, and "Everything I turn down" opens a window under the answer. The old address goes to Data readiness | The user: the deck at /present covers it, "and it makes no sense under Data" (`../user-additions.md`, item 1) | 8.4 Data; the refusal window ticket |
| Nine patterns from fairshare are adopted: five in the citation chain's two tickets, the rest folded into the Home, Drafts and package tickets. Two are left for later and the "not to carry over" list is kept | The user asked to borrow fairshare's patterns, not its palette or subject (`../user-additions.md`, item 3; `../fairshare/notes.md` section 7) | 9; the last ticket |
| Motion rules: what moves in Strata and what never does, two easing curves, durations by purpose, transitions over keyframes, nothing under reduced motion. The sidebar no longer animates its width | Emil Kowalski's decision framework (`../emil-skills/emil-design-eng.SKILL.md` lines 62 to 145) and DESIGN.md section 10 ("Motion 120 to 200ms") | 5.7; design-md block 1 |
| The number tooltip and the evidence pane are written as components with variants, states and accessibility notes | The design-system skill's form, and the tooltip and popover rules in Emil's skill (lines 234 to 345) | 10; design-md blocks 13a and 13b |
| Worst-case data: which strings wrap, which never break, and the one rule that forbids clamping source text | `../emil-skills/break-ui.SKILL.md` lines 117 to 125, against DESIGN.md section 3 ("No container that holds writer or source text has a fixed height or a line clamp") | 7.10; the prototype's Data switch |
| The prototype now draws eight pages: Home, Packages, the plan check, the package workspace, All projects, Lessons, Drafts and a draft's page, plus an answer on Home. It has three switches: the rail at rest, the evidence pane's placement, and real, longest or empty data | The user judges the prototype in the morning (`../user-additions.md`, item 4); `../emil-skills/prototype.SKILL.md` line 65 on switching variants | 13 |
| The past range in the prototype now uses the 49 real packages from the test fixture, not dots traced by eye | Every fact in the prototype should be a real fixture fact | 13 |
| The deck keeps its own branch. The token sweep and the uppercase lint leave `web/src/deck/` alone, two old tokens stay as aliases until the deck branch moves its last uses, and the exact deck lines are listed as that branch's follow-up | The deck session rebuilds /present on `deck/second-draft`; round 2 put the deck inside the sweep, which would collide with that branch | 5.1, 5.3; the tokens ticket's comments |
| Tickets in the order asked: tokens and motion, the shell in four tickets, one or two tickets per tab in the demo's order, then the citation chain (two tickets since the second critic's review, 0.1) | The orchestrator's order; the first critic found a one-ticket frame too big for a night | `tickets.md` |
| `design-md.md` is rewritten in the design-system skill's form: each component with its variants, states and accessibility notes | `design-system/SKILL.md`, "Output, Document" | `design-md.md` |

What did not change: the light finding as the one bold move (section 6), the grey frame with white panels around open work, the bar that carries the box, the sidebar defaults by width, the plan check under Packages, and every round 2 answer to the first critic (0.3).

### 0.3 Round 2: the first critic's points, still answered

The first critic (`../critique/critique.md`) scored hierarchy 3, distinctiveness 3, World Bank fit 4, task flow 3, progressive disclosure 4, accessibility 4, copy 4 and build risk 2. Round 2 answered each point; round 3 keeps every answer.

| Critic's point | Round 2's answer, kept |
|---|---|
| The one change: a panel only around open evidence | A zone is a white panel when it holds open work and a row on the grey otherwise (principle 7) |
| Draw the wide layout before the page tickets | The prototype draws the plan check, Packages, All projects and Lessons; round 3 adds Home, Drafts and a draft's page |
| The finding in the first screen at every width | Below a frame of 75rem the side panel folds into one facts line; the breadcrumb lists parents only |
| Keep the chart wide | The workspace layout starts at a frame of 75rem; the sidebar is a rail by default from 1024 to 1439 px |
| Each ticket lands its own DESIGN.md rows | `design-md.md` is grouped by ticket |
| Fix the order; two frame tickets | The frame and the workspace parts are two tickets; the sidebar ticket owns the boot paint |
| Name the deck in the token sweep | Round 3 changes this answer: the deck is named, and kept out (5.3) |
| Polish 1 to 13 | Kept as round 2 settled them: the opened dot's ring, no eyebrow in the drawer, Start here on Home, two columns of facts, a rule after the stage label, 24 px link boxes, the current item on cross-section pages, one page head rule, 4 px button corners marked Strata, Open Sans Light to test on the demo laptop, "Advertised again" in zone 1, two waves of page tickets, the abstention under the chart |

## 1. Subject, audience and job

- **Subject.** Procurement intelligence on World Bank open data: Procurement Plans and their STEP rows, notices and contracts, project records, and the numbered paragraphs of ISRs, ICRs and IEG reviews.
- **The two people.** A World Bank procurement specialist (the staff view), and a procurement officer at a borrower's implementing agency (the agency officer view). Both read Procurement Plans for a living, know STEP's field names, and work on one plan or one package at a time. The public view (Projects, Lessons, Data) serves anyone else. The first people to see Strata are a World Bank interview panel, who arrive as staff (the blueprint's "The first 60 seconds").
- **Primary job.** Check a plan, plan a package, read a lesson and check a draft. Every number comes from a tool, and every claim cites a record or a numbered paragraph.
- **The subject's own vocabulary.** The plan row, the version date, "Disclosed", the PPSD section, the source line under every World Bank figure, the paragraph mark (¶54).

The brief: the five tabs move into a sidebar that can fold to a rail; a modern type hierarchy; the World Bank's design language; task panels in the order of the work, with detail on demand; structure borrowed from Linear, Vercel, Supabase and Claude as inspiration only. Round 3 adds the user's principle: show each person what they need for the step they are on, keep the rest one click away where they would look for it, and make it pleasant.

## 2. What Strata borrows from the World Bank, and what it leaves

Borrowed:

- **Navy only where the logo is.** `#002244` stays in the one bar that carries the logo. The Loop called it the "brand dark blue used only in main navigation and WB logo" ([The Loop, colors, archived](https://web.archive.org/web/20211019025519/https://theloop.worldbank.org/colors)).
- **The blues and greys of worldbank.org.** Blue-70 `#004370` for action, blue-90 `#012740` for headings, and the pale elevations `#f5f7f9` and `#e7edf3` ([worldbank.org components-variable.css](https://www.worldbank.org/ext/styles/components-variable.css)). These are DESIGN.md's tokens already.
- **Restraint.** The Loop says brand blue is "used sparingly" (same archived page), and the 2016 guide says secondary colors "should not dominate the corporate blues" ([WBG Branding and Visual Identity Guidelines, February 2016, page 18](https://thedocs.worldbank.org/en/doc/723361567518322252-0060022019/original/WBGBrandingandVisualIdentityGuidelinesFebruary2016.pdf)).
- **Open Sans and Roboto Mono**, as worldbank.org sets them in `--global-font-family` and `--fixed-font-family` (same CSS file), with tabular figures for numbers.
- **The light cut for the big sentence.** The 2016 guide names Andes ExtraLight, Regular and Bold as the most used weights and sets its large navy openers in the light cut (pages 20 to 22). Strata does the same with Open Sans Light (300), which is free, for one sentence per page.
- **The document feel.** A source line under every figure, numbered sections where the work is a sequence, a stage label over a hairline rule, and dated documents, as on the [Procurement Framework page](https://www.worldbank.org/en/programs/project-procurement/framework).
- **DataBank's ordered left column** ([DataBank, World Development Indicators](https://databank.worldbank.org/source/world-development-indicators)), the World Bank's own case of a process laid out as ordered steps.
- **The chart rules** of the [Data Visualization Style Guide](https://worldbank.github.io/data-visualization-style-guide/): the finding as the title, direct labels, about five ticks, a dashed grey grid, selection1 `#0071bc` for a selected mark, and uppercase semibold labels inside charts only ([chart elements](https://worldbank.github.io/data-visualization-style-guide/chartelements)).

Left behind: hero banners, uppercase headings with tight tracking, "By the numbers" tiles ([Kenya overview](https://www.worldbank.org/en/country/kenya/overview)); the 32 px pill on every control (a Strata deviation, section 5.6); `#009fda` and `#169af3` as text (3.01:1 and 3.02:1 on white); Andes, a commercial logotype font ([MyFonts, Andes](https://www.myfonts.com/collections/andes-font-latinotype)); bold white tabs on a navy masthead; and anything that would make Strata pass for a World Bank page, which the 2016 guide's "Do Not" list rules out (page 66).

**One family with the deck.** The session that rebuilds /present fixed five colors and one face: navy `#002244`, primary `#004370`, ink-heading `#012740`, page `#f5f7f9`, accent `#0071bc`, and Open Sans. The app uses the same five values under DESIGN.md's names (5.1), so the deck and the app read as one product. The palette departs from them nowhere. Two differences of use, not of value, are written down so the deck can choose: the deck sets whole opener slides in navy, while the app keeps navy to the bar; and the deck calls `#0071bc` "accent" and uses it as its figures' one focal mark, while the app calls it `info-icon` and uses it only for the opened chart mark's ring, the info badge's icon and border, and the Watch badge. Neither needs a change on either side. If the user keeps the deck's navy slides, DESIGN.md's navy rule names them, as the deck session and the orchestrator agreed (`../deck-ticket.md`); in this wave that sentence lands with the bar and frame tickets, so they carry it (design-md blocks 3 and 4).

## 3. The plan, first pass

This is the plan as first written in round 1. Section 4 reviews it against the brief.

- **Color.** The six values in section 5.1, with a white sidebar.
- **Type.** DESIGN.md's scale (h1 28 bold, h2 24 bold, h3 20 bold, title 18 bold) with 600 for card titles; each section's finding in 20 px bold.
- **Shell.** A navy bar with the logo, the wordmark, the box, the stamp and the view switch; a white sidebar under it that collapses to a 64 px icon rail; the selected item a filled blue pill.
- **Pages.** Every section a white card with an uppercase eyebrow and a heading such as "1 · How long it took"; the package's facts in a three-column grid under the h1.
- **Controls.** Pills, as now.

## 4. Review against the brief, and what changed

### 4.1 Round 1

Asked of each part: would I have drawn this for any data app with a sidebar? Where yes, it changed.

1. **Cards with uppercase eyebrows and "1 · Name" headings** became zones with a plain number in a fixed column, because the package workspace's sections are a sequence; the stage shows once where it changes.
2. **The finding in 20 px bold** became Open Sans Light at 28/36, the largest and only light type on the page.
3. **A filled blue pill for the selected item** became Strata's "current" mark: a `tint` fill and a 3 px `primary` bar on the left.
4. **A white sidebar** became `page` grey with a hairline edge, as Linear dimmed its sidebar ([Linear changelog, March 12, 2026](https://linear.app/changelog/2026-03-12-ui-refresh)).
5. **The stamp in the bar** moved to the sidebar's foot under Data (7.2 has the arithmetic).
6. **The facts in a grid under the h1** moved to a side panel at the right, as Linear keeps an issue's properties beside its content ([Linear changelog, July 23, 2026](https://linear.app/changelog/2026-07-23-agent-assisted-editing)).
7. **Pills on controls** became 4 px corners; pills stay for data.
8. **An icon-only rail by default** was rejected in round 1 and made the default from 1024 to 1439 px in round 2 (4.2, item 3), with a tooltip on every icon.

### 4.2 Round 2

1. **Four matching cards under zone 1** became rows on the grey; a panel only around open work.
2. **"What · record" and middle dots in the drawer** became a title and one caption sentence.
3. **Narrow work at laptop widths**: the workspace layout starts at a frame of 75rem.
4. **The finding below the first screen at 390 px**: one facts line and a button that opens the plan row in the drawer.
5. **Start here in the sidebar** went back to Home.
6. **Plan check rows with two links each**: a row opens its records in the drawer, as Linear's triage keeps the focused issue beside the list ([Linear changelog, January 20, 2022](https://linear.app/changelog/2022-01-20-linear-preview-new-sidebar-and-team-icons)).
7. **A table that turns into cards when the drawer opens**: three columns beside the drawer, cards only below a page area of 40rem.

### 4.3 Round 3, after the new inputs

I put the round 2 plan through the frontend-design skill's calibration list again, now with the fairshare stills beside it, and through Emil Kowalski's motion gate. Five things changed.

1. **Two strings still carried template chrome.** Home's panel title is "Worth knowing · fixed checks, no model" and the public view's is "Closed projects · contracts traced from public records" (`web/src/copy.ts`, `home.worth.title` and `home.publicView.title`). That is calibration item 5, meta strings joined with middle dots. **Changed:** each becomes a name and a `caption` tag at the panel's right ("Worth knowing" with "Fixed checks, no model"), the same shape as a zone's PPSD tag. The words are ticket 58's; the shape is the Home ticket's. One middle dot stays on purpose: the access label "Official Use Only · visible to your team", which DESIGN.md section 7, rule 39 fixes word for word as a classification label, with its dot hidden from screen readers.
2. **The sidebar animated its width.** Round 2 grew and shrank it over 160 ms. Width is a layout property, so the page re-lays every frame (`../emil-skills/emil-design-eng.SKILL.md` lines 477 to 481), and a person toggles it often enough that the motion adds wait without telling them anything. **Changed:** the sidebar changes at once.
3. **A number's tooltip said what the number was but not where it came from.** fairshare's tooltip names the column, the row, the query and the table, and ends with what a click does (`../fairshare/notes.md` lines 72 and 77). **Changed:** Strata's number tooltip has three parts: what the number is, where it came from with its date, and what a click does, said only when the click does it (section 10).
4. **The check line said what was checked but not how.** **Changed:** "How was that checked?" after the check line opens a window with the six checks, in the copy file's own words (9, pattern 3).
5. **Home and the drafts were prose.** The principle in 8.0 depends most on Home and on a draft's page, so both are now drawn from recorded fixtures.

What I kept after the review, and why: one bold move (the light finding); no new color; no dark tooltip, because DESIGN.md's Dot tooltip is already a light surface with a hairline and two tooltip looks on one page would read as two systems; and no typing effect, no shimmer and no count-up, which fairshare uses and Strata's rules reject (9.3).

## 5. The token system

### 5.1 Color

No new color token. Six named values carry the shell, all from DESIGN.md section 2. The right column says which of the deck's fixed points each one is.

| Name | Hex | Token | Role in the shell | The deck's name |
|---|---|---|---|---|
| Bar navy | `#002244` | `navy` | The top bar, which carries the logo and the box | navy |
| Heading ink | `#012740` | `ink-heading` | h1, zone names, the finding | ink-heading |
| Action blue | `#004370` | `primary` | Links, the primary button, the current mark's 3 px bar | primary |
| Frame grey | `#f5f7f9` | `page` | The sidebar, the page behind the panels, zone rows, foot strips | page |
| Panel white | `#ffffff` | `surface` | Panels, the side panel, the box, the drawer, tooltips | |
| Hairline | `#dae3eb` | `line` | Panel edges, the line under a zone row, the stage label's rule | |
| Selection blue | `#0071bc` | `info-icon` | The opened chart mark's 2 px ring, the info and Watch badges' icon and border | accent |

State colors, `tint`, `tint-hover`, `surface-2`, `ink`, `ink-muted`, `focus`, `focus-on-dark` and the chart tokens keep their DESIGN.md values and roles.

### 5.2 Typefaces

| Family | Weights | Role | License |
|---|---|---|---|
| Open Sans | 300 | The page's one finding | SIL OFL 1.1, self-hosted (`@fontsource/open-sans/300.css`, in the installed 5.3.0 package) |
| Open Sans | 400, italic 400 | Sentences, table cells, captions | SIL OFL 1.1 |
| Open Sans | 600 | Zone names, labels, buttons, the current sidebar item | SIL OFL 1.1 |
| Open Sans | 700 | The h1 and the wordmark only | SIL OFL 1.1 |
| Roboto Mono | 500 | IDs: P-codes, STEP references | SIL OFL 1.1 |

The deck uses Open Sans too, so the two share the face at every weight they both use.

### 5.3 Type scale

Every size is on worldbank.org's scale (12, 13, 14, 16, 18, 24, 28, 32). Size says how much a line matters; weight says what kind of line it is. Tracking follows the size, as Apple's typography talk asks: tighter on the large light finding, zero on body text, slightly open on the small uppercase chart label (`../emil-skills/apple-design.SKILL.md` line 230).

| Token | Size / line height | Weight | Color | Use |
|---|---|---|---|---|
| `display` | 32 / 40 | 700 | ink-heading | Deck titles only |
| `finding` | 28 / 36; 24 / 32 below a page area of 48rem | 300, -0.01em, balanced lines | ink-heading | The page's one finding |
| `h1` | 24 / 32; 20 / 28 below 48rem | 700 | ink-heading | Page title or object name. It steps down on a phone as the finding does, so the longest real title (257 characters) still leaves the finding in the first screen at 390 by 844 |
| `h2` | 18 / 24 | 600 | ink-heading | A zone's name, a side panel's name, a table named by a noun |
| `h3` | 16 / 24 | 600 | ink-heading | A block inside a zone, a group of facts in the drawer |
| `lead` | 18 / 28 | 400 | ink | A block's own finding, a table's title sentence, an answer's sentences |
| `body` | 16 / 24 | 400 | ink | Sentences, zone summaries |
| `small` | 14 / 20 | 400 | ink | Table cells, badges, the sidebar's items, fact values, tooltip text |
| `caption` | 13 / 20 | 400 | ink-muted | Source lines, notes, count lines, the stamp, a tooltip's source line |
| `label` | 13 / 16 | 600 | ink-muted | Field and fact labels, stage labels. Sentence case |
| `chart-label` | 12 / 16 | 600, uppercase, +0.02em | chart-text-subtle | Lane and legend labels inside a chart, as the World Bank chart guide sets them |
| `button` | 14 / 20 | 600 | | Buttons |
| mono | Roboto Mono 500, at the size of its text | | | IDs |

Retired from the app: `title` (18 / 700, now `h2` at 600) and the uppercase `label`. Every uppercase label outside a chart becomes sentence case, and the class lint allows `uppercase` only with `chart-label`.

**The deck stays out of this wave.** The deck session rebuilds /present on its own branch, `deck/second-draft` (commit 494a176b, read only). So this wave's token sweep and the new lint rule leave every file under `web/src/deck/` alone: the lint's uppercase rule names `web/src/deck/` as its one exemption, and `--text-title` and `--radius-box` stay in DESIGN.md's theme block as deprecated aliases (`--text-title` takes `h2`'s values), so the deck's old classes still draw when its branch merges. The deck branch's follow-up, with its exact lines, is in the tokens ticket's comments; once it lands, the exemption and the two aliases go in one change.

### 5.4 Space

DESIGN.md's steps, now named by role.

| Token | Value | Role |
|---|---|---|
| `space-0.5` | 2 px | Between sidebar items |
| `space-1` | 4 px | A label to its value; a heading to its ID line |
| `space-2` | 8 px | A heading to its first line; a stage label to its zone; the breadcrumb to the h1; a tooltip's parts |
| `space-3` | 12 px | Control padding; a zone's number to its name; tooltip side padding |
| `space-4` | 16 px | Between blocks inside a zone; between panels; a zone row's padding |
| `space-6` | 24 px | Panel padding; a finding to what follows it |
| `space-8` | 32 px | The page head to the first zone; before a stage label |
| `space-10` | 40 px | Page margin from 1200 px |
| `space-12` | 48 px | Spare, for the deck |
| `space-16` | 64 px | The rail's width; the space under `main` |

### 5.5 Shell sizes

| Token | Value | Note |
|---|---|---|
| `bar-height` | 56 px from 1024 px | The logo's 24 px plus 16 px above and below |
| `sidebar-width` | 224 px | No reference app publishes a width (section 12) |
| `rail-width` | 64 px | The collapsed sidebar |
| Sidebar default | Open from 1440 px; a rail from 1024 to 1439 px; the Menu sheet below 1024 px | A person's own choice wins from 1024 px. The prototype's "Rail at rest" switch shows the other two options (open.md item 2) |
| `frame-top` | 56 px from 1024 px, 0 below | Where sticky parts stick |
| `content-max` | 1280 px | The page's content box, left aligned beside the sidebar |
| Workspace threshold | A frame of 75rem (1200 px) | The frame is the window minus the sidebar |
| `drawer-width` | On a workspace page, from the work's end plus a gutter to the window's edge, 384 to 600 px. On a wide page, `clamp(384px, 40vw, 560px)`. Full screen below 768 px | |
| `tooltip-width` | at most 20rem (320 px) | As Data readiness's tooltips are today |

### 5.6 Shape and elevation

- **Corners by role.** 4 px for controls (buttons, the box, inputs, selects, the view switch, sidebar items, key hints, tooltips). 8 px for containers (panels, the side panel, cards, popovers, windows, the drawer's record cards). The pill for data (status badges, citation markers, chips, the check pill). 16 px only for a bottom sheet's top corners. This is a Strata deviation: worldbank.org's button token is a pill (`--loop-button-border-radius`, [components-variable.css](https://www.worldbank.org/ext/styles/components-variable.css)), and Strata keeps the pill for data so a reader can tell a control from a fact by its shape.
- **Elevation.** Panels have none: a 1 px `line` edge on `page` grey. Zone rows have only the line under them. Tooltips, popovers, windows and the Menu sheet keep the popover shadow. The drawer beside the page has a 1 px `line` edge and no shadow; the drawer over the page (the prototype's other placement) adds the popover shadow, because it then sits over content.

### 5.7 Motion

The rule is Emil Kowalski's gate, in order: should it move at all, what is the movement for, which curve, how long (`../emil-skills/emil-design-eng.SKILL.md` lines 62 to 145). Strata is a work tool read many times a day, so the answer is usually no. Every duration stays inside DESIGN.md section 10's 120 to 200 ms.

**What moves, and why.**

| What | When | Movement | Curve | Time | Purpose |
|---|---|---|---|---|---|
| A tooltip (a number's, a rail item's, a dot's) | The first hover after 150 ms; keyboard focus at once | Opacity 0 to 1 and scale 0.97 to 1, from the side that touches its trigger | `ease-out` | 160 ms | Says where it came from (origin-aware, lines 234 to 245) |
| A later tooltip | Another tooltip closed less than 300 ms ago | None: it appears at once | | 0 | Moving along a row of numbers stays fast (lines 247 to 267) |
| A popover or window (the view switch, "How was that checked?", a count word's window, a definition) | A press | Opacity and scale 0.97 to 1, from its trigger | `ease-out` | 160 ms | Ties the window to what opened it |
| The evidence drawer | A press on a marker, a dot, a row or a facts button | Opacity 0 to 1 and 12 px in from the right, the side it lives on | `ease-out` | 160 ms | Shows the drawer arrived from the edge it sits on |
| The Menu sheet (below 1024 px) and a bottom sheet (below 768 px) | A press | Slides in from its edge; slides back out the same way | `ease-drawer` in, `ease-out` out | 200 ms in, 120 ms out | Spatial consistency: it leaves the way it came (`apple-design.SKILL.md` lines 141 to 147) |
| A primary or secondary button | Pressed | Scale 0.98 on press; back at once on release | `ease-out` | 120 ms in, 0 out | Feedback on press, not on release (`apple-design.SKILL.md` lines 28 to 42); the release snaps, because the deliberate half is the press and the system's answer is instant (`review-animations.SKILL.md` standard 9). The transition lives only on `:active` |
| Hover fills and link colors | Pointer only, gated by `(hover: hover) and (pointer: fine)` | Color | `ease` | 120 ms | A calm hover; the focus ring is never part of it |
| The range chart's lane 2 and dots | A comparison the person pressed | As today: 160 ms and 120 ms (`web/src/styles/app.css` lines 286 to 294) | `ease-out` | as today | State: the comparison changed |
| The export success panel | After export | Fade | `ease-out` | 200 ms | The screen's one entrance (DESIGN.md, Export success panel) |

**What never moves.** Page loads and route changes. The sidebar's width. A zone row opening into a panel. Table rows, cards and lists entering. Numbers (they never count up). Charts on load or rerun. A drawer's content when its source changes. Skeletons (static bars, no shimmer). Focus rings. Anything opened from the keyboard with "/" or closed with Escape: a popover, a tooltip and the drawer close at once however they close, because the system is answering, not deciding (lines 77 and 587 to 600). The past range's table when a pressed number filters it. The prototype's own switches.

**Nothing opens under a resting pointer.** When the page scrolls (a press that lands on rows, a link to a zone), a number that slides under a still pointer opens no tooltip until the pointer moves, as DESIGN.md's evidence card already waits for the pointer to leave and come back. Without this, pressing "2" at 390 px opened 4.4's tooltip over the rows it had just shown.

**Curves.** Two named curves replace app.css's `--ease-out: cubic-bezier(0, 0, 0.2, 1)` and the default `cubic-bezier(0.4, 0, 0.2, 1)` (`web/src/styles/app.css` lines 92 to 94), which are too weak for entrances (line 108): `ease-out` is `cubic-bezier(0.23, 1, 0.32, 1)` and `ease-drawer` is `cubic-bezier(0.32, 0.72, 0, 1)` (lines 112 and 118). Color changes use plain `ease`. Nothing uses `ease-in`.

**Interruptible.** Anything a person can trigger again before it ends (tooltips, popovers, the sheets, the drawer) uses a CSS transition, which can reverse from where it is, never a keyframe animation, which restarts from zero (lines 269 to 288). Entrances use `@starting-style` ([MDN, @starting-style](https://developer.mozilla.org/en-US/docs/Web/CSS/@starting-style)); a browser without it shows the element at once, which is the fallback we want. Input is never locked while something moves. Today's keyframes for the drawer, menus and sheets (`fade-in`, `menu-in`, `sheet-in`, `settle`, app.css lines 96 to 120) become transitions; `spin` stays for the steps' spinner, which is constant motion.

**Only transform and opacity** move (line 479). The chart's SVG attributes are the one exception, as today.

**Reduced motion.** Under `prefers-reduced-motion: reduce` nothing moves and nothing fades: every state lands at once. Emil's and Apple's skills allow a gentle fade under reduced motion (`emil-design-eng.SKILL.md` lines 527 to 543; `apple-design.SKILL.md` lines 207 to 224). Strata keeps DESIGN.md section 10's "none", because no state in Strata needs a fade to be understood, and one rule is easier to test: app.css lines 296 to 303 already stop every transition, and `gallery-a11y.spec.ts` checks it. This is a deliberate departure from `review-animations.SKILL.md` standard 8 ("gentler, not zero"), and design-md block 1 names it as one.

## 6. The one place the plan spends its boldness

**The finding leads, in the World Bank's light voice.** Every Strata page answers something. The plan check answers "One activity needs a look and two are worth watching; three have data notes." The package workspace answers "2 of 49 comparable packages, fewer than 1 in 10, were signed within the plan's 1.5 months." Home answers "One plan changed in the past 15 days. One of its activities needs a look and two are worth watching." Today those sentences are the third thing the eye finds, after the navy bar and the buttons (`notes.md` section 4.2).

In the redesign that one sentence is the largest type on the page: Open Sans Light, 28 px, heading ink, left aligned, at most about 45 characters a line. Its checkable numbers keep their dotted underline and tabular figures in the same weight. Everything around it is quieter. One finding per page, never two. List pages (Packages, All projects, Drafts) have none; their table's title sentence in `lead` does that job.

**World Bank fit outranks a stronger visual identity, on purpose.** The second critic scored distinctiveness 3: at thumbnail size Packages, All projects, Drafts and Lessons share one shape, and the past range, the subject's most telling picture, is 563 px wide at 1440 px while grey sits beside it. I keep it that way, for three reasons. The first people to see Strata are a World Bank panel, and the 2016 guide says secondary colors "should not dominate the corporate blues" (page 18, section 2 above); a louder identity would read as someone else's product. The grey beside the chart is not spare: it is where the evidence drawer opens, so a dot and its records share one screen and the chart never moves (principle 5); a chart in that space would be covered or would jump. And the chart already gets the room the layout can give: 810 px at 1024 px with the rail, 647 px at 1440 px with the Icons rail (`open.md` item 2). What makes Strata recognizable is behavior the panel will feel within a minute, not decoration: the light finding, a number that says where it came from, a press that lands on the rows it counts. If the user wants more presence, the cheapest step is the Icons rail at every width, not a new color or face.

**Where delight comes from, without a second bold move.** The user asked for the app to be pleasant to use. Strata gets that from behavior, not decoration: a number that says what it is and where it came from before you ask; a click that lands on the rows behind it; a check line that explains itself; a removed sentence quoted with its reason; the same current mark everywhere; a button that answers the press. Each is small and quiet, and each is a pattern the user's own fairshare already had (section 9). Apple's principles put it the same way: delight is "the result of getting the other seven right, not confetti tacked on top" (`../emil-skills/apple-design.SKILL.md` line 258).

## 7. Layout concept

### 7.1 Principles

1. **The answer leads.** One finding per page, in the largest type, inside the first screen at every width.
2. **One place for each kind of thing.** Where you are: the sidebar. What you can type or ask: the box, in the bar. What the object is: the side panel. Why to believe a sentence, and a row's whole record: the drawer. The work: the zones, in its order.
3. **Zones follow the work, and open on demand.** A zone a reader usually skips starts closed with a one-sentence summary. A zone is never closed if it holds the page's finding, a removed sentence, an Experimental badge or a refusal. Numbers mark zones only where the work is a sequence.
4. **Provenance has a fixed place.** Each block of evidence ends in a grey foot strip with its note, its coverage line and its source line.
5. **Nothing moves when you open something.** The drawer opens into the space the side panel held, the page's left edge never moves, and every skeleton holds the size of what it stands for.
6. **Pills are data, 4 px corners are controls, 8 px corners hold things.**
7. **A panel only around open work.** A white panel holds evidence, a table or a form. A zone with only a sentence, an action or nothing yet is a row on the grey.
8. **Each person's next step first.** A page shows what the person who comes to it needs for the step they are on. The rest is one click away, on the thing it explains (a number, a row, a source line, a zone's name), never in a menu and never on another page. Section 8.0 applies this page by page.

### 7.2 The shell at 1440 px (sidebar open by default)

```
x 0        224   264                                          913   945                  1440
+-------------------------------------------------------------------------------------------+
| [WBG logo]  Strata  [Q Within KE-NWWDA-541055-CW-RFB x | Ask about this package /]    [View: World Bank staff v] |  navy, 56, sticks
+----------+--------------------------------------------------------------------------------+
| Home     |  Packages > Water and Sanitation Development Project (P156634)                  |
|[Packages]|  Equipping of Exploratory Bo reholes Project-Lot 1-         +--------------------+ |
| Projects |  Sarma n - Tarbaj Water Supply              h1 24/700        | From the plan row  | |
| Lessons  |  KE-NWWDA-541055-CW-RFB                     mono, once       | Method   Market Ap.| |
| Drafts   |  This page shows how comparable packages went, ...           | ...                | |
|          |  Planning ---------------------------------------------     | Source ... [1]     | |
|          |  +------------------------------------------------------+   +--------------------+ |
|          |  | 1  How long it took                                  |     columns 9 to 12      |
| Data     |  |    2 of 49 comparable packages, fewer than 1 in 10,  |     (sticks)             |
| Data through Oct 23 (24 px box)                                    |                          |
| [<] Collapse the sidebar                                           |                          |
+----------+--------------------------------------------------------------------------------+
```

The box starts at the page's content edge (224 + 40 = 264 px) and is at most 640 px wide. At 1280 px the sidebar is a 64 px rail by default, so the frame is 1216 px, as at 1440 px open. The stamp sits at the sidebar's foot because at 1024 px the bar holds the logo and wordmark (to about 212 px), the box from 244 px and a view switch up to 215 px wide, which leaves the box about 500 px; a package page needs 505 px for its chip, its placeholder and the "/" hint.

### 7.3 The shell at 390 px

```
+------------------------------------+
| [= Menu]  [WBG logo]  Strata       |  navy row 1, 56
| +--------------------------------+ |
| | Q KE-NWWDA-541055-CW-RFB  x    | |  navy row 2: the box
| |   Ask about this package       | |
| +--------------------------------+ |
+------------------------------------+
| < Water and Sanitation Developm... |  the breadcrumb's back link (wraps, never cut)
| Equipping of Exploratory Bo        |  h1 24/32
| reholes Project-Lot 1- Sarma n -   |
| Tarbaj Water Supply                |
| KE-NWWDA-541055-CW-RFB             |
| This page shows how comparable ... |
| Request for Bids, Open - National, |  the plan row in one line
| US$1,230,000, Pending Implement... |
| [Show the plan row]                |  opens the plan row in the drawer
| Planning ------------------------- |
| | 1 How long it took             | |
| | 2 of 49 comparable packages,   | |  finding, 24 light, inside 844 px
+------------------------------------+
Menu open: a sheet from the left, min(320 px, the window minus 48 px), over the scrim.
```

The bar does not stick below 1024 px, so a phone keeps its screen for the page.

### 7.4 The package workspace at 1440 px

```
 columns 1 to 7 (649 px)                                     columns 9 to 12 (357 px)
 Packages > Water and Sanitation Development Project (P156634)
 Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n -       +---------------------------+
 Tarbaj Water Supply                                                | From the plan row         |
 KE-NWWDA-541055-CW-RFB                                             | Method        Market      |
 This page shows how comparable packages went, so you can judge     | Request for   Approach    |
 whether this package's plan is realistic.                          | Bids          Open - Nat. |
 Planning -----------------------------------------------------     | ...                       |
 +-------------------------------------------------------------+   | Source: ... [1]           |
 | 1  How long it took                                         |   +---------------------------+
 |    2 of 49 comparable packages, fewer than 1 in 10,         |
 |    were signed within the plan's 1.5 months.   (finding)    |   hover "49": a tooltip under the whole
 |    ...chart, abstention, Show the table, summary...         |   finding, left aligned with 49: "All
 |.............................................................|    comparable packages in the past range,
 |    Note, coverage line, Source              (grey foot)     |    including the four still open. / From
 |-------------------------------------------------------------|    Procurement Notices and Contract Awards,
 |    Advertised again  (Experimental) ...                     |    through October 13, 2026. / Select to
 +-------------------------------------------------------------+    see all 49."  Hover "2": its own sentence.
   2  Planned date for each step                [v Show the steps]    Press "2": the table opens filtered to its
                                                                       two rows, its title under the bar,
                                                                       "Showing the 2 of 49 packages signed
                                                                       within 1.5 months. [Show all 49]"
   3  Procurement risks and what helped               PPSD section 3
   4  Procurement approach options                    PPSD section 6
 Tender design -------------------------------------------------
   5  Check your criteria                       [v Show the check]
```

### 7.5 The plan check at 1440 px (wide)

```
 Packages > Water and Sanitation Development Project (P156634)
+------------------------------------------------------------------------------------------+
| Northern Water Works Development Agency           [9 activities checked] [Draft review notes (3 rows)] |  sticks from 1024 px
| Procurement Plan of October 9, 2026              The draft waits in Drafts for you to check. I send nothing. |
+------------------------------------------------------------------------------------------+
 One activity needs a look and two are worth watching;             (finding, 28 light)
 three have data notes.
 I checked every activity against its own dates, ...
 Compared with the plan of March 5, 2026, this version re-estimated two activities. See what changed
 +----------------------------------------------------------------------------------------+
 | Activities in this plan                                      Showing 6 of 9 activities |
 | Activity | Method and market approach | Review | Estimated (US$) | Process status | What Strata found |
 | ... marked rows; a row's reference opens its records in the drawer ...               |
 | Three more activities have no signals: ...                              [Show them]   |
 | Source ... (grey foot)                                                                 |
 +----------------------------------------------------------------------------------------+
   What changed since the plan of March 5, 2026                         [Show the changes]
   Baseline for delay ... [Save as the baseline]
```

Six columns need a page area of 60rem. At 1024 px with the rail the page area is 56rem, so the table draws three: Activity, Estimated (US$) and What Strata found, as it does beside the drawer; the other STEP fields are one press away in the row's records. Below 40rem the rows are cards. Round 3's first pass drew six columns down to 54rem and broke "Review" and "Implementation" inside the word at 1024 px. With no signal to draft from (a staff check of a plan with no signals, or the public view), the head holds no action and does not stick, and only the data-note rows are marked.

### 7.6 The package workspace below a frame of 75rem

```
 1024 px, rail (frame 960): all 12 columns, 896 px of content
 Packages > Water and Sanitation Development Project (P156634)
 Equipping of Exploratory Bo reholes Project-Lot 1- Sarma n - Tarbaj Water Supply
 KE-NWWDA-541055-CW-RFB
 This page shows how comparable packages went, so you can judge ...
 Request for Bids, Open - National, US$1,230,000, Pending Implementation  [Show the plan row]
 Planning -----------------------------------------------------------------------
 | 1  How long it took ... (chart about 810 px)
```

### 7.7 Home at 1440 px (workspace layout; new in round 3)

```
 columns 1 to 7                                                     columns 9 to 12
 Your briefing for Wednesday, October 28                   (label, the h1's first line)
 One plan changed in the past 15 days. One of its          (finding, 28 light; count words
 activities needs a look and two are worth watching.        open windows that list them)
 One lesson cited in your drafts changed. Two drafts
 are waiting for you to check.
   Start here   Examples Strata set up for you                    [Remove]   a row on the grey
   Check a published plan (P156634)  Plan a package from a sentence  ...    (staff, own view)
 +-------------------------------------------------------------+   +---------------------------+
 | Worth knowing                      Fixed checks, no model   |   | Waiting for you           |
 | [Needs a look]                          Open the activity   |   | Suggested PPSD risk rows  |
 | KE-NWWDA-541055-CW-RFB, US$1.23 million of works in the     |   | for Equipping of ...      |
 | Water and Sanitation Development Project (P156634), passed  |   | [Example] I set it up as  |
 | its planned completion date of July 31, 2026 with no signed |   | an example on October 28, |
 | contract in the plan. The project closes October 31, 2026.[1]|  | 2026.                     |
 | [Watch] ... [Watch] ... [Changed] [Example] ...             |   | Review notes on the ...   |
 |.............................................................|   | Go to Drafts              |
 | Source: Procurement Plans, project records and ISRs ...     |   +---------------------------+
 +-------------------------------------------------------------+

 After a question asked from Home: the answer panel at the top, then the briefing folded to
 one line ("Your briefing for Wednesday, October 28. One plan changed in the past 15 days."
 and "Show the briefing"), then Worth knowing and Waiting for you as before.
```

### 7.8 A draft's page at 1440 px (workspace layout; new in round 3)

```
 columns 1 to 7                                                     columns 9 to 12
 Drafts                                                    (breadcrumb)
 Review notes                                              (h1)
 Northern Water Works Development Agency, Procurement Plan of October 9, 2026
 I drafted notes on 2 of the 3 activities that need a look or are worth watching.   (lead)
 I wrote each note from my check of this plan and cited ...                          +----------------------+
 +------------------------------------------------------------+                    | State of this draft  |
 | Checked: 5 of 5 numbers match records; 4 of 4 dates match  |  surface-2 block   | (o) Draft            |
 | records.                                                   |                    | ( ) Checked by you   |
 | Not checked: whether the plan's published records are     |                    | ( ) Exported         |
 | complete, or whether these notes are what you would tell   |                    | Made from            |
 | the borrower.          How was that checked?               |                    | my check of this plan|
 | I removed two sentences. The first said the plan lists ... |  removed box, open | I drafted these notes|
 +------------------------------------------------------------+                    | for you on October   |
 | Activity               | Review note                       |  a panel           | 23, 2026.            |
 | KE-NWWDA-541055-CW-RFB | The plan lists this activity ...[1]|                   +----------------------+
 | ... three rows; the third holds its first-person abstention |
 Sources (2) ... 
+--------------------------------------------------------------+
| A working draft of your review notes ... Exporting sends nothing ... You opened 0 of 2 sources.  |  the draft bar,
| Mark the notes as checked before you export them.                                                |  held to the work's
| [Discard]                                    [Export to Word (held)] [Mark as checked]            |  columns
+--------------------------------------------------------------+
 After "Mark as checked": the stepper moves to "Checked by you", the bar's line reads
 "Checked by you on October 27, 2026." and Export to Word becomes the primary button. Nothing animates.

 Below a frame of 75rem the stepper takes one line in the head, under the subtitle
 ("(o) Draft  ( ) Checked by you  ( ) Exported"), and "Made from" and "Drafted" follow the draft,
 so the lede stays in the first screen (296 px down at 390 by 844).
```

### 7.9 Alignment

Everything is left aligned with a ragged right edge. Nothing is centered or justified. The content box hugs the sidebar and stops at 1280 px, so on a wide screen the air is on the right, where the drawer opens. Numbers in tables and fact lists are right aligned in tabular figures; the finding is left aligned. Zone names share one left edge after a 24 px number column, in panels and rows alike. Labels sit above their values in the side panel at every width, so a long STEP value never crowds its label.

### 7.10 Worst-case data: wrap, never break, never clamp

`break-ui.SKILL.md` gives three choices for a long string: wrap, truncate or clamp (lines 117 to 125). DESIGN.md section 3 settles one of them for Strata: "No container that holds writer or source text has a fixed height or a line clamp". STEP descriptions, project names, agency names, notices and quotes are all source text. So Strata never clamps or truncates them; it wraps them and gives them room. The longest real strings in the fixture (`tests/fixtures/api/`, searched October 26, 2026) set the cases, and the prototype's "Longest" switch shows each one in place.

| String | Longest real value | Where it shows | Rule |
|---|---|---|---|
| STEP description | 257 characters, KE-KIMAWASCO-76105-GO-RFB: "Supply and delivery of al l small customer meters(3,510 no.) to AMR enabled meter s(DN15mm-32mm) ..." (`packages-p156634-page-2.json`) | The package page's h1, a plan check row, a drawer's Description | Wrap in full. The h1 keeps the work's 7 columns; a row's Activity cell keeps at least 40 percent of the table; the side panel's facts never sit beside it |
| An all-capitals description | "REFURBISHMENT OF HUDUMA CENTRES IN BORDERLAND AREAS IN THREE (3) LOTS ..." (166, a notice's Bid Description) | A drawer's record card | Shown as the record has it; never re-cased, because it is the source's text |
| STEP reference with spaces | "KE-UASIN GISHU COUNTY-571338-CW-RFB" (35), one of the package's 49 comparables (`comparables-ke-nwwda-541055.json`) | The box's chip, the past range's table, the drawer's title | DESIGN.md's Reference words: break at its spaces first, after a hyphen only when a part is wider than the line, never inside a part, never truncated |
| Project name | "Second Program for Strengthening Governance for Enabling Service Delivery and Public Investment in Kenya" (104, P180287) | All projects, the breadcrumb, a drawer's meta line | Wrap. Below 768 px the breadcrumb's back link wraps to two lines and keeps its 24 px line box |
| All-capitals project name | "NATIONAL AGRICULTURAL VALUE CHAIN DEVELOPMENT PROJECT (NAVCDP)" (P176758) | All projects, a comparable's drawer | As the projects API writes it |
| Implementing agency | "Rural Electrification and Renewable Energy Corporation" (54) | The plan check's h1 in its sticky head | Wrap. The sticky head lays its title and its action out by the page area, and stacks them below 46rem |
| Amount | 232,524,000.00 (a P161305 plan row) | Estimated (US$) cells and facts | Never wraps or shortens (`white-space: nowrap`, tabular figures); STEP's form with its cents |
| Dates, "N of M", "page N" | "October 13, 2026"; "49 of 65"; "Open at page 65" | Everywhere, tooltips included | Never break inside (no-break spaces, as ticket 59 line 35 asks for the Data tooltips) |
| Lesson statement | 68 characters (the lesson editor's limit is 80) | Lessons cards, Home's line, a draft's notice | Wrap |
| Export file name | 99 characters with no spaces | The export success panel's links | `overflow-wrap: anywhere`, the one string that may break anywhere, since it has no words |
| The box's placeholder | "Open a project or package, or ask a question" measured 333 px against a 318 px field at 390 px (`work/probe3.cjs`), so round 2's claim that it fit was wrong | The bar's box below 768 px | A short form below 768 px, "Open a project or package, or ask" (250 px), with the whole sentence kept as the field's name; below 360 px the search icon hides (272 px of field at 320 px) |
| Count of one | "One draft.", "One note.", "1 of 1 sentence" | Count lines and the six checks | The copy file's one and many forms, as today |
| Zero and empty | Home's first run, an empty Drafts tab, Lessons' first visit, no packages | Those pages | The first-person sentence and its one link, as a zone row; a status sentence takes `lead`, never the finding style (8.5) |
| Fewer than 20 comparables | Seven: the same package compared with prior-review packages only (`comparables-ke-nwwda-541055-prior.json`, with `rebidding-ke-nwwda-541055-prior.json`) | The package page's zone 1 | Strata holds back (DESIGN.md section 7, rules 15 and 16): "I'm not giving a range: only seven comparable packages. Here are all seven." takes the finding style, the count follows in `body` ("None of the seven comparable packages were signed within the plan's 1.5 months."), the chart keeps its dots and plan line with no band, middle or 8-in-10 line, and the table opens with the page |
| No search match | "atlantis" (`projects-no-match.json`) | All projects | The field keeps the query; the panel holds the first-person sentence, its body and "Show all projects", with no count line, table or pager |
| A failed request | Each page's own sentence from the copy file ("I couldn't load this plan's check because the data service didn't answer.") | Every page | 8.5: the alert slot for a page that failed, the zone for a block that failed |
| A plan check with no signals | No fixture holds a staff check with none; the public view's check holds them back (`check-plan-p156634-nwwda-2026-10-09-public.json`) | The plan check | "No activity needs a look or is worth watching; three have data notes." The head holds no action and does not stick; only the data-note rows are marked |

The sidebar's labels, the buttons and the view switch hold copy-file words only, never data, so none of them needs a rule beyond DESIGN.md's 167 px for the view switch's label.

## 8. Information architecture

### 8.0 What to show where, to whom

The user's principle, page by page. "Staff" is the World Bank staff view; "officer" is the implementing agency officer view. Each "one click away" names where the click sits, because the principle is as much about place as about count.

| Page | Who comes | What they are there to do | Shows first | One click away, and where the click sits | Stays out |
|---|---|---|---|---|---|
| Home `/` | Staff each morning, and the panel on arrival. An officer, for their team's latest plan. A member of the public, for a way in | Staff: learn what changed since the last visit, and what waits for them. An officer: see what in their own plan is behind. The public: find a project | Staff: the briefing sentence (finding style) with count words; Worth knowing lines, each with one verb; Waiting for you in the side panel. An officer (drawn from `home-preview-piu.json`): "I checked your team's latest Procurement Plan ... Two of its activities are behind their planned dates.", then those two lines, and no Start here. The public (`home-preview-public.json`): one `lead` sentence on the 93 projects Strata holds, then the latest closed project's traced contracts | What a count counts: a window on the count word. A line's record: the marker at the line's end. The activity or the change: the line's verb at the first row's right. A draft: its title in the side panel. An answer: the box | Totals across all projects, charts, anything unchanged in the window, projects not followed, and Start here once removed |
| Packages `/packages` | Staff who check a plan; an officer who checks their own plan before submitting it | Start a check, or go back to a package or check in progress | The two verbs at the head's right; their packages and checked plans, newest first | A check or package: its name in the row. "Last worked on" defined: its column head. Check mode or plan mode: the head's buttons, which put the box in that mode | Other people's packages, comparables, signals; those belong on the plan check and the package |
| The plan check `/projects/:pid/procurement/:agencyId` (lit as Packages; lit as Projects in the public view, which has no Packages) | Staff preparing comments on a borrower's plan; an officer on their uploaded plan's check; the public, reading a plan with its signals held back | Decide which activities to raise, then draft the notes | The finding; marked rows first; "Draft review notes" as the one primary action in the sticky head. With no signal to draft from, the finding says so and the head holds no action and does not stick | A row's records (reason, what I checked, the plan row): the row's reference, in the drawer. The past range: the row's link. What changed: the change line's link, which opens its row in place. Rows with no signals: "Show them" in the fold | Unmarked rows (folded), the baseline control (last), definitions (on the count words and column heads) |
| The package page `/packages/:stepRef` | Staff judging whether a plan's dates are realistic and choosing PPSD risk rows; an officer planning the package's dates | Judge the plan, then pick what goes into the draft | The finding in zone 1, the chart, the plan row's facts in the side panel, zones 2 to 5 as one-line rows. With fewer than 20 comparables, the sentence that holds back is the finding and the table opens with the page | A dot's records: the dot, in the drawer. The rows behind a number: the number, which filters the table under the chart to them, with "Show all 49" after the count line. The plan row: the marker in the side panel. A closed zone: its Show button at the row's right | The comparables' full records (drawer), how comparables were chosen (the foot strip's Note, under the evidence), STEP's step definitions (windows) |
| Projects `/projects`, `/projects/following` | Staff on their followed projects; everyone else finding a project | Open the right project | Following's rows (staff), or the search and the list (others; the public view has no Following). A search with no match keeps the query and says what I search | A project: its P-code. Quiet projects: the fold. Following or All projects: the sidebar's sub-items | Signals sorted, shaded or counted (DESIGN.md rule 33), and repeated columns |
| The project page `/projects/:pid` | Staff before a mission; an officer on their own project | See the project's whole story | Summary's finding and its fact tables | A fact's source: its marker. Another view: the tabs. Closing date history: its disclosure. Follow: the head's right | Agencies past the first line (Show all agencies), the activity list (Procurement tab) |
| Lessons `/lessons` | Staff and officers whose drafts cite lessons; reviewers | See what changed where they used it, and what is new | The digest sentence counting what came in since the last visit; "Changed where you used it" first. On a first visit the status sentence in `lead`, not the finding style | What a count counts: the count word. A quote's paragraph: its Source chip, in the drawer. Two versions: "See both versions", in the drawer. Reviewer pages: the sidebar | Retired lessons (the status filter), and the review queue for non-reviewers |
| A lesson's page `/lessons/review/:itemId` | A lead procurement specialist or an accredited reviewer. Strata has no reader page for one lesson; a reader opens a lesson in the drawer | Decide whether the lesson enters the library, with a reason | The statement, its quote and paragraph, the decision form | The paragraph: the drawer. Its history: the side panel. The queue: the sidebar | Other items in the queue, and anything that ranks lessons by use |
| Drafts `/drafts` | Staff and officers who made drafts | Check and export what waits | To check, newest first, then Checked and Exported | A draft: its title. Discarded drafts: the fold's "Show it" | Drafts of other teams; nothing is sorted by how much it holds |
| A draft's page `/drafts/:id` | The draft's author; a teammate reads it | Read each note against its record, mark it checked, export | The lede, the check line, the removed box (open), the notes, the bar with what exporting does | A note's record: its source number, in the drawer. How it was checked: "How was that checked?" after the check line. The steps: "Show the n steps I took" | Export until it is checked (the held button says why), and other drafts |
| Data readiness `/data` | Anyone asking whether to trust an answer: the panel, staff, officers, the public | Learn what each source covers and what holds it back | The headline (finding style), What you can ask, Sources | Any number's definition and table: the number. A column's definition: its head. The hardest documents and the fixes: closed rows. Sources and licenses: the sidebar's sub-item | How Strata works (the deck covers it), and the AI/BI dashboard |

### 8.1 The sidebar

1. **Home.** The briefing. The wordmark in the bar also opens it.
2. **Packages, Projects, Lessons, Drafts**, the applied view's (the public view has Projects and Lessons; the officer's view has all four and hides Following and the reviewer pages, as `config/roles.toml` lines 182 to 185 say, and the public view hides Packages and Drafts, lines 187 to 191). Under the current section, and only there, its own pages show as indented items: Following and All projects under Projects (staff); Waiting for review, Passage reports and Judging under Lessons (for the reviewers who have them, a count in a small badge hidden at zero).
3. **The foot**: **Data** (with Data readiness and Sources and licenses under it when it is the current section; How Strata works is gone), the stamp ("Data through Oct 23"), and "Collapse the sidebar".

Each section is one route, once. The blueprint's Occam's razor row removed "the Home sidebar" because "between them they offered four routes to the same list"; this sidebar offers one route per noun. The current item is the route's own section from `routes.ts`; the plan check's section becomes Packages, with a breadcrumb that starts at Packages. The rail is 64 px of icons, each with its label in a tooltip on hover and focus; the Data tooltip carries the stamp's words. The person's choice of open or rail is kept in local storage and read before the first paint. Below 1024 px the sidebar is the Menu sheet.

### 8.2 The top bar

The navy bar is the banner landmark: the Menu button (below 1024 px), the World Bank Group logo (`open.md` item 1), the wordmark "Strata" (a link to Home), the one box, and the view switch. From 1024 px everything sits on one 56 px row that sticks. Below 1024 px the box takes a second row; below 768 px the view switch moves into the Menu sheet. The data stamp sits at the sidebar's foot.

### 8.3 The page frame and its two layouts

- **The frame.** Under the bar: the sidebar, the page column, then the drawer when it is open. The page's left margin follows the window, so the drawer cannot move it. `main` holds at least the window's height minus the bar. The footer holds the disclaimer on every screen.
- **The page head**: the breadcrumb (parents only), the h1, an object's ID line, the purpose; at most one primary action at the head's right.
- **Wide layout**, for lists, tables and dashboards: Packages, All projects, Following, the plan check, a project's tabs, Drafts, Data, Lessons. All 12 columns; the drawer narrows the page and keeps its left edge.
- **Workspace layout**, for pages read top to bottom while sources open: Home, the package workspace, a planned package, a draft, a lesson's review page. The work in columns 1 to 7 and a side panel in 9 to 12, measured on the frame, so the drawer opens into columns 8 to 12 and the work never moves. From a frame of 75rem; below it one column with an object's facts in one line.
- **The drawer's placement.** Beside the page, as DESIGN.md has it ("never over it"), and the prototype's other option, over the page's right side, is in `open.md` item 3. On a workspace page the two look the same, because the drawer fills free columns. They differ on a wide page: beside narrows the table to three columns; over keeps all six and covers the right ones.

### 8.4 Each tab as task zones

**Home** (`/`, workspace; drawn from `tests/fixtures/api/home.json`)
- First: the date line in `label` and the briefing's sentences in the `finding` style, as the h1. Then Start here as a row (staff, own view, until removed). Then Worth knowing as a panel in columns 1 to 7: its name and the tag "Fixed checks, no model", four lines, each a badge, one verb at the first row's right, the sentence, and its marker at the end, then the foot strip's source. Waiting for you is the side panel.
- After a question asked from Home, the answer panel takes the top and the briefing folds to one line with "Show the briefing" (`aria-expanded`), fairshare's strip (9, pattern 6). Worth knowing and Waiting for you stay as they were.
- Empty: the first-run sentences ("You don't follow any projects yet, so I have no plans to brief you on. No draft is waiting for you to check.") in `lead` under the date line, because they report a state, not a finding; Worth knowing as a row with "I brief you on the projects you follow." and "Go to All projects", Waiting for you with its empty sentence and "Go to Packages".
- The agency officer's view (`home-preview-piu.json`, a preview): the same date line and finding style over the officer's own briefing, "I checked your team's latest Procurement Plan, the plan of October 9, 2026 for the Water and Sanitation Development Project (P156634). Two of its activities are behind their planned dates.", where "Two" opens "Activities behind their planned dates"; no Start here; Worth knowing with the two lines and the agency's source sentence; Waiting for you as a row that says a preview shows no team's drafts.
- The public view (`home-preview-public.json`): "Home" as the h1, one `lead` sentence on what Strata holds, and a "Closed projects" panel (tag "Contracts traced from public records", split from today's middle-dot title) with the latest closed project's line, "See its contracts" and "Find more projects". No side panel.
- Error: "I couldn't load your briefing because the data service didn't answer." in the alert slot with "Try again", and "Home" as the h1.

**Packages** (`/packages`, wide; drawn): the h1, its purpose, "Check a plan" (primary) and "Plan a package" (secondary) at the head's right, then the list in a panel with its title sentence in `lead` and its source in the foot strip. Empty: "You have no packages or checked plans yet." and "Use Check a plan or Plan a package above to start one."

**The plan check** (lit as Packages; drawn): the sticky head, the finding, the method and change lines, the activities panel, "What changed" as a closed row, the baseline as a row with its action. A row's reference opens its records in the drawer. Six columns from a page area of 60rem, three below it, cards below 40rem (7.5). With no signals the finding reads "No activity needs a look or is worth watching; three have data notes.", the head holds the check pill only and does not stick, and only the data-note rows are marked. The public view holds signals back on an active project ("I don't show signals on active projects in this view, so a procurement still under way isn't prejudged; three have data notes."), shows no baseline, and lights Projects with its breadcrumb at the project. Error: the alert slot, then the breadcrumb and "Procurement Plan" as the h1.

**The package workspace** (drawn): as round 2, with the chart drawn from the 49 real comparables and the dots opening their records. A pressed number filters the table under the chart to the rows it counts (9, pattern 2). With fewer than 20 comparables (Empty or few), zone 1 holds back as 7.10 says. Error: zone 1's first block is the error alert "I couldn't load the comparable packages for this section." with "Try again", under the zone's header; "Advertised again" keeps its own result, because it comes from its own tool.

**Projects and the project page**: as round 2; the project page is not drawn. All projects is drawn with no match ("atlantis") and with a failed load, where the panel keeps its name and its search and the error alert takes the list's place. The public view shows All projects with no Following.

**Lessons** (drawn in its first-visit state): the digest sentence as the finding once there is something to count; on a first visit its status sentence in `lead`. Then "Changed where you used it", "New", "Your reports", "The library", each a panel or a row by what it holds.

**Drafts** (`/drafts`, wide; drawn from `drafts-list.json`): one panel, one table, the groups To check, Checked and Exported as row groups with their count lines, discarded drafts folded. Empty: "You have no drafts to check." and "Go to Packages".

**A draft's page** (`/drafts/:id`, workspace; drawn from `drafts-review-notes-partial.json`): the lede, the method, the check line with "How was that checked?", the removed box open under it, the notes panel, the sources, and the draft bar held to the work's columns. The side panel holds the state stepper, what the draft was made from and when; below the threshold the stepper is one line in the head and the rest follows the draft. After "Mark as checked" the bar says who checked it and when (9, pattern 9).

**Data** (`/data`, wide; not drawn). Data readiness and Sources and licenses become sidebar items under Data; the sub-tab row goes. The headline is the page's finding; "What you can ask" and "Sources" are panels; "The hardest documents I read", "Plan pages the layout parser couldn't read" and "Fixes that would unlock the most" are closed rows. The page lays out by the page area.

**How Strata works leaves.** Where its content goes:

| Part of the page today | Where it goes | Why |
|---|---|---|
| The eight figures and their captions (`web/src/pages/data/HowStrataWorks.tsx`, `FigureSection`) | The deck at /present, which already shows the same figures from `web/src/figures/` and `web/src/deck/copy.ts` | The user: the deck covers it |
| "What I don't do", the list of refusals with each one's reason (`WhatIDontDo`, `HowStrataWorks.tsx` line 118) | Split in two. (a) Each refusal in the answer panel says its own reason in place, as a third sentence after what I don't do and what I can do instead, from the same copy key (`copy.refusals[key].why`). (b) The caption under a refusal becomes a flush ghost "See everything I turn down", which opens a non-modal window (DESIGN.md's window, as the Measure number's) listing every lead and its reason. The section 5 check's refusal note gets the same | The reason belongs where the refusal is read (principle 8), and the full list is one click away from the only place anyone needs it |
| The page's intro and its links to Data readiness and Sources (`copy.dataReadiness.howPage.lead` and `.next`) | Removed | Data readiness and Sources are sidebar items |

Routes and code that change: `web/src/routes.ts` lines 61 to 64 (`DATA_PAGES.dataHow`, `DATA_HREF.dataHow`, `WHAT_I_DONT_DO`) and line 133; `web/src/RoutePage.tsx` line 85; `web/src/pages/data/DataPage.tsx` lines 9, 25 and 30; `web/src/pages/data/HowStrataWorks.tsx` (removed; `WhatIDontDo` moves to `web/src/components/` as the window's body); `web/src/components/AnswerPanel.tsx` lines 46 and 471 to 473 and `CheckCriteria.tsx` lines 18 and 211 to 212 (the refusal note); `web/src/gallery/pages.tsx` lines 87 and 1506 and `web/src/gallery/copy.ts` lines 279 and 1078 to 1079; `web/src/copy.ts` lines 22 to 23 and 918 to 920 (the refusal note) and 5601 to 5624 (`howPage`, removed). The address `/data/how-strata-works` answers with Data readiness through a replace, so an old link lands somewhere true and Back never returns to it. Tests and captures that change: `web/tests/data.spec.ts` line 72 (the sub-tab list), line 81 (the title) and lines 780 to 847 (the How Strata works test and its row in the route table); `web/tests/sweep.spec.ts` lines 112 to 113; `web/tests/checks.spec.ts` lines 216 to 227 and `web/tests/answer.spec.ts` lines 317 to 318 (the refusal's link becomes the window); `web/capture/shots.ts` lines 1746 (`refusal--how-strata-works` becomes `refusal--why`) and 1973 (`data("how", ...)` goes). `web/src/figures/order.ts` line 17's `PAGE_ORDER` is then used by nothing on `build/strata`; it stays for the deck branch to keep or remove (tokens ticket, comments). DESIGN.md's lines that name the page change with the refusal window ticket ("How Strata works leaves Data"): the Refusal row, section 7's note on the deck, section 9's figure bullet and section 11's deck paragraph.

### 8.5 The states every page draws

- **Loading.** The bar paints at once. Until GET /api/me answers, the sidebar shows six static `surface-2` bars at the items' height. Zones load with their real header and skeleton bars sized to their content; the side panel with its labels and value bars. No shimmer.
- **Empty.** A first-person sentence that says what will appear and what to do next, with at most one link, as a zone row. A status sentence ("This is your first visit to Lessons.", Home's first run) takes `lead`: the finding style is for a finding.
- **Few.** When Strata holds back (DESIGN.md section 7, rules 15 and 16), the first-person sentence is the page's answer, so it takes the finding style, and the counts it may still give follow in `body`. Every record stays in view, the table opens with the page, and the chart drops what rule 15 forbids.
- **Error.** An error alert (the error state's background, a 4 px left border, `circle-x`, the copy file's own sentence) with a secondary "Try again". When the page's one request failed (Home, the plan check, a draft, Lessons), it sits in the alert slot above the head, the h1 names the page and nothing else draws. When one block failed (the package's past range), it sits in that zone's body under the zone's header, and the rest of the page stays. When a list failed (Packages, All projects, Drafts), the panel's name and its search stay and the alert takes the list's place.
- **Abstention.** First person, inside the zone, never in a closed row.
- **Populated.** As above.
- **Shell states.** Preview, as of a past date, the public view, narrow (the Menu sheet), collapsed (the rail), signed out and identity errors. A preview opens every page with the info alert ("Preview of what the public sees. You are still signed in as yourself.") and "Leave the preview"; a page the view hides keeps its address, takes the section's name as its h1, and says "This page isn't part of the public view." with one link.

### 8.6 Strings the prototype adds

The prototype uses copy.ts's strings where they exist. These are new, proposed for copy.ts, each landing with the ticket that shows it; ticket 58 owns their wording.

- `nav.home` "Home", `nav.collapse` "Collapse the sidebar", `nav.expand` "Expand the sidebar", `nav.menuClose` "Close the menu".
- `packagePage.factsTitle` "From the plan row", `packagePage.factsShow` "Show the plan row", the facts line template.
- `risks.ppsdTag` "PPSD section 3", `approach.ppsdTag` "PPSD section 6".
- `checkPlan.activitiesTitle`, `checkPlan.columns.method` "Method and market approach", `checkPlan.changes.show` and `hide`, `checkPlan.rowChecked` "What I checked", `checkPlan.rowPlan` "From the plan row".
- `evidence.planRowCaption` "Activity in the {agency} plan of {date}", `evidence.package.caption` "Comparable package in the past range".
- `home.worth.title` "Worth knowing" and `home.worth.tag` "Fixed checks, no model", split from today's string; `home.briefingShow` "Show the briefing" and `home.briefingHide` "Hide the briefing".
- `checkLine.how` "How was that checked?", `checkLine.howTitle` "How I checked this answer" (and "How I checked this draft"), `checkLine.rounding` "A number passes only when a record holds it at the same rounding.", `checkLine.runId` "Answer ID".
- `num.from.*`, the tooltip's source line, one template per kind of number: "From Procurement Notices and Contract Awards, through {date}." for the past range; "From the {agency} plan of {date}." for a plan row; "From my check of this plan, as of {date}." for the plan check; "From my checks on {date}." for Home.
- `answer.refusalAll` "See everything I turn down" and `answer.refusalWindow` "What I turn down", replacing `refusalNote` and `refusalLink`.
- `box.placeholderShort` "Open a project or package, or ask", the box's placeholder below 768 px (7.10).
- `draft.side.madeFrom` "Made from" and `draft.side.drafted` "Drafted", the draft's side panel labels.
- `projectsPage.countRange` "Showing {from} to {to} of {total} projects", replacing the en dash.
- Added after the second critic's review:
  - `pastRange.explain.*`, one What sentence per number, replacing `counts` and `quantiles` (whose "This is the Kaplan-Meier method." goes): `within` "Comparable packages signed within {plan} months of their notice.", `total` "All comparable packages in the past range, including the {open} still open.", `plan` "The plan's months from notice to signed contract.", `middle` "Where the middle half of the {total} packages starts and ends. I counted the {open} still open as not signed yet.", `median` "The middle package's months. ...", `in10` "The months by which 8 in 10 packages were signed. ...", `coverage` "Comparable packages I used, out of all that matched the criteria.", and `rebidding.explain` "Comparable packages advertised again, out of all {m}, canceled packages included."
  - `num.act.*`, the action lines: "Select to see the two packages.", "Select to see all {total}.", "Select to see the plan row.", "Select to see the packages in the middle half.", "Select to see the middle package.", "Select to see the packages signed within it.", "Select to see its records.", "Select to mark it in the table." and "... them ...", "Select to list them.", "Select to see the record."
  - `pastRange.chart.tipSigned` and `tipOpen` rewritten with full dates (rule 13): "{country}. Its notice was published {notice}, and its contract was signed {signed}." and "{country}. Its notice was published {notice}, and the records I hold show no signed contract."
  - `pastRange.table.shown.within` "Showing the {within} of {total} packages signed within {plan} months.", `.middle` "Showing the packages in the middle half, from {q25} to {q75} months.", `.median` "Showing the middle package, at {q50} months.", `.in10` "Showing the packages signed within {q80} months.", `.all` "Showing all {total} packages." (under 20), and `pastRange.table.showAll` "Show all {total}". A number and "months" never break apart.
  - `checkLine.howScope` "These counts include the two sentences I removed. The check line counts only the sentences I kept." (with a one form), shown only when the verifier removed a sentence; `checkLine.howTitleDraft` "How I checked this draft"; `steps.check.six.sourcesDraft` "{returned} of {total} sources I cited came back for this draft."; `checkLine.draftId` "Draft ID {id}, run {run}".
  - `home.publicView.title` "Closed projects" and `home.publicView.tag` "Contracts traced from public records", split from today's middle-dot string.
  - Ticket 58's words that now render larger: `checkPlan.finding.lookAndWatch` gains its noun ("{look} activity needs a look ..."), "Show the {n} packages and their reasons" writes one to nine in words, and the risks section's "None of the {n} projects" does too.

## 9. Patterns borrowed from fairshare

The user's earlier app, fairshare, had many of the things the user now asks for (`../user-additions.md`, item 3; read only). The study is `../fairshare/notes.md`; its section 7 names ten patterns. Strata adopts nine, folds the "small ones" it can use, and keeps fairshare's own "not to carry over" list. Each row names the fairshare file the pattern comes from (paths under the fairshare repo), the Strata page and component it lands on, the ticket that builds it, and how it keeps Strata's rules: every number from a tool at the tool's rounding, every claim cited to a record or a numbered paragraph, every string in `web/src/copy.ts`.

**The naming trap.** fairshare's `web/src/components/Notes.tsx` is the deck's speaker-notes window, not a citation component (`../fairshare/notes.md` line 11). What works like a citation in fairshare is a chain: the checked number (`Num.tsx`) with the fact behind it, the check line under the answer, the red box of removed sentences, and the "Show the numbers" and "Show the query" panels (lines 81 to 108). Strata's chain is the same shape with its own parts: Num and Measure number, the check line, the removed box, and the evidence drawer. Strata's deck already has its own speaker notes view (DESIGN.md, Speaker notes view), so nothing from `Notes.tsx` is needed.

### 9.1 Adopted

| # | Pattern | fairshare file | Strata page and component | Ticket | How it keeps Strata's rules |
|---|---|---|---|---|---|
| 1 | **The number that explains itself.** Hover or focus gives what the number is, where it came from, and what a click does | `web/src/lib/runs.ts` lines 192 to 201 (the hint), `web/src/copy.ts` lines 195 to 196, `web/src/components/Num.tsx` lines 13 to 19 | Every Num and Measure number; drawn on the package workspace, the plan check, Home and a draft. Component: Number tooltip (section 10) | The number tooltip ticket | The sentence and the source line are copy-file templates filled with the tool's own values and the record set's date. Each number has its own What sentence, so two numbers in one sentence never share one unless they come from the same record and open the same thing. The tooltip shows no number the page does not show, as fairshare's never did (notes line 77), with one exception DESIGN.md already makes: a rounded amount's tooltip gives the record's own unrounded value (DESIGN.md, Signal line: "whose popover gives the record's exact Estimated Amount") |
| 2 | **Click a number, land on its rows.** The click opens the rows behind it and scrolls to them | `web/src/components/Answer.tsx` lines 75 to 78 and 138 to 147; `Document.tsx` lines 101 to 105 | The package workspace: a number in the finding or the summary opens "Show the table" under the chart filtered to the rows it counts, scrolls the table's title under the bar and moves focus to the count line, which repeats the pressed number ("Showing the 2 of 49 packages signed within 1.5 months.") with "Show all 49" after it. The first counted row lands at 134 px at 1440 by 900 and 118 px at 390 by 844. Round 3's first pass marked the rows in the unfiltered table instead, which put three still-open packages on screen and the two marked ones below the fold. On the plan check a count word marks its rows, which already come first, and a row's number opens its records in the drawer | The package ticket | The rows are the tool's own rows; the filter states no number of its own, and the count line only repeats the number that was pressed |
| 3 | **The check line with "How was that checked?"** A dotted button after the check line opens a short window on what the checker compared | `web/src/components/Answer.tsx` lines 94 to 110; `web/src/lib/share.ts` lines 53 to 62 | The answer panel, a draft's page, the risks section and section 5's check. The window lists the six checks in the copy file's words (`copy.ts`, `steps.check.six`, the same lines the steps list shows), one sentence on rounding, and the Answer ID or the draft's ID. When the verifier removed a sentence, the window opens on "These counts include the two sentences I removed. The check line counts only the sentences I kept.", because the window counts every sentence written (`checks.checked`) and the line counts those on screen (`checks.shown`); without it a draft's window said "9 of 11" under a line that said "5 of 5" and "4 of 4". A draft's step 2 says "came back for this draft" | The check window ticket | Its counts are the verifier's, from the answer stream or the draft; the window adds no count of its own and says which scope it counts |
| 4 | **The removed sentence stays in view, with its reason** | `web/src/components/Answer.tsx` lines 114 to 119; `web/src/copy.ts` lines 74 to 76 | Strata's removed box already does this (DESIGN.md, Removed box). Round 3 sets it with the check line as one block on `surface-2`, both on the block's text edge, and keeps it neutral, never red | The check window ticket | Removed sentences stay plain text with no Num and no marker, as DESIGN.md says |
| 5 | **A tooltip promises only what the click delivers** | `web/src/components/Term.tsx` lines 5 to 24; the test `web/e2e/smoke.spec.ts` lines 118 to 128 | Number tooltip: the action line ("Select to see the two packages.") shows only when a click opens something, and says what it opens. A range chart's dot has the same three parts as a number, its action line included, because its click opens the drawer. A number with no tooltip and nothing to open is plain text with no underline. A gate test opens every number and every dot whose tooltip has an action line and checks that the promised rows, record or window opened | The number tooltip ticket | Settles ticket 59 lines 36 and 39, where numbers carry the underline but open nothing |
| 6 | **The briefing folds into a strip** | `web/src/components/SummaryStrip.tsx` lines 11 to 19; `web/src/App.tsx` lines 216 to 223 and 276 to 292 | Home: when an answer opens, the briefing folds to its date line and first sentence with "Show the briefing" (`aria-expanded`) | Home | The strip repeats the server's own first sentence, unchanged |
| 7 | **"Worth knowing" lines with one verb each** | `web/src/components/Signals.tsx` lines 9 to 26; `Summary.tsx` lines 103 to 115 | Home's Briefing line already has one action link (DESIGN.md, Briefing line). Round 3 keeps that and splits the panel's middle-dot title (4.3, item 1) | Home | The lines are the server's copy templates with check_plan's values |
| 8 | **Loading as shape** | `web/src/components/Skeleton.tsx` lines 21 to 58 | Already Strata's rule (skeletons sized to their content). Round 3 keeps them static, with no shimmer | Every page ticket keeps it | No number is shown while loading |
| 9 | **The bar that says what the act does, then who did it and when** | `web/src/components/Document.tsx` lines 292 to 307; `web/src/lib/runs.ts` lines 44 to 50 | A draft's page: the draft bar keeps its fixed consequence sentence before the act, and after "Mark as checked" its first row reads "Checked by you on {date}." (`copy.ts`, `draft.tab.checkedYou`), by role. No cross-fade: the text changes at once | Drafts | Roles, never names (rule 31); the date is the server's |

The small ones (`../fairshare/notes.md` line 225): the held label that says what releases it (fairshare's share link label, held until a decision, `web/src/components/Brief.tsx` line 97) is already DESIGN.md's Held button; the count words (`numberWord`, `web/src/copy.ts` lines 2 to 9) are already the server's `num.words`; the one status line per agent in the sidebar (`web/src/lib/runs.ts` lines 71 to 81) would be a "2 to check" beside Drafts, kept for later in `open.md` item 10, because GET /api/me does not carry the count yet.

### 9.2 Adopted later, not in this wave

| Pattern | fairshare file | Why later |
|---|---|---|
| 10. **The related line under an answer**: under an answer about one activity or project, the one Worth knowing line about it | `web/src/components/Conversation.tsx` lines 32 to 45; `web/src/lib/signals.ts` lines 19 to 29 | It fits Strata's rules (the line is the server's, with its marker), and the principle in 8.0 wants it. It needs a server route that returns one object's lines, and this wave changes no route contract. The prototype does not draw it: the recorded answer was asked from Home, where the same line already sits in Worth knowing, and a related line shows only when its line is not already on the page; `open.md` item 9 |
| "Show the query" under an answer | `web/src/components/Answer.tsx` lines 148 to 164 | Strata's numbers come from named tools, and its windows already name the table a measure counted (DESIGN.md, Measure number). A query panel for a borrower's officer adds reading without a decision, and for staff it would need the tools to return their SQL. `open.md` item 11 |

### 9.3 Left out, and why

fairshare's own list (`../fairshare/notes.md` lines 197 to 208), with how Strata stands on each:

1. Hex colors inline: Strata allows tokens only, and the class lint refuses the rest.
2. Strings outside the copy file: Strata's lint fails a component that renders text not from `copy.ts`.
3. The grey text token at about 2.5:1: Strata's `ink-muted` is 6.69:1 on white.
4. **The typing effect**: a reader who wants a source waits up to 2.5 s; Strata shows a checked answer at once.
5. The dotted underline as the only sign of a citation: Strata keeps its markers and source chips; fairshare's hover sentence goes into Strata's tooltip, not in place of the marker.
6. Native `title` tooltips: mouse only; Strata's tooltips open on focus too.
7. Custom DOM events: Strata keeps a context or a store.
8. `mailto:` export and conversations in local storage: Strata's drafts live on the server.
9. The hidden Recent list in the collapsed rail: Strata's rail hides nothing that the open sidebar shows except the stamp, which moves into the Data tooltip.
10. Color as the only sign on bars: Strata's status is always a word.

Also left out from fairshare's motion (`../fairshare/notes.md` line 164): the seconds counter and the timed hints while an answer runs ("This usually takes 15 to 30 seconds"), because a duration on screen is a number no tool returned; views that slide between depths, and rows that rise with a stagger, because they fail the motion gate's frequency question (section 5.7); a count-up on stats, which fairshare itself never did on first paint.

## 10. The number tooltip and the evidence drawer

Both are written as components in `design-md.md` (blocks 13a and 13b). In short:

**Number tooltip.** On a Num or a Measure number. Three parts, each its own line: what the number is (`small`, `ink`), where it came from with its date (`caption`, `ink-muted`), and what a click does (`caption`, `ink`), the last only when a click does it. A light surface with a 1 px `line` edge, 4 px corners, the popover shadow, 8 by 12 px padding, at most 20rem wide, under the number and left aligned with it, above it when there is no room below, never covering the number; a number inside the page's finding opens its tooltip under the whole finding, so it never covers the rest of the sentence being read; a dot's tooltip sits above every dot in its lane, so it covers none, and has the same three parts. It opens 150 ms after a hover and at once on keyboard focus, never because the page scrolled a number under a resting pointer; a second tooltip within 300 ms of the last one closing opens at once with no movement; it stays while the pointer is on the number or the tooltip, and hides 100 ms after it leaves both; Escape hides it until the pointer or the focus leaves the number ([WCAG 2.2, 1.4.13 Content on Hover or Focus](https://www.w3.org/TR/WCAG22/#content-on-hover-or-focus)). It holds no links. It is the number's description (`aria-describedby`), never its name. Dates and "N of M" pairs never break inside it.

**Evidence drawer.** Beside the page from 768 px, a non-modal dialog; a full-screen modal sheet below. It opens at what was clicked, and on a list view it lands on the row that was clicked, marked with `tint`. Its head is the title and one caption sentence, with the 44 px close button. It enters with opacity and 12 px from the right over 160 ms and closes at once. Focus moves to its heading and returns to what opened it. The opener keeps the current mark (a row's `tint` and 3 px bar, a dot's 2 px `info-icon` ring) while the drawer shows it. Its placement (beside or over) is the user's call (`open.md` item 3); over the page it has a `line-strong` left edge as well as the popover shadow, so it reads as lying on top.

## 11. The study's open questions, as the plan answers them

- The local viewer is not in the staff group (`notes.md` section 1). The prototype shows Following, the reviewer pages and Start here as staff and a lesson reviewer see them, and says so.
- GET /api/home answered 404 on the local app, so Home is drawn from the recording the tests use (`tests/fixtures/api/home.json`), not from the live app.
- The blueprint says the Menu takes the tabs below 768 px; the code does it below 1024 px. The redesign keeps 1024 px.
- The package page's h1 stays the STEP Description with the data's own spaces (`open.md` item 12).

## 12. Facts the studies did not have

- None of Linear, Vercel, Supabase or Claude publishes a sidebar width. 224 px and the 64 px rail are Strata's choices.
- The prototype's Home and Drafts come from two recordings taken on different days: `home.json` (today October 28, 2026; two example drafts waiting) and `drafts-list.json` (October 23, 2026; one draft to check, one checked, one exported). So Home says "Two drafts are waiting for you to check" while the Drafts list shows one. Each page is true to its recording; the prototype's controls say so.
- The draft page is `drafts-review-notes-partial.json`, the same draft as the Drafts list's row to check (draft-0002, made October 23, 2026 at 2:16 PM UTC).
- The past range's 49 packages are `comparables-ke-nwwda-541055.json` (as of October 22, 2026). Only KE-NWWDA-229129-CW-RFB's notice record is recorded in full (`activity-ke-nwwda-229129.json`), so other dots open a drawer with the package's months, dates and project, and their notice and award cards show as loading.
- The plan check row's planned completion, the project's closing date and the as-of date are the screenshot's (`current/plan-check-nwwda-1440.png`); the study did not record the row's other planned dates.
- The counts of the reviewer pages were not seen; the prototype shows the items without counts.
- A populated Lessons library, Following and the project page were not seen live.
- The "Longest" data switch puts the longest real value of each kind into one layout, so a page mixes records. It tests the layout, not the facts, and the prototype says so while it is on.
- Whether Open Sans Light reads well on Windows at 28 px was not tested (`open.md` item 8).
- Whether `@starting-style` is supported on the demo laptop's browser was not checked; without it, entrances appear at once.
- No fixture holds a staff check of a plan with no signals. The Empty switch on the plan check keeps the October 9, 2026 plan's three data-note rows and puts the copy file's no-signal finding (`checkPlan.finding.none`) over them, and says so while it is on. The public view's check (`check-plan-p156634-nwwda-2026-10-09-public.json`) is real: it holds the signals back and marks the same three rows.
- The seven comparables of the Few state (`comparables-ke-nwwda-541055-prior.json`) are the same package compared with prior-review packages only. Its zones 2 to 5 keep the package's own 49, because the study recorded no other section for that comparison; the prototype says so while it is on. None of the seven has its notice recorded in full, so their drawers show the months and dates with the notice and award cards loading.
- The officer's and the public Home are previews from a staff account (`home-preview-piu.json`, `home-preview-public.json`). An officer's own Home, with their team's drafts in Waiting for you, was not recorded; the brief for the Home ticket draws it.

## 13. The prototype, and what building it changed

Open `prototype.html` in a browser; it needs only Google Fonts. The dashed "Prototype controls" box lists the eight pages and four switches. The address sets every state, so a link or a screenshot can hold one:

- `?page=home|packages|plancheck|package|projects|lessons|drafts|draft`
- `?rail=auto|labels|icons`: the rail at rest. Auto is the plan (open from 1440 px, a rail from 1024 to 1439 px); labels keeps the sidebar open from 1024 px; icons keeps it a rail with labels in tooltips.
- `?pane=beside|over`: the evidence drawer beside the page, or over its right side.
- `?data=real|long|empty|error`: the fixture's own data, the longest real strings, the empty or few state (on the package page, seven comparables; on the plan check, no signals; on All projects, no match), or each page's failed request.
- `?view=staff|officer|public`: the view, as the bar's view switch sets it. The officer's Home, the public Home, the public sidebar and All projects, the public plan check and the public view's hidden pages are drawn; other pages say what is not drawn.
- `?drawer=dot|open|plan|row0` to `row5` `|note0|note1|line0` to `line2`, `?answer=1` (Home), `?tip=finding|within|plan|home|dot` (a tooltip open: 49, 2, 1.5, a count word on Home, a dot), `?how=1` (the check line's window open), `?rows=within|all|middle|median|q80` (a number pressed, so the table is filtered to its rows), `?view-open=1` (the view switch's popover open), `?checked=1` (a draft after Mark as checked), `?loading=1`, `?menu=open` (below 1024 px), `?changes=open`, `?controls=open` (the controls box open; it starts closed), and `?clean` to hide the controls.

The prototype's source is `prototype.src.html`; `work/build.sh` embeds the logo file into `prototype.html`. After the second critic's review, `work/shoot4.cjs` took 106 screenshots into `shots4/` (every page at 1440, 1024 and 390 px; every page in Longest, Empty or few and Error at 1440 and 390 px; the press, tooltip, drawer, view and window states), and `work/cli4.cjs` retook the orchestrator's CLI shots in this folder (`proto-1440.png`, `proto-1024.png`, `proto-390.png`, `proto-1440-longest.png`, `proto-390-longest.png`, `proto-1440-switches.png`, plus `proto-1440-few.png` and `proto-390-press2.png`). `work/axe4.cjs` ran axe with the repo's WCAG 2.2 AA tags in 105 states (every page in every data state at 1440 and 390 px, at 1024 and 320 px, in the officer and public views, and the new tooltip, press, window and drawer states): no violation, no page error, and no width scrolls sideways. `work/words4.cjs` and `work/words-twin.cjs` found no word broken inside itself on any page at 1440, 1280, 1024, 390 and 320 px in any data state, the past range's open table included. `work/copyscan4.cjs` found no dash, curly quote, exclamation mark, middle dot or rule 19 word apart from DESIGN.md's two fixed sentences. Round 3's first pass is described below: its screenshots are in `shots3/` (`work/shoot3.cjs` took 79 states, `work/focus3.cjs` the focus and hover states), and the CLI shots the orchestrator asked for are `proto-1440.png`, `proto-1024.png`, `proto-390.png`, `proto-1440-longest.png`, `proto-390-longest.png` and `proto-1440-switches.png` in this folder. `work/axe3.cjs` ran axe with the repo's WCAG 2.2 AA tags in 53 states (every page at 1440, 1024, 390 and 320 px, every drawer view, both placements, the Menu sheet, the rail, a tooltip, both windows, the answer on Home, a checked draft, the Longest and Empty data): no violation, and no width scrolls sideways. Its target probe finds only the hidden skip link, the citation markers (inside sentences, 20 px with a padded hit area) and the chart's dots (exactly 24 px). `work/copyscan3.cjs` read every page's visible text: no dash, curly quote, exclamation mark, middle dot or rule 19 word, apart from DESIGN.md's two fixed sentences (the footer and the draft bar's). `work/focus3.cjs` measured the number tooltip: closed 60 ms after the pointer arrives, open by 260 ms, and the next number's tooltip open at once with no movement.

Measured (`work/shoot3.cjs`, `work/measure3.cjs`; checked again with `work/shoot4.cjs` and `work/measure4.cjs`, which give the same tops):

| Window | Rail at rest | Package: finding's top | Package: chart | Plan check: first marked row | Home: finding | Draft: finding (the lede) |
|---|---|---|---|---|---|---|
| 1440 x 900 | open (by width) | 373 px | 563 px | 607 to 772 px | 116 to 260 px | 200 px |
| 1440 x 900 | icons | 373 px | 647 px | | | |
| 1280 x 800 | rail (by width) | 373 px | 563 px | 607 to 772 px | 116 px | |
| 1280 x 800 | labels | 397 px | 890 px (one column, facts line) | | | |
| 1024 x 768 | rail (by width) | 429 px | 810 px | 619 to 784 px | 116 px | 232 px |
| 1024 x 768 | labels | 429 px | 650 px | | | |
| 390 x 844 | Menu sheet | 593 px | 324 px | 854 px (finding at 429 px) | 160 px | 296 px |
| 390 x 844, Longest | Menu sheet | 773 px | 324 px | finding at 429 px | | 320 px |
| 320 x 640 | Menu sheet | 637 px | 254 px | | 160 px | |

After pressing "2" in the finding, the first counted row's top is at 134 px at 1440 by 900 and 118 px at 390 by 844, under the table's title and its count line, which has focus; "49" lands its first row at 122 px, and "9.1" at 134 px. In the Few state the finding starts at 385 px at 1440 by 900 and 605 px at 390 by 844. The plan check draws six columns at 1440 and 1280 px and three at 1024 px; with no signals its finding starts at 225 px. A number's tooltip in the finding opens 6 px under the whole finding (487 px under a finding that ends at 481 px). With the drawer open on the package page at 1440 px it fills x 945 to 1440 (495 px) and the work keeps its place; over the page it is 560 px from x 880. On the plan check at 1440 px the drawer beside the page is 560 px and the table keeps three columns. With Longest on, the package page's 257-character h1 takes six lines at 1440 px and the finding still starts at 545 px.

What building it changed, after looking at the screenshots:

- **Waiting for you and a draft's state were hidden below the threshold.** Both side panels used the package page's rule that folds the side panel into a facts line. Home's side panel now follows Worth knowing, and a draft's stepper takes one line in the head while the rest follows the draft, because the full panel first pushed the lede to 586 px at 390 px.
- **The answer panel ran across both columns on Home.** It now takes columns 1 to 7 above the head, beside Waiting for you.
- **The related line repeated Worth knowing on Home.** It came out of the prototype (9.2).
- **IDs broke inside a part** ("KE-NWWDA-229129-CW-" / "RFB"). Each part of an ID between spaces now stays on one line, as DESIGN.md's Reference words already ask, and links that hold an ID are inline blocks, so a space inside them is never lost.
- **The box's placeholder was cut at 390 px**, as measured in 7.10.
- **The longest title pushed the finding below the first screen at 390 px** (889 px). The h1 now steps down to 20/28 below 48rem; the finding starts at 773 px.
- **The past range's table broke its headings into syllables at 563 px.** It now turns into cards below 49rem of its own width, as DESIGN.md's `cardsBelow="fit"` says, with the reference as each card's heading and the other values in a grid of 120 px columns.
- **A dot's tooltip covered the dots above it.** It now sits above the whole lane.
- **The notes panel repeated the h1 ("Review notes").** It now opens on its count line.
- **The controls box covered the side panel at 1440 px.** It starts closed, as a small dashed button at the bottom right.

After the second critic's review, looking at `shots4/` changed six more things:

- **A hidden block left a 16 px gap.** The zone body's spacing counted blocks the Data switch hides, which pushed the finding from 373 to 389 px. Space now falls only between shown blocks.
- **Pressing "2" opened 4.4's tooltip at 390 px**, because the scroll slid 4.4 under the resting pointer. A tooltip now waits for the pointer to move after a scroll (5.7).
- **The past range's open table broke "signature," at 1024 px**, where the table is 810 px wide and keeps its columns. The Months column, which carries its definition under its name, is wider now.
- **The public plan check's breadcrumb started at Packages**, a section the public view does not have. It starts at the project, and Projects is lit.
- **A draft that failed to load still showed its project's scope chip.** The chip now waits for the draft.
- **The officer's P-code outweighed the light finding around it** (Roboto Mono 500, underlined, at 28 px). An ID inside the finding now takes Roboto Mono 400, which DESIGN.md section 3 already self-hosts.

## 14. What the redesign does to the polish tickets

| Ticket | Settled in full | Settled in part or made moot | Stays |
|---|---|---|---|
| 56, timing tests | | | All; land it after the redesign's specs are rewritten |
| 57, the gate's checks | | The two whitespace items in specs the shell tickets edit | The rest |
| 58, copy | The Menu label at 320 px (line 129) | The plan-mode placeholder cut at 390 px (line 83); the two dates on one screen (line 72); the drawer's eyebrows and middle dots; the three panel titles with middle dots (4.3, item 1, and the public Home's "Closed projects"), whose words 58 writes; the second critic's rule 12 and 13 strings that now render larger, the plan check finding's missing noun and the Kaplan-Meier sentence (8.6) | Every other string |
| 59, layout | The page column moving when the drawer opens (line 44); short states pulling the footer up (line 50); the Lessons purpose above the sub-tabs (line 81); the planned package's header (line 64); the draft's state with no fixed place (line 87); the section name outranking the finding (line 61); three empty states in two sizes (line 60); the check line's indent (line 29); numbers with an underline that open nothing (lines 36 and 39); tooltips that split a date (line 35); the drawer stopping with a tab under its header (line 27); Term and Num spacing in "In short" (line 25); the answer ID breaking after "run-" (line 30) | The Data pages laid out by the window (line 40) and the Fact table widths (line 47), which the sidebar forces | Charts, skeleton heights and the other items |
| 60, accessibility | The 37 px sideways scroll at 1024 px and the wordmark touching Menu at 320 px (line 47); the skip link covering the logo (line 46); the shell captures with a load error on /lessons (line 72); a dot's tooltip after Escape or a click (lines 40 and 41); no capture of a number's tooltip in an answer (line 71) | A wrapped link's focus ring through the line above (line 45), if the tokens ticket takes the global focus rule | The live region, judging, preview and recording items |
| 61, the verifier | | | All |
| 62, app code | The sticky padding rule in two hooks (line 71) | Breadcrumb's doubled class strings (line 71); the project tab order in two lists (line 66) | The rest |
| 63, the data side | | | All |
