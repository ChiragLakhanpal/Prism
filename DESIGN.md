# Strata design

Every screen, slide, proposal figure and diagram in Strata follows this file. A deviation needs a line here first.

Strata follows the World Bank's public design and editorial conventions, carries the World Bank logo in the private demo, and says plainly on every screen that it is an independent demo. Each choice is marked **WB** (published or shipped by the World Bank) or **Strata** (our decision or deviation, with the reason). Where a skill such as `diagram-design` or `hairline` has its own rules, follow its rules for structure and this file for color, type and voice.

Sources, checked October 22, 2026: the live CSS of worldbank.org (`/ext/styles/components-variable.css`, `styles.css`), data.worldbank.org, projects.worldbank.org and financesone.worldbank.org; The Loop design system (archived 2018 to 2021); the World Bank Data Visualization Style Guide (draft, updated March 19, 2025) and its `wbplot` package; the World Bank Group Publications Editorial Style Guide (2020); the World Bank Legal page, Terms and Conditions (amended July 25, 2025) and dataset terms.

## 1. Principles

1. **Evidence first.** Every number, chart, table and card ends with a source line.
2. **Quiet and blue.** White surfaces on a pale page, navy headings, one blue for action. Other colors mark a state or a data category.
3. **Plain words.** Full sentences a 10th grader follows, in World Bank editorial style.
4. **Accessible.** WCAG 2.2 AA. Nothing depends on color alone.
5. **World Bank look, honest label.** Use the World Bank's public conventions and its logo, and never claim to be an official World Bank product.

Light theme only: the World Bank publishes no dark theme.

## 2. Color

| Token | Hex | WB source token | Role |
|---|---|---|---|
| `page` | `#f5f7f9` | neutral-solid-05 | App background |
| `surface` | `#ffffff` | white | Cards, tables, dialogs, every chart |
| `surface-2` | `#e7edf3` | neutral-solid-10 | Table headers, quiet panels, meter track |
| `tint` | `#e9f7fd` | blue-10 | Selected row, active citation, secondary-button hover |
| `tint-hover` | `#f6fcff` | blue-05 | Row hover, ghost-button hover |
| `line` | `#dae3eb` | neutral-solid-15 | Decorative hairlines only |
| `line-strong` | `#586e84` | neutral-solid-50 | Input borders, axis lines. Strata: WB's 24% alpha outline is 1.57:1 |
| `ink` | `#181f25` | neutral-solid-90 | Body text |
| `ink-heading` | `#012740` | blue-90 | Headings, wordmark |
| `ink-muted` | `#4b5e71` | neutral-solid-60 | Secondary text, source lines. Strata: WB's 57% alpha text falls to 4.40:1 on `surface-2` |
| `primary` | `#004370` | blue-70 | Links, primary buttons, selected tab, meters |
| `primary-hover` | `#00538a` | blue-60 | Primary button hover. Strata: WB's hover pair is 3.41:1 |
| `primary-pressed` | `#012740` | blue-90 | Pressed |
| `link-hover` | `#066db1` | blue-55 | Link hover |
| `focus` | `#b6490c` | keyboard-focus-on-light | Focus outline |
| `focus-on-dark` | `#f5926c` | keyboard-focus-on-dark | Focus outline on the navy bar. Strata: `focus` is 3.01:1 on navy |
| `highlight` | `#fff1b8` | Strata (the blueprint's highlighter) | Matched words in a quoted passage, under `ink` text |
| `navy` | `#002244` | brand navy | The top navigation bar only |
| `scrim` | `rgba(0,13,26,.57)` | Strata | Behind a full-screen sheet below 768 px |
| `bright` | `#169af3` | blue-40 | Decoration on white only, never text |

| State | Background | Text | Icon, border | Icon (lucide) | Strata meaning |
|---|---|---|---|---|---|
| info | `#f6fcff` | `#00538a` | `#0071bc` | `info` | New, note |
| success | `#f6fef0` | `#388004` | `#388004` | `check` | Confirmed, checked |
| warning | `#fef3d7` | `#473201` | `#896001` | `triangle-alert` | Conflict, stale |
| error | `#fdf2f2` | `#9d161d` | `#c91c25` | `circle-x` | Failed |
| neutral | `#e7edf3` | `#3d4c5c` | `#586e84` | `circle-dashed` | Gap, not enough evidence |

| Foreground | Background | Ratio (WCAG 2.x) | Use |
|---|---|---|---|
| ink | surface / page / surface-2 | 16.65 / 15.50 / 14.11 | Body |
| ink-heading | surface / page | 15.38 / 14.32 | Headings |
| ink-muted | surface / page / surface-2 / tint | 6.69 / 6.23 / 5.67 / 6.11 | Secondary text |
| primary | surface / page / surface-2 / tint | 10.31 / 9.60 / 8.74 / 9.42 | Links |
| white | primary / primary-hover | 10.31 / 8.06 | Button text |
| link-hover | surface | 5.48 | Link hover |
| state text | its own background | info 7.79, success 4.78, warning 11.03, error 7.47, neutral 7.46 | Badges, alerts |
| focus | surface / page / surface-2 | 5.32 / 4.95 / 4.51 | Focus ring (needs 3:1) |
| focus-on-dark | navy | 7.02 | Focus ring on the navy bar (needs 3:1) |
| white | navy | 16.00 | Wordmark, tabs, the view switch and the selected tab's underline |
| line-strong | navy | 3.03 | Tab hover underline on the navy bar (needs 3:1) |
| ink / ink-muted | highlight | 14.69 / 5.90 | Highlighted words. The fill is 1.13:1 on surface, so screen readers also hear where a highlight starts and ends |
| line-strong | surface / page | 5.28 / 4.92 | Control borders (needs 3:1) |
| bright | surface | 3.02 | Non-text only |
| chart-cat1-text `#106ca1` | surface / chart-grey200 | 5.70 / 3.83 | Range chart dots (essential marks need 3:1) |
| chart-grey500 / chart-grey400 | chart-grey200 | 12.68 / 3.85 | The middle tick and the 8-in-10 line on the band |

```css
@theme {
  --color-page: #f5f7f9;  --color-surface: #ffffff;  --color-surface-2: #e7edf3;
  --color-tint: #e9f7fd;  --color-tint-hover: #f6fcff;
  --color-line: #dae3eb;  --color-line-strong: #586e84;
  --color-ink: #181f25;  --color-ink-heading: #012740;  --color-ink-muted: #4b5e71;
  --color-primary: #004370;  --color-primary-hover: #00538a;  --color-primary-pressed: #012740;
  --color-link-hover: #066db1;  --color-focus: #b6490c;  --color-bright: #169af3;
  --color-focus-on-dark: #f5926c;  --color-highlight: #fff1b8;
  --color-navy: #002244;  --color-scrim: rgba(0,13,26,.57);
  --color-info-bg: #f6fcff;  --color-info: #00538a;  --color-info-icon: #0071bc;
  --color-success-bg: #f6fef0;  --color-success: #388004;
  --color-warning-bg: #fef3d7;  --color-warning: #473201;  --color-warning-icon: #896001;
  --color-error-bg: #fdf2f2;  --color-error: #9d161d;  --color-error-icon: #c91c25;
  --color-neutral-bg: #e7edf3;  --color-neutral: #3d4c5c;
  --color-chart-text: #111111;  --color-chart-text-subtle: #666666;  --color-chart-cat1-text: #106ca1;
  --color-chart-grey200: #ced4de;  --color-chart-grey400: #666666;  --color-chart-grey500: #111111;
  --font-sans: "Open Sans", "Open Sans Fallback", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "Roboto Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --radius-xs: 2px;  --radius-sm: 4px;  --radius-md: 8px;  --radius-lg: 16px;  --radius-pill: 32px;
  --radius-box: 22px; /* the one box: half its 44 px height */
}
```

The `chart-*` tokens are section 6's chart text, greys and cat1's text variant, kept here as tokens so a chart draws from them and the token test checks them.

Brand navy `#002244` (`navy`) is used only for the top navigation bar that carries the logo, as The Loop specifies; text on it is white (about 16:1). Brand blue `#009fda` is used sparingly and never for text.

On the navy bar, the selected tab's underline is white and the hover underline is `line-strong`, and the focus outline is `focus-on-dark` (`#f5926c`, WB keyboard-focus-on-dark, 7.02:1 on navy). Strata: `primary` on navy is 1.55:1, so `primary` underlines tabs only on light surfaces.

## 3. Typography

| Role | Family | License | Stack |
|---|---|---|---|
| All text, UI and charts | Open Sans 400, 600, 700, italic 400 | SIL OFL 1.1 | `--font-sans` |
| IDs and codes (P123456, KE-MOWASCO-16771-CW-RFB) | Roboto Mono 400, 500 | SIL OFL 1.1 | `--font-mono` |
| Arabic-script titles | Noto Naskh Arabic | SIL OFL 1.1 | Appended to the sans stack, as data.worldbank.org does |
| Not used | Andes (Latinotype) | Commercial | worldbank.org now sets headings in Open Sans 700, and so does Strata |

Self-host with `@fontsource/open-sans` and `@fontsource/roboto-mono`. Define `Open Sans Fallback` as `local(Arial)` with `size-adjust: 105.22%; ascent-override: 101.58%; descent-override: 27.84%` (FinancesOne's values) to prevent layout shift.

| Token | Size / line height | Weight | Color | Use |
|---|---|---|---|---|
| `display` | 32 / 1.2 | 700 | ink-heading | Deck titles |
| `h1` | 28 / 1.2 | 700 | ink-heading | Page title |
| `h2` | 24 / 1.25 | 700 | ink-heading | Section |
| `h3` | 20 / 1.3 | 700 | ink-heading | Subsection |
| `title` | 18 / 1.3 | 700 | ink-heading | Card and table titles |
| `body` | 16 / 1.5 | 400 | ink | Text |
| `small` | 14 / 1.45 | 400 | ink | Tables, badges |
| `caption` | 13 / 1.5 | 400 | ink-muted | Source lines, notes |
| `label` | 12 / 1.2 | 600, uppercase, +0.02em | ink-muted | Eyebrows |
| `button` | 14 / 24 | 700, -0.5px tracking | | Buttons |

Every size is a step on the World Bank's scale. Use sentence case, tabular numerals in tables and charts, and italics only for publication titles.

## 4. Space, grid, shape

| Token | Value | WB source |
|---|---|---|
| Space | 2, 4, 8, 12, 16, 24, 32, 40, 48, 64 px | spacing tokens |
| Grid | 12 columns; gutter 16 / 24 / 32 px (below 768 / from 768 / from 1024); margin 28 / 48 / 72 px; max width 1456 px | grid tokens |
| Breakpoints | 768, 1024 (1200, 1400 for wide tables), written in rem (48rem, 64rem, 75rem, 87.5rem) so a larger default font size reaches them sooner. Strata: 360 (22.5rem) is used only by the navigation's Menu button. Strata: under the band, a page lays out by the page area's width, not the window's, because the evidence drawer narrows it: the page column is a size container, the same four widths are container queries on it (`@md/page:`, `@lg/page:`, `@xl/page:`), and its margins and gutters follow them. The bar and the band follow the window | worldbank.org media queries |
| Radius | Pill: buttons, search, badges. 8: cards, inputs. 4: images. Strata: the one box takes 22 px (`radius-box`), a pill on one row that keeps its corners when a chip wraps it to two | border-radius tokens |
| Elevation | Cards: none, use `line`. Popovers and dialogs: 1px `line` and `0 5px 25px rgba(160,158,143,.25)` | worldbank.org section shadow |
| Scrim | `scrim`, `rgba(0,13,26,.57)` | Strata |
| Targets | 24 x 24 px minimum; buttons 44 px tall | WCAG 2.5.8 |

## 5. Components

- **Top navigation** (WB). Navy `#002244` bar, 56px tall: the logo, then the Strata wordmark (which links Home), then five tabs (Packages, Projects, Lessons, Drafts, Data), with the view switch ("View: World Bank staff ▾") on the right. The view switch is a 32 px pill, like a chip (section 10), so the five tabs and the pill fit in the bar from 1024 px. Under it, a white band holds the one box (search a project, check a plan, describe a package, or ask; "/" focuses it, and it lists what Enter will do) and the data-freshness stamp. Nouns navigate; verbs act. Below 1024 px (64rem) a labeled Menu button holds the tabs and the view switch, because the bar is 856 px wide with all five tabs; below 360 px the button stacks its icon over its label. The logo slot gives the logo clear space of half its height on every side, and 24 px before the wordmark, so the logo and "Strata" never read as one name.
- **Buttons** (WB). Pill, 2px border, 14px bold. Primary: `primary` fill, white text. Secondary: `primary` outline, `tint` hover. Ghost: `primary` text, `tint-hover` hover; on the `page` background a ghost button hovers to `tint` (`onPage`), as "Show them" and "Show all agencies" do. A ghost button in a column of text sits flush: 8 px side padding and no side border, pulled left 8 px, so its icon starts on the text's edge, its label on the edge of a list under it, and its hover fill and focus ring stay inside a card's 16 px padding. Buttons act; links navigate.
- **Tabs.** 16px bold; the selected tab gets a 3px `primary` underline on light surfaces (Strata: WB's `#169af3` underline is 2.81:1) and a 3px white underline on the navy bar (Strata: `primary` is 1.55:1 on navy). Five tabs at most. Tabs that change the address are links with `aria-current`, not ARIA tabs. Tabs on a light surface never wrap. When the row is wider than its column, as five section tabs are below 48rem, it scrolls sideways inside its own strip, with the hairline under the whole strip. The selected tab starts in the middle of the strip, or at the row's end when the middle is less than 32 px from it. Each side with more tabs out of sight fades out over 32 px, so a reader can tell the row goes on. A tab that gets keyboard focus scrolls clear of the fade, with its whole focus ring in view. A click or a tap never scrolls the strip, and once a reader has pressed, scrolled or focused it, the strip never moves by itself. So a press lands on the tab it was aimed at.
- **Cards** (The Loop). `surface`, 1px `line`, radius 8. Titles 80 characters or fewer, blurbs 140, eight cards per group at most.
- **Tables.** Title sentence, count line ("Showing 1–20 of 99 sources"), `surface-2` header, units in column heads, numbers right-aligned, source line below. The title, count and source lines show only with the rows. While the rows load, skeleton lines hold their places under the real column heads, at fixed column widths, and a title that is a short name, such as "All projects", keeps a one-line skeleton at every width; an empty table shows only its empty-state card, and a failed one only its error alert. Below 768 px each row becomes a card. A table whose columns need more than the 672 px a 768 px screen leaves, such as the plan check and the past range's table, becomes cards below 1024 px instead (`cardsBelow="lg"`). A table never scrolls sideways inside its frame. A table that keeps to columns 1 to 8 does so only from 1200 px, and takes all 12 columns below that, as a project's plan versions do. The row's name is its heading. Each column head sits above its value, the head in `caption` `ink-muted` and the value in `small`. Every value starts at one left edge. Text runs the full width of the card. When a card has two or more numbers or short values (a date, a country, a project's status such as Active), they share a grid of 120 px columns, numbers in tabular numerals. Each field sits at the bottom of its grid row, so the values in a row line up. A column head that carries a definition under its name, such as the past range's Months, shows only its name in the cards, and the definition ends the count line's row once while the rows are cards, as its own element beside the count that wraps to a line of its own when the two don't fit (`cardHeader` and `cardsNote`).
- **Alerts.** State background, 4px left border, icon, one sentence.
- **Icons.** The World Bank's icon font is not public; use `lucide-react` (ISC). Icon-only buttons need an `aria-label`.

| Strata component | Spec |
|---|---|
| Evidence card | Card with a `label` eyebrow naming the stratum (names as in GLOSSARY.md), a `title`, a quoted excerpt of two or three sentences with the matching words highlighted, and a source line ("Source:" bold, document type, project ID in mono, date, paragraph and page). Citation number top right. Claims are past tense. Strata: the eyebrow reads "Why · evaluation", "How · operations" or "What · record", from the stratum the answer stream names; the title names the source ("Rajasthan Road Sector Modernization, paragraph 54"); "You have opened this source." follows the source line once it was opened. A passage with no paragraph number, such as an ISR's, is named by its section wherever a paragraph would be: "section Project Development Objective Indicators", never the internal key "s4". A no-break space keeps "paragraph" and "page" with their numbers. A sentence ends only at a stop before a space, so a number such as 80.00 stays whole. The excerpt holds the sentences the match is in, then the sentence before and after while it stays within 280 characters. Only when the match's own sentences are longer, as in an ISR's table text, is it cut between words, never inside the match, with "…" where it was cut. A record's card ends with the drawer's source line for that record. It is a popover `min(360px, 100vw − 56px)` wide that opens 150 ms after hover and at once on focus, holds no links or buttons, and never opens on a tap. It never opens on the marker whose source the drawer shows in full. When the drawer closes and gives focus back to the marker, or the page moves the marker back under a resting pointer, the card stays closed until the focus or the pointer leaves the marker and comes back. |
| Citation marker | Inline `[1]`: 12px bold `primary`, 1px border, pill, 20px tall. Accessible name such as "Source 1: Implementation Completion and Results Report, June 30, 2021, paragraph 54". Hover or focus opens the evidence card; click opens the source at its page; Escape closes. A marker never starts a line. A word joiner ties it to the last word of the sentence it cites, so a reader never takes it for the source of the next sentence. Strata: in an answer the marker is a link to the page with `?evidence=` and its id, so it opens in a new tab; a click opens the evidence drawer instead, and `aria-expanded` says whether the drawer shows its source. Each source is numbered once, in order of first appearance. Visited (opened before): `surface-2` fill, `line-strong` border, `ink-muted` text, and its name ends ", opened", so the sources you have not opened draw the eye. The sentence whose source is open takes the `tint` background. |
| Disagreement card | Both claims side by side (stacked below 768px), in the order they were written, with equal weight, each with its source line and date. One carries the tag "Strata leans on this", one sentence names the rule, and a line says what changes if you keep the other. Warning state and the badge "Two reports disagree" only when it changes a number or claim in the answer or draft; otherwise an info note, "Sources differ". Shown only beside the claim it concerns. Never red: a disagreement is not an error. |
| Check line | Neutral, never green: "Checked: 23 of 23 numbers match records; 14 of 14 quotes are on their pages. Not checked: whether these are the right comparables." Sits under "In short", with the removed box open below it. Strata: its counts are the answer stream's, over every sentence the agent wrote; dates the verifier matched get their own clause ("1 of 1 date matches records"), so "numbers" never counts a date. Its text starts 48 px in, on the removed box's text edge, so the two read as one column, with no icon. |
| Evidence drawer | Opens beside the page, never over it: `clamp(400px, 40vw, 600px)`, about 65 characters a line; a full-screen sheet below 768px. Opens at what was clicked, with a switcher for the claim's other sources, the whole numbered paragraph with the matching words highlighted, "Open at page N" as a link, and "Wrong passage" and "Not useful" grouped at the bottom. 44 px close; focus returns to the marker. The panel keeps a scroll padding as tall as its sticky header, so a focused tab or link is never hidden under it. On open, the drawer scrolls only when the first highlight is out of view, and then centers it under the sticky header. Strata: it is a column beside the page column, under the band, whose panel stays in view as the page scrolls; the page narrows and stays usable, so it is a non-modal dialog, and below 768 px a modal sheet with the page inert behind it. Its heading names the source, because a link can open it with no answer on the page; when a sentence opened it, "From the answer" and that sentence sit under the heading. The meta line ("Implementation Completion and Results Report · Rajasthan Road Sector Modernization (P130164) · October 10, 2019 · Section III.B · ¶54 · PDF page 23 of 66") runs on a `surface-2` strip above the paragraph, with only the project ID in mono. The date, the paragraph, the page and a short section such as III.B each keep to one line. A long section name, such as an ISR's, may wrap. A section's closing ID, such as 1.A in Annex 1.A, stays with the word before it in the heading, the tab and the card's source line. Each dot stays with the part before it, and the project's name keeps its ID beside it. A passage with no paragraph number shows no ¶ part, and its drawer says "section" where it would say "paragraph". A passage backs a number only inside quoted words, so every number a sentence matched to a passage sits inside its quote's highlight. A sentence that cites a passage without quoting it highlights nothing there, and the drawer says so above the passage. The address's `?evidence=` holds it, so a link reopens it and Back closes it; the answer is not in the address. A record cited from the What stratum shows its STEP fields instead of a paragraph: a two-column list under STEP's own names (Description, Method · market approach as the plan check writes it, Review, Estimated (US$) right-aligned in STEP's form with its cents, Process status), then its source line. Its content fades in over 160 ms, then the highlight settles in over 200 ms. |
| Source switcher | In the evidence drawer, one pill tab 32 px tall per source of the sentence it was opened from, such as "ICR ¶54" (heard as "ICR paragraph 54"), or "ISR, Overall Ratings" for a section: `small` text, a 1px `line-strong` border, and the selected tab a `tint` fill with an inset 1px `primary` ring, so nothing changes size. A long tab wraps inside its pill. Left and Right move between them, Home and End jump to the ends, and selection follows focus. Shown only when the sentence has more than one source. |
| Coverage line | A sentence with its denominator: "Based on 37 of 52 matching packages; 15 lacked the STEP reference that links notice to contract." No meter unless it shows that ratio. Links to Data readiness, filtered to the sources behind it. |
| Removed box | Open by default under "In short": the first removed sentence with its reason ("No record supports this number."), then the rest. Neutral state, never hidden behind a link. |
| One box list | Under the box in the band, as you type, a popover at the box's width lists what Enter will do, one rule per kind of input: a project ID offers "Open P130164", a loan number in any of its four forms opens its project, a STEP reference shows its row in its plan, and anything else offers "Ask this". Each option is at least 44 px tall: a 16 px lucide icon, the label with any ID in mono, and a second line in `caption` `ink-muted` that a lookup fills in. The option Enter does has the `tint` fill, a 3 px `primary` bar inset on its left and an "Enter" key hint; hover gives `tint-hover` and does not move it. An ID no record holds, or a lookup that failed, is a `caption` line under the list, not an option. Focused and empty, the popover holds only the hint. Nothing is sent until you choose. |
| Scope chip | Inside the box, before the text, on a project or package page: 32 px tall, pill, 1px `line-strong` border, "Within" in `small` `ink-muted` and the ID in mono (the ID only below 768 px), and a 24 px round remove button. Removing it, or Backspace in the empty box, changes the placeholder and is announced. A new page brings its chip back. The text field keeps room for about ten characters (96 px) beside a P-code's chip, and on a package page for its whole placeholder (176 px), so "Ask about this package" is never cut. When a long STEP reference leaves less, the chip takes a row of its own above the text and the box grows to two rows, with 22 px corners (`radius-box`); the "/" hint stays at the end of the text's row. With a chip the box keeps 4 px inside its border on both sides, so a chip that fills its row sits 5 px from each edge, and the text row keeps 16 px on the right. A press anywhere in the box outside the chip puts the cursor in the text field, and the box shows the text cursor everywhere but on the chip. A reference wider than the chip's row moves to its next line whole when it fits there, and otherwise breaks after a hyphen, so the page never scrolls sideways. On more than one line the chip keeps its 16 px corners. |
| Reference words | A STEP reference inside running text or a chip (`MonoWords`): Roboto Mono, with each part between spaces in its own inline box. A part moves to the next line whole when it fits there, and breaks after a hyphen only when it is wider than the line, so the page never scrolls sideways. A reference with a county's name breaks at its spaces first, and a full stop after it stays with its last part. The scope chip, the package workspace's not-found sentence, the past range's table (its rows and its cards) and a dot's details on the range chart use it. |
| Answer panel | The answer to a question asked from the box, in a card at the top of the page under the band, on columns 1 to 8 from a page area of 1024 px and all 12 below it; it pushes the page down and holds one answer at a time. Page alerts stay above it. The question is its `h2` in `title`, then "Asked within P130164." in `caption`, and "Close the answer" (a 44 px icon below 768 px). It closes the drawer that answer opened. Focus goes back to the box, which still holds the question, with its list shut until you press Down, type or click in it. While it streams, the steps sit on four lines of reserved height, with the steps still to come listed as "To do: ..." in `ink-muted`, above a skeleton of "In short" and the check line. Then "In short", the check line, the removed box and the steps folded into "Show the four steps I took", whose opened list and "Answer ID" line share one left edge, and whose project IDs are in mono. Each number or date the checks matched has a tooltip that says where the value is. A date that a passage backs only as its report's date reads "Matches the date of the completion report for P130164." The lines of "In short" stay 24 px apart, with or without a number in them. A status line announces each step once, then "The answer is ready.". A refusal is plain text under "In short", with no alert and no check line. An error is an error alert with "Try again" (none when no model is connected, since trying again cannot help) and "Answer ID" under it when the run has one. The Asked line names no view until the server applies one (ticket 40). Above an error alert, the steps done so far start on the alert's edge. |
| Readiness tables | First, what you can ask, what it is ready for and what holds it back. Then one row per source: the number first in each cell, then a badge only for Partial or Gap, with definitions in the column headers. Freshness reads "Oct 22 · daily". No composite score. Strata (ticket 16): each column head holds its label, which opens its full definition, and a short definition always on show under it. Number cells are right-aligned stacks: the number in `small` 600, what it counts in `caption` `ink-muted`, then the badge, so numbers line up down each column and the reading order stays number first. The row's name is a row header with its scope as a caption ("All countries, since fiscal 2020"). A known gap, or a source with no measures yet, spans the measure columns with one note, so no cell is blank. A frozen source reads "Jun 2016 · frozen" and documents "Jun 30 · as published"; the date and the schedule each stay whole and the dot keeps to the date, so a narrow cell breaks only after the dot and never runs into the next one. A column the registry gives a source no measure for reads "No measure", or its schedule ("As published"), in `ink-muted`. So does a Fresh cell whose measure has no date ("Not measured yet · as published"), at regular weight, since it is not a value. The source line under each table keeps its date on one line. A limit the source declares ("IDA countries only") is its own `caption` line under what the number counts, so the number keeps its unit. Below 768 px each row is a card whose fields sit at the top of their grid row, not the bottom as in Tables, because each value is a stack of two or three lines and the heads must stay level; each card's labels open their full definitions, as the table's heads do. |
| Measure number | Num for a number a data readiness measure gave. Hover or focus shows "528 of 603 contracts. Measured Oct 23, 2026."; the tooltip always names what was counted. A click or Enter opens a non-modal window titled with the measure's column, or, for a measure that fills no column (a check such as "First listing confirmed", a fix's own measure, or a kind's Ready for measure such as "Passages you can search"), with the measure's own name from the copy file, never a column's. Each window names the table its measure counted, and a gate test opens every number's window on three views of the page and checks its title, definition and table against the registries. The window gives that definition, its numerator and denominator, when it was measured and the table it counted in `--font-mono`, which a narrow window breaks only after a dot ("strata.silver." then "plan_listings"). A number that is neither, such as a shortfall ("Missing 75"), is the window's first row, so the window always shows the number that opened it, and a shortfall's tooltip names what its records lack ("75 of 603 contracts lack a STEP reference."), or, for Read well, that I couldn't read them ("30 of 175 body pages I couldn't read without errors."). A share arrives from the tool already rounded ("88%", "about 8 in 10"); the browser divides nothing, and the line breaks only after its comma, so "20 of 21," and "more than 9 in 10" each stay whole. Escape or the 44 px close returns focus to the number. A short number pads its hit area to 24 px with a layer over it, never its type. |
| Range chart | Two lanes on one month axis (see section 6). Lane 1, the past range: each dot one real comparable package, hollow for packages still open. Lane 2, the time estimate: a navy bar for the middle half, a thin line to the 8-in-10 point, a white notch at the middle. The plan is a full-height line through both lanes with a count readout ("4 of 40 signed within 6 months"), draggable with keyboard and number input. The title is the finding; a sentence says why the lanes differ. |
| Draft bar | Sticky bottom bar on drafts, 1px top `line`, held to the document column. Left: what exporting does and is not ("A working draft for the borrower's PPSD. Exporting sends nothing and is not a World Bank review, clearance or no-objection.") and "You opened 3 of 14 sources". Right: Mark as checked (primary), Export to Word (secondary), with Discard set apart and undoable. States: Draft → Checked by you → Exported. Ends on a success state. |
| Following row | 2px top divider. Status first, then the project name as a link; country and project ID (mono) and closing date; the signals that put it there, one line each, past tense, with counts; one next action ("Add to mission brief"). The status definition sits on the column header. |
| Status badge | Pill, padding 4/12, 16px icon, 14px text. One icon shape per state; the text always names the state: Needs a look (warning, `triangle-alert`), Watch (info, `info`), No signals (neutral, `circle`, an empty ring, never a check mark). Data readiness adds Partial (warning, `triangle-alert`) and Gap (neutral, `circle-dashed`, dashed border); plan checks add Data note (neutral, `circle-dashed`, dashed border). A dashed border marks something missing from the record. Badges mark exceptions only. |
| Page header | Every page's `h1`, then one or two short sentences in `body` `ink-muted` that say what the page is for, at most 65 characters a line, 8 px under it, so someone arriving from a link is never stranded. The `h1` takes focus when a route change moves to it. An ID from the address shows in Roboto Mono 500 and wraps after its hyphens. In an empty state's balanced title, an ID such as a STEP reference moves whole to a line of its own when it fits there, and breaks after its hyphens only when it is wider than the line. Above the header, columns 1 to 8 hold the alert slot: one-sentence alerts, errors first, 24 px above the title when it holds any. |
| Eight columns | `EightColumns`: columns 1 to 8 of the 12-column grid, and the full width below its breakpoint. Alerts, empty states and prose keep to them from 1024 px, and prose also stops at 72 characters. A table keeps to them only from 1200 px (see Tables). It has no look of its own, so it has no gallery page. Check a plan, a project's page and All projects show it in use. |
| Empty-state card | A card with a 24px `circle-dashed` icon in `line-strong`, a first-person sentence as its heading in `title` ("I have nothing to brief you on yet."), one or two `body` sentences that say what will appear and what fills it, and at most one link. No illustration and no shadow. |
| Freshness stamp | `caption` in `ink-muted` with tabular numerals, a link to the Data page with a dotted underline. States: a static skeleton for the first second, "Reading the data date", "Data through Oct 21" (the year is added when it is not the current one), "No data loaded yet", and "I can't read the data date." with a `circle-x` icon. Not a live region. It shows the earliest day a daily source was last loaded, so it never claims more freshness than the stalest one. |
| Highlight | Matched words in a quoted passage: `highlight` fill under `ink` text. Screen readers hear "Highlight starts." and "Highlight ends.", because most do not announce a `<mark>`. |
| Breadcrumb | The trail above a project's pages, in `caption`: each step a link except the page you are on, which carries `aria-current="page"`, with `chevron-right` separators hidden from screen readers. Open Sans, with only an ID such as the project ID in Roboto Mono. Below 768 px only the parent shows, as a link back with a `chevron-left` ("< Procurement"), because the whole trail would take three lines. |
| Check pill | How much Strata checked, such as "9 activities checked" or "8 of 9 activities fully checked": a neutral pill (`neutral` background and text, 1px `line-strong` border, padding 4/12, `small` 600) with no icon, which keeps it apart from a status badge. Not a control. |
| Plan check table | Check a plan's rows in STEP's columns (Activity, Method · market approach, Review, Estimated (US$), Process status, What Strata found). The title is the finding, an h2 in `title`, over the method sentence; then the count line ("Showing 6 of 9 activities"). Marked activities come first, by their strongest mark; each mark's badge sits on its own line above its past-tense reason. Rows with no signals fold into a last row on the `page` background that names them ("Three more activities have no signals: ...", or only how many from four) with a ghost "Show them" right after the sentence; the folded rows open after it with "No signals.", and the sentence stays. Below 1024 px the rows are activity cards: the badges and the reference make the heading, then the Description, the reasons, a hairline and the four STEP fields in the cards' grid of 120 px columns. Method and Process status take the card's full width, because STEP's values, such as "Pending Implementation", are wider than one column, and Review and the amount share a row. The count line's row then ends with the What Strata found definition, since cards have no column heads. In the Method cell the middle dot stays with the Method and the Market Approach moves to the next line whole, so no line starts with the dot or STEP's dash. The header (agency name as the h1, the plan's date, the check pill) sticks from 1024 px with a hairline under it. A blank STEP value reads "Not in the plan", never a dash. A link whose hash names a reference opens the fold if it must, focuses that row, and gives it the selected row's `tint`. Each activity's Activity cell, or the foot of its card, ends with a `small` "See the past range" link to its package workspace, whose accessible name adds the reference. The page lands from its top when the whole row or card, badges included, fits on the first screen. Otherwise the row or card lands just under the sticky header. The page never stops with the box band or the title cut at the top edge. |
| Package header and facts | The package workspace's `h1` is the package's Description from its plan row, over its STEP reference in Roboto Mono 500, with a hairline under both. It sticks from a page area of 768 px (not below, where it carries no action and would hold an eighth of a phone screen, or a quarter of the page beside the evidence drawer), and the page keeps scroll padding at its height plus 16 px. Like every width on the page, 768 px here is the page area's, as section 4 says. Beside the evidence drawer, the workspace looks as it would in a window as wide as its page area. Under it, the purpose line, then the package's facts as a definition list in STEP's field names, word for word: Method, Market Approach, Review Type, Estimated Amount (US$), Process Status and "In the plan", a link back to the plan check with the row in view. Labels in `caption` `ink-muted`, values in `small`, three columns from a page area of 768 px and two below. A blank value reads "Not in the plan row". On the not-found page, the reference in the sentence reads as one word: it moves whole to the next line with the full stop after it when it fits there, and when it is wider than the line, breaks after a hyphen like any ID, so the page never scrolls sideways. One with a county's name breaks at its space first. |
| Plan control | Above the range chart: the visible label "Planned months", a text input (`inputmode="decimal"`, 88 x 44 px, radius 8, 1px `line-strong` border, value right-aligned in tabular numerals), the word "months", and a `caption` helper line that names the plan row's planned notice and signing dates. A text input, so a scroll wheel never changes the plan. It takes 0.5 to the thresholds file's maximum, with one decimal and a comma as the decimal mark; an invalid value leaves the line where it was, sets `aria-invalid` and shows one `caption` sentence in `error` text. When the value differs from the plan row's own, a flush ghost "Use the plan's N months" button shows at the row's end from 768 px, and below that in the helper's place, which holds the taller of the two, so no empty row sits between the control and the chart (the hidden helper still describes the input); when pressed, it gives focus back to the input. The error line sits between the input and the helper. The button's place and one `caption` line for the error are held while they are hidden, so showing either moves nothing. After a reader types months into a row with no plan dates, the helper says the line shows the months typed. |
| Dot tooltip | A range chart dot's details on hover or focus: `surface`, 0.5px grey200 border, radius 4, padding 8/12, the popover shadow, as wide as its content up to 240 px (so it never shrinks to the room left at the chart's edge), above the dot and every dot within reach of its width whenever that fits inside the card, and below them all otherwise, so it covers no dot; clamped inside the chart's width. Header in `s` semibold (a STEP reference in Roboto Mono), the months in `m` bold, then one `s` line in textSubtle. It shows at once, stays while the pointer is on it or on its dot, and its text can be selected. While the pointer moves toward the tooltip, inside the band from where it last was on its dot (8 px each side) to the tooltip, the tooltip keeps its dot even over other dots, and shows another dot only after the pointer rests on it for 100 ms. A pointer moving along the dots leaves that band at once, so the tooltip follows it. It hides 100 ms after the pointer leaves both, and Escape hides it until another dot is visited. A tapped dot keeps its tooltip until the next tap outside it, because a finger lifting off is not the pointer leaving. Hidden from screen readers, because the dot's accessible name says the same. |
| Project header | A project page's `h1` and purpose, then labelled pairs (Project ID in Roboto Mono, Country, Status, Implementing agency or agencies), labels in `caption` `ink-muted` and values in `small`, 24 px apart and wrapping, two columns below 768 px. The agencies take a row of their own, set apart with semicolons because some names hold commas. The agencies keep to two lines, with a ghost "Show all agencies" after them when there are more. The button sits 4 px below the names, so its focus ring stays off them. While the project loads, the `h1` holds the project's ID for a screen reader. Its bars hold a name of about 40 characters, such as P156634's: two lines below 1200 px and one from 1200 px. The header shows the same pairs as bars, with the agencies' two lines and the button's place. A longer name moves the tabs down by a line or two when it arrives. A project whose agencies take less than two lines moves them up by a line and the button's row. |

## 6. Data visualization

From the World Bank Data Visualization Style Guide (draft, March 19, 2025) and its MIT-licensed `wbplot` package. Charts sit on `surface`.

| Group | Tokens |
|---|---|
| Chart text | text `#111111`, textSubtle `#666666` |
| Greys | grey500 `#111111`, grey400 `#666666`, grey300 `#8a969f`, grey200 `#ced4de`, grey100 `#ebeef4` |
| Functional | selection1 `#0071bc`, selection2 `#8963c1`, reference `#8a969f`, total `#163c6c`, noData `#ced4de` |
| Categorical, in order | `#34a7f2` `#ff9800` `#664ab6` `#4ec2c0` `#f3578e` `#081079` `#0c7c68` `#aa0000` `#ddda21` |
| Categorical text variants | `#106ca1` `#b65f0c` `#664ab6` `#208383` `#bb3b64` `#081079` `#0c7c68` `#aa0000` `#767712` |
| Sequential, bad to good | `#fdf6db` `#a1cbcf` `#5d99c2` `#2868a0` `#023b6f` |
| Sequential, good to bad | `#e3f6fd` `#91c5f0` `#8b8ac0` `#88506e` `#691b15` |
| Sequential, blue | `#e3f6fd` `#75ccec` `#089bd4` `#0169a1` `#023b6f` |
| Diverging, default | `#920000` `#bd6126` `#e3a763` `#efefef` `#80bde7` `#3587c3` `#025288` |
| Diverging, neutral | `#24768e` `#4ea2ac` `#98cbcc` `#efefef` `#d1aee3` `#a873c4` `#754493` |

| Element | Spec |
|---|---|
| Type by chart width | below 400px 12/14/16; 400 to 700px 13/15/18; above 700px 14/16/20 (s/m/l) |
| Title, subtitle | Title is the finding, l bold text; subtitle m regular textSubtle with units ("US$, millions") |
| Notes | "Source:" or "Note:" s bold, then s regular textSubtle |
| Axes | About five rounded ticks; grid 1px grey200 dashed; zero line 1px grey300; time axes have no title |
| Legends | Only when direct labels fail |
| Tooltip | 0.5px grey200 border; header s semibold; number m bold |
| Annotations | Label s semibold uppercase textSubtle; line 3px reference |
| Numbers | Comma thousands; K from 10,000, then M, B; 2 decimals below 1, 1 up to 100, 0 above; years have no comma. Strata: a STEP amount in a table is never shortened to K, M or B; it keeps STEP's form, cents included (1,230,000.00), so it matches the record to the cent |

Use category colors in order, only when color separates categories, and pair color with labels or shapes. Strata: cat1, cat2, cat4 and cat9 fall below 3:1 on white, so essential marks use the text variants.

**The AI/BI dashboard** (Strata, ticket 16; waiting for the user to confirm). Its pages are built from code in `src/strata/dashboard`. Three things differ from the charts above, because AI/BI fixes them: each chart's title names what it measures and never states the finding, since a title is fixed when the dashboard is deployed and a finding written into it would go stale after the next nightly run (the day's finding is the headline in its own tile, built by the same function as the app's); the dashboard uses AI/BI's own font, since it cannot load Open Sans; and its axes write numbers in full with commas, since AI/BI's short form starts at 1,000, not 10,000. Colors follow this section: the categories in order with the text variants for cat1, cat2, cat4 and cat9, and `#106ca1` alone for a single series.

**Strata's range chart.** Two lanes on one month axis, because position on a common scale is read most accurately (Cleveland and McGill). The middle half is a `grey200` band with `line-strong` edges, and the median is a 2.5px `grey500` tick (a `grey300` line on the band is only 2.03:1). Above about 60 comparables, the past range switches to 20 quantile dots. One tab stop per chart, arrow keys between marks, a "Show the table" twin, and alt text that states the statistics. No hypothetical outcome plots, and no animation by default.

Lane 1 (ticket 12) is 240 px tall in every state, in rows: the lane label "What happened" with its key (24 px), the plan's readout (32 px, 48 below 400 px wide), the lane (112 px, 96 below 400 px, taller in 16 px steps up to 160 before the first paint when the dots don't fit), the statistics' labels (40 px) and the axis (32 px). Each comparable is a dot in cat1's text variant `chart-cat1-text` (`#106ca1`, 5.70:1 on `surface`, 3.83:1 on the band), r 4.5 px (4 below 400 px), with a 2px `surface` ring, and a hovered dot gets a 2px `grey500` ring drawn over the dots around it; a package still open is the same dot hollow, a `surface` fill and a 1.5px `#106ca1` stroke. Quantile dots are r 6 (5 below 400 px). Dots sit exactly at their months and move up or down from the lane's centre, in a fixed order, when they would overlap (an exact-position beeswarm, never bins). The 8-in-10 point is a solid 1.5px `grey400` line, because the gridlines are dashed. The plan is a 2px `grey500` line from the readout row to the axis with a 1px `surface` halo each side, and its knob a 12 x 24 px `primary` pill with two white grip lines; the knob is a `role="slider"` with a 24 x 44 px hit area (44 x 44 for a coarse pointer). The axis covers what is placed on it: the dots (or the quantile dots the curve reached), the 8-in-10 point, the plan's months and the months typed. Ticks fall every 6 months, every 3 up to 12, every 12 above 36, stepping up to 24 and 48 so there are at most six labels, or five under 400 px wide; the last label reads "N months", and the label before it is dropped when it comes within 8 px of the last. A quantile dot the curve never reached is drawn hollow at the plot's right edge with a small `chart-cat1-text` chevron after it, and keeps its months in its name and tooltip ("Past 87.4 months"), so one stale package never stretches the axis. The readout sits right of the plan line in the left 55 percent of the plot and left of it otherwise, on the other side when it does not fit, and never across the line; under 400 px wide it is two lines ("2 of 49 signed" over "within 1.5 months"). When the key is wider than the chart, its hollow half takes a second line and row A grows by it before the first paint. When the lane label and the key don't both fit on row A, the key keeps the row, because it is the legend. With quantile dots the key is words alone, "Each dot is 1 in 20 of the 103 packages. Eight still open.", because open packages are not drawn one by one there; the one hollow dot is the unreached one, which its chevron, tooltip and name explain. Row A's label and key start at the chart's left edge, on the card's text edge. The middle tick starts 4 px into the lane, so the readout's descenders stay clear of it. The middle's label is centred on its tick, and the 8-in-10 label sits right of its line, or left when there is no room. When the plan line would cross either one, it moves off the line, the middle's label to start 6 px right of it or end 6 px left of it and the 8-in-10 label to the other side of its own line, if that clears the plan line by 6 px. Each label sits on a `surface` knockout, its box plus 2 px, drawn after the plan line, so where a label can move nowhere the line stops cleanly above it and resumes below it; each also keeps a 3px `surface` halo. The chart text and greys are the `chart-*` tokens in section 2's theme block. Below 20 comparables there is no band, middle, 8-in-10 line or "in 10", and the dots, the plan line and its count stay.

**Maps.** None by default. If one is needed, use World Bank Official Boundaries (CC BY 4.0) and print: "The boundaries, colors, denominations, and any other information shown on this map do not imply, on the part of Strata or the World Bank Group, any judgment on the legal status of any territory, or any endorsement or acceptance of such boundaries."

## 7. Writing

All copy lives in one file, `web/src/copy.ts`, so it can be reviewed and translated in one place. The gate's copy lint (`web/lint/`) checks it for rules 3, 8 and 19 and for GLOSSARY.md's Avoid terms, and fails when a component renders text that is not from it. The design gallery, which is for development only, keeps its sample text in `web/src/gallery/copy.ts`, and the same lint checks it.

1. Full sentences a 10th grader follows: short words, no jargon, nothing that sounds like a model wrote it ("use", not "utilize").
2. Buttons are short verb phrases: "Open the report", "Start a package".
3. No em dashes. En dashes only in ranges (2019–23). No exclamation marks.
4. Evidence is past tense ("Packages like this took 7 to 11 months"), never a promise ("will take"). Strata's own state is present tense.
5. Strata says "I"; the reader is "you".
6. Small groups get counts, not percentages: "6 of 37 packages", "8 in 10 were signed within 14 months". No percentage from fewer than 20 cases.
7. Events are described without blame: "the contracts were advertised again", never "the agency failed".
8. "World Bank" for IBRD and IDA; "World Bank Group" only for all five institutions; never "the Bank", except inside fixed terms such as "the Bank's no-objection". Spell out regions; never AFR, EAP, ECA, LAC, MNA or SAR.
9. Country names exactly as the World Bank lists them ("Türkiye"; "Egypt, Arab Rep." in tables).
10. Spell out abbreviations once per screen: "Request for Bids (RFB)". Name procurement methods as the current Procurement Regulations do.
11. "US$12.5 million" in text, "US$, millions" in tables; "8 percent" in sentences, "%" in tables and charts.
12. One to nine in words; numerals for 10 and up and with units.
13. "March 4, 2024" in sentences, "Mar 4, 2024" in tables; "fiscal 2024" in text, "FY24" in charts.
14. "Data" is plural.
15. Name the reference class ("of 37 comparable packages") and use one denominator per comparison. Under 50 cases, show "31 of 37" beside "about 8 in 10". No percentage or range from fewer than 20 cases, subgroups included.
16. When Strata holds back, it says so in the first person: "I'm not giving a range: only 12 comparable packages. Here are all 12."
17. Use STEP's field names and values word for word (Review Type, Method, Market Approach, "Open - National", "Single Stage - One Envelope", Process Status) and the Regulations' names for selection methods.
18. Use World Bank usage: package (always with its STEP reference), past range, time estimate, delay, rebidding, disagreement, data readiness, drafts, contract modifications, ISR, ICR Review.
19. Never write: approve, clear, clearance, no-objection (as Strata's own act), concur, endorse, validate; at risk, problem project; flag, red flag; misprocurement; slippage; splitting. Write "Procurement Plan" in full, never "PP", which in the 2026 Procedure means Project Paper.

## 8. Attribution and disclaimers

| Where | Text |
|---|---|
| Footer, every screen and slide | "Strata is an independent demo built on World Bank open data. It is not a World Bank product, and the World Bank has not reviewed or endorsed it." |
| Sources page, per dataset (WB format) | "The World Bank: [Dataset name]: [Data source]. License: CC BY 4.0." For example: "The World Bank: Contract Awards in Investment Project Financing (Since FY 2020): Systematic Tracking of Exchanges in Procurement (STEP). License: CC BY 4.0." Then: "Terms of use: https://www.worldbank.org/ext/en/legal/terms-conditions/datasets". The final list names every dataset Strata ingests. |
| Sources page, changes | "Strata joined these records, read the documents, and summarized them. These changes are Strata's own." |
| Quoting an Open Knowledge Repository work | "[Authors]. [Year]. [Title]. © World Bank. [handle URL] License: [license]." then, word for word: "This is an adaptation of an original work by The World Bank. Responsibility for the views and opinions expressed in the adaptation rests solely with the author or authors of the adaptation and are not endorsed by any member institution of the World Bank Group." |
| Other World Bank material | "The World Bank Group authorizes the use of this material subject to the terms and conditions on its website, Legal." |
| Data caveat | "The World Bank does not guarantee the accuracy of the data." |

## 9. Logo and name

- **Decision (Strata, October 22, 2026):** the World Bank logo appears in the private demo: the app's top navigation bar, the deck's title slide, and one corner of each deck figure. The World Bank's terms say its logos need express written permission (legalhelpdesk@worldbank.org) and must not imply an association. We use it anyway because Strata is a private demo built for a World Bank assessment panel and shown only to them inside a private workspace. It never goes on a public page, and the footer disclaimer in section 8 stays on every screen and slide.
- Use the official file from worldbank.org unaltered: no redrawing, recoloring, stretching, shadows or effects. worldbank.org's white mark, in its footer, is the World Bank Group logo; Strata uses that file because the header file's wordmark is dark navy, and its text alternative is "World Bank Group logo". Keep clear space of at least half the logo's height on every side, and never set it smaller than 24px tall. (Strata: the World Bank publishes no third-party logo rules, so these are conservative defaults.)
- The product name stays "Strata". The World Bank's name appears as attribution and as context ("built for the World Bank Group's procurement intelligence assessment"), never with "official", "partner" or "powered by".
- Wordmark: "Strata" in Open Sans 700, white on the navy bar and `ink-heading` on light surfaces.

## 10. Accessibility (WCAG 2.2 AA)

- Only the checked pairs above: text 4.5:1; large text and essential marks 3:1.
- Focus: 2px `focus` outline, 2px offset, never removed or covered; `focus-on-dark` on the navy bar. Color transitions leave the outline out, so focus shows at once. When a resize hides the focused control, such as the view switch below 1024 px, focus moves to the control that now holds the same thing.
- Targets 24 x 24 px or larger. A number you can check inside a sentence ("186 days") is an inline target, which WCAG 2.5.8 exempts from the width; its line stays 24 px tall.
- Never color alone: badges pair icon and text; charts add labels and shapes; text links are underlined.
- Charts: the finding as the title, `role="img"` with a name, a "Show the table" toggle, and tooltips on focus that Escape closes.
- Live regions announce steps, not tokens. Drags have a click alternative. Layouts reflow at 320px.
- Passages carry their `lang` attribute (French, Spanish, Portuguese). Focus moves into the drawer and back to the marker on close. Scroll padding keeps focused elements clear of sticky bars. Chips and segmented controls are at least 32 px tall; close buttons are 44 px. A skip link leads every page.
- Motion 120 to 200ms; none under `prefers-reduced-motion`.

## 11. Diagram-design profile (`strata-wb`)

For figures made with the `diagram-design` skill. Saved as `~/.diagram-design/profiles/strata-wb.md` and selected by the `strata/.diagram-design` marker. Deck figures carry the logo in one corner, per section 9.

| Role | Light | Dark | WB source |
|---|---|---|---|
| `paper` | `#f5f7f9` | `#181f25` | neutral-solid-05 / neutral-solid-90 |
| `paper-2` | `#e7edf3` | `#252e37` | neutral-solid-10 / neutral-solid-80 |
| `ink` | `#181f25` | `#f5f7f9` | body text |
| `ink-strong` | `#111111` | `#111111` | chart text |
| `muted` | `#4b5e71` | `#bdccdb` | neutral-solid-60 / neutral-solid-30 |
| `soft` | `#586e84` | `#8a9db1` | neutral-solid-50 / neutral-solid-40 |
| `rule` | `rgba(0,57,107,0.16)` | `rgba(255,255,255,0.16)` | divider-on-light-default |
| `rule-solid` | `#bdccdb` | `rgba(255,255,255,0.24)` | neutral-solid-30 |
| `accent` | `#0071bc` | `#169af3` | blue-50 (chart selection1) / blue-40 |
| `accent-tint` | `rgba(0,113,188,0.08)` | `rgba(22,154,243,0.12)` | derived |
| `link` | `#01707e` | `#02aac0` | accent-teal-70 / accent-teal-40 |

| Role | Family | Size | Weight |
|---|---|---|---|
| `title` | Open Sans | 1.75rem | 700 |
| `node-name` | Open Sans | 12px | 600 |
| `sublabel` | Roboto Mono | 9px | 400 |
| `eyebrow` | Roboto Mono | 7 to 8px | 500, tracked 0.18em, uppercase |
| `arrow-label` | Roboto Mono | 8px | 400, tracked 0.06em |
| `callout` | Open Sans italic | 14px | 400 |

On `paper`: accent 4.78, muted 6.23, soft 4.92, link 5.40. Keep accent text off `paper-2` (4.36). Deliberate breaks from the skill's defaults: cool grey paper, and no serif, because the World Bank sets everything in sans.
