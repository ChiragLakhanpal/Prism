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
| line-strong | surface / page | 5.28 / 4.92 | Control borders (needs 3:1) |
| bright | surface | 3.02 | Non-text only |

```css
@theme {
  --color-page: #f5f7f9;  --color-surface: #ffffff;  --color-surface-2: #e7edf3;
  --color-tint: #e9f7fd;  --color-tint-hover: #f6fcff;
  --color-line: #dae3eb;  --color-line-strong: #586e84;
  --color-ink: #181f25;  --color-ink-heading: #012740;  --color-ink-muted: #4b5e71;
  --color-primary: #004370;  --color-primary-hover: #00538a;  --color-primary-pressed: #012740;
  --color-link-hover: #066db1;  --color-focus: #b6490c;  --color-bright: #169af3;
  --color-info-bg: #f6fcff;  --color-info: #00538a;  --color-info-icon: #0071bc;
  --color-success-bg: #f6fef0;  --color-success: #388004;
  --color-warning-bg: #fef3d7;  --color-warning: #473201;  --color-warning-icon: #896001;
  --color-error-bg: #fdf2f2;  --color-error: #9d161d;  --color-error-icon: #c91c25;
  --color-neutral-bg: #e7edf3;  --color-neutral: #3d4c5c;
  --font-sans: "Open Sans", "Open Sans Fallback", "Helvetica Neue", Arial, sans-serif;
  --font-mono: "Roboto Mono", Menlo, Consolas, "Liberation Mono", monospace;
  --radius-xs: 2px;  --radius-sm: 4px;  --radius-md: 8px;  --radius-lg: 16px;  --radius-pill: 32px;
}
```

Brand navy `#002244` is used only for the top navigation bar that carries the logo, as The Loop specifies; text on it is white (about 16:1). Brand blue `#009fda` is used sparingly and never for text.

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
| Breakpoints | 768, 1024 (1200, 1400 for wide tables) | worldbank.org media queries |
| Radius | Pill: buttons, search, badges. 8: cards, inputs. 4: images | border-radius tokens |
| Elevation | Cards: none, use `line`. Popovers and dialogs: 1px `line` and `0 5px 25px rgba(160,158,143,.25)` | worldbank.org section shadow |
| Scrim | `rgba(0,13,26,.57)` | Strata |
| Targets | 24 x 24 px minimum; buttons 44 px tall | WCAG 2.5.8 |

## 5. Components

- **Top navigation** (WB). Navy `#002244` bar, 56px tall: the logo, then the Strata wordmark (which links Home), then five tabs (Packages, Projects, Lessons, Drafts, Data), with the view switch ("View: World Bank staff ▾") on the right. Under it, a white band holds the one box (search a project, check a plan, describe a package, or ask; "/" focuses it, and it lists what Enter will do) and the data-freshness stamp. Nouns navigate; verbs act.
- **Buttons** (WB). Pill, 2px border, 14px bold. Primary: `primary` fill, white text. Secondary: `primary` outline, `tint` hover. Ghost: `primary` text, `tint-hover` hover. Buttons act; links navigate.
- **Tabs.** 16px bold; the selected tab gets a 3px `primary` underline (Strata: WB's `#169af3` underline is 2.81:1). Five tabs at most.
- **Cards** (The Loop). `surface`, 1px `line`, radius 8. Titles 80 characters or fewer, blurbs 140, eight cards per group at most.
- **Tables.** Title sentence, count line ("Showing 1–20 of 99 sources"), `surface-2` header, units in column heads, numbers right-aligned, source line below.
- **Alerts.** State background, 4px left border, icon, one sentence.
- **Icons.** The World Bank's icon font is not public; use `lucide-react` (ISC). Icon-only buttons need an `aria-label`.

| Strata component | Spec |
|---|---|
| Evidence card | Card with a `label` eyebrow naming the stratum (names as in GLOSSARY.md), a `title`, a quoted excerpt of two or three sentences with the matching words highlighted, and a source line ("Source:" bold, document type, project ID in mono, date, paragraph and page). Citation number top right. Claims are past tense. |
| Citation marker | Inline `[1]`: 12px bold `primary`, 1px border, pill, 20px tall. Accessible name such as "Source 1: Implementation Completion and Results Report, June 30, 2021, paragraph 54". Hover or focus opens the evidence card; click opens the source at its page; Escape closes. |
| Disagreement card | Both claims side by side (stacked below 768px), in the order they were written, with equal weight, each with its source line and date. One carries the tag "Strata leans on this", one sentence names the rule, and a line says what changes if you keep the other. Warning state and the badge "Two reports disagree" only when it changes a number or claim in the answer or draft; otherwise an info note, "Sources differ". Shown only beside the claim it concerns. Never red: a disagreement is not an error. |
| Check line | Neutral, never green: "Checked: 23 of 23 numbers match records; 14 of 14 quotes are on their pages. Not checked: whether these are the right comparables." Sits under "In short", with the removed box open below it. |
| Evidence drawer | Opens beside the page, never over it: `clamp(400px, 40vw, 600px)`, about 65 characters a line; a full-screen sheet below 768px. Opens at what was clicked, with a switcher for the claim's other sources, the whole numbered paragraph with the matching words highlighted, "Open at page N" as a link, and "Wrong passage" and "Not useful" grouped at the bottom. 44 px close; focus returns to the marker. |
| Coverage line | A sentence with its denominator: "Based on 37 of 52 matching packages; 15 lacked the STEP reference that links notice to contract." No meter unless it shows that ratio. Links to Data readiness, filtered to the sources behind it. |
| Removed box | Open by default under "In short": the first removed sentence with its reason ("No record supports this number."), then the rest. Neutral state, never hidden behind a link. |
| Readiness tables | First, what you can ask, what it is ready for and what holds it back. Then one row per source: the number first in each cell, then a badge only for Partial or Gap, with definitions in the column headers. Freshness reads "Oct 22 · daily". No composite score. |
| Range chart | Two lanes on one month axis (see section 6). Lane 1, the past range: each dot one real comparable package, hollow for packages still open. Lane 2, the time estimate: a navy bar for the middle half, a thin line to the 8-in-10 point, a white notch at the middle. The plan is a full-height line through both lanes with a count readout ("4 of 40 signed within 6 months"), draggable with keyboard and number input. The title is the finding; a sentence says why the lanes differ. |
| Draft bar | Sticky bottom bar on drafts, 1px top `line`, held to the document column. Left: what exporting does and is not ("A working draft for the borrower's PPSD. Exporting sends nothing and is not a World Bank review, clearance or no-objection.") and "You opened 3 of 14 sources". Right: Mark as checked (primary), Export to Word (secondary), with Discard set apart and undoable. States: Draft → Checked by you → Exported. Ends on a success state. |
| Following row | 2px top divider. Status first, then the project name as a link; country and project ID (mono) and closing date; the signals that put it there, one line each, past tense, with counts; one next action ("Add to mission brief"). The status definition sits on the column header. |
| Status badge | Pill, padding 4/12, 16px icon, 14px text. One icon shape per state; the text always names the state: Needs a look, Watch, No signals. |

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
| Numbers | Comma thousands; K from 10,000, then M, B; 2 decimals below 1, 1 up to 100, 0 above; years have no comma |

Use category colors in order, only when color separates categories, and pair color with labels or shapes. Strata: cat1, cat2, cat4 and cat9 fall below 3:1 on white, so essential marks use the text variants.

**Strata's range chart.** Two lanes on one month axis, because position on a common scale is read most accurately (Cleveland and McGill). The middle half is a `grey200` band with `line-strong` edges, and the median is a 2.5px `grey500` tick (a `grey300` line on the band is only 2.03:1). Above about 60 comparables, the past range switches to 20 quantile dots. One tab stop per chart, arrow keys between marks, a "Show the table" twin, and alt text that states the statistics. No hypothetical outcome plots, and no animation by default.

**Maps.** None by default. If one is needed, use World Bank Official Boundaries (CC BY 4.0) and print: "The boundaries, colors, denominations, and any other information shown on this map do not imply, on the part of Strata or the World Bank Group, any judgment on the legal status of any territory, or any endorsement or acceptance of such boundaries."

## 7. Writing

All copy lives in one file, so it can be reviewed and translated in one place.

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
- Use the official file from worldbank.org unaltered: no redrawing, recoloring, stretching, shadows or effects. Keep clear space of at least half the logo's height on every side, and never set it smaller than 24px tall. (Strata: the World Bank publishes no third-party logo rules, so these are conservative defaults.)
- The product name stays "Strata". The World Bank's name appears as attribution and as context ("built for the World Bank Group's procurement intelligence assessment"), never with "official", "partner" or "powered by".
- Wordmark: "Strata" in Open Sans 700, white on the navy bar and `ink-heading` on light surfaces.

## 10. Accessibility (WCAG 2.2 AA)

- Only the checked pairs above: text 4.5:1; large text and essential marks 3:1.
- Focus: 2px `focus` outline, 2px offset, never removed or covered.
- Targets 24 x 24 px or larger.
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
