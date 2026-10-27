# DESIGN.md: the sections the shell redesign changes, grouped by the ticket that lands them

Proposed text for DESIGN.md, round 3, finished after the second critic's review, written to paste in as it stands. It is grouped by ticket, in `tickets.md`'s order (block 1 by the tokens ticket, whose class sweep pastes nothing; block 12 in two parts by the two Data tickets; block 13 in two parts by the two citation chain tickets), because DESIGN.md describes the app as it is: each ticket pastes only its own block, in the same change, so polish tickets 56 to 63 never read a rule for a screen that does not exist yet. "(Strata, the shell redesign)" takes the ticket's number once the orchestrator files it.

Round 3 writes the new and much-changed components in the design-system skill's form (a description, then variants, states and accessibility notes, then what to do and not do), as a subsection of DESIGN.md section 5 under the heading "Shell and citation components". A component that already has a row in section 5's table keeps a one-line row that points to its subsection, so the table still lists every component once. Small changes to an existing row stay sentence edits.

Everything not named here stays as DESIGN.md has it, including section 7's rules, section 8's footer sentence and section 9's logo decision.

---

## 1. Tokens, type, space, shape and motion (the tokens ticket; one sentence by the class sweep)

The tokens ticket pastes this block, except the one sentence marked "pasted by the class sweep", which becomes true only when the sweep has moved every page's classes to their roles.

### Section 2, Color: add these rows to the contrast table

```markdown
| ink-heading | tint | 14.05 | The current mark's label: a sidebar item, a view row, an open or marked table row |
| ink | surface-2 | 14.11 | A sidebar item on hover |
| surface | navy | 16.00 | The box's edge on the bar (needs 3:1) |
| focus | tint / page | 4.86 / 4.95 | Focus ring on the current mark and on the sidebar (needs 3:1) |
| info-icon | surface | 5.14 | The opened chart mark's 2px ring, the chart guide's selection1 (needs 3:1) |
```

### Section 2, Color: add after the theme block's note

```markdown
The deck at /present uses the same five values (Strata, the shell redesign): `navy`, `primary`, `ink-heading`, `page`, and `info-icon` (#0071bc), which the deck calls its accent. The app keeps navy to the bar that carries the logo; the deck may set whole opener slides in navy. Neither adds a color the other lacks.
```

### Section 3, Typography: replace the families table's first row, the self-host sentence and the scale table, and add a note

```markdown
| All text, UI and charts | Open Sans 300, 400, 600, 700, italic 400 | SIL OFL 1.1 | `--font-sans` |
```

```markdown
Self-host with `@fontsource/open-sans` (300, 400, 400 italic, 600 and 700) and `@fontsource/roboto-mono` (400, 500). Define `Open Sans Fallback` as `local(Arial)` with `size-adjust: 105.22%; ascent-override: 101.58%; descent-override: 27.84%` (FinancesOne's values) to prevent layout shift. Strata (the shell redesign): weight 300 is for the `finding` style only, as the World Bank's 2016 guide sets its large sentences in Andes ExtraLight.
```

```markdown
| Token | Size / line height | Weight | Color | Use |
|---|---|---|---|---|
| `display` | 32 / 40 | 700 | ink-heading | Deck titles only |
| `finding` | 28 / 36; 24 / 32 below a page area of 48rem | 300, -0.01em, balanced lines | ink-heading | The page's one finding (principle 6). At most 22.5em wide, about 45 characters a line |
| `h1` | 24 / 32; 20 / 28 below 48rem | 700 | ink-heading | Page title, or the object's name |
| `h2` | 18 / 24 | 600 | ink-heading | A zone's name, a side panel's name, a table named by a noun |
| `h3` | 16 / 24 | 600 | ink-heading | A block inside a zone, a group of facts in the drawer |
| `lead` | 18 / 28 | 400 | ink | A block's own finding, a table's title sentence, an answer's sentences |
| `body` | 16 / 24 | 400 | ink | Sentences, zone summaries |
| `small` | 14 / 20 | 400 | ink | Tables, badges, sidebar items, fact values, tooltip text |
| `caption` | 13 / 20 | 400 | ink-muted | Source lines, notes, count lines, the stamp, a tooltip's source line |
| `label` | 13 / 16 | 600 | ink-muted | Field and fact labels, stage labels. Sentence case |
| `chart-label` | 12 / 16 | 600, uppercase, +0.02em | chart-text-subtle | Lane and legend labels inside a chart, as the World Bank chart guide sets them |
| `button` | 14 / 20 | 600 | | Buttons |
```

```markdown
Strata (the shell redesign): size says how much a line matters and weight says what kind of line it is. The finding is the only light text; the h1 and the wordmark are the only 700; names, labels and buttons are 600. A zone's name never outranks its finding. Tracking follows size: -0.01em on the finding, zero on text, +0.02em on the small uppercase chart label. `title` (18 / 700) is retired into `h2`, and `label` loses its uppercase and its tracking. An ID inside the finding, such as a P-code in an officer's briefing, takes Roboto Mono 400, so it does not outweigh the light sentence around it. Two old tokens stay until the deck branch moves its last uses: `--text-title` (with `h2`'s values) and `--radius-box`; the class lint lets only files under `web/src/deck/` use them, and the uppercase rule exempts the same folder until then, and also the files that use `uppercase` today, by one frozen list the class sweep empties.
```

Pasted by the class sweep, as the last sentence of the note above:

```markdown
Uppercase appears only with `chart-label`, inside charts.
```

Theme block, the type, radius and motion lines:

```css
  --text-display: 2rem;      --text-display--line-height: 2.5rem;   --text-display--font-weight: 700;
  --text-finding: 1.75rem;   --text-finding--line-height: 2.25rem;  --text-finding--font-weight: 300;
  --text-finding--letter-spacing: -0.01em;
  --text-h1: 1.5rem;         --text-h1--line-height: 2rem;          --text-h1--font-weight: 700;
  --text-h2: 1.125rem;       --text-h2--line-height: 1.5rem;        --text-h2--font-weight: 600;
  --text-h3: 1rem;           --text-h3--line-height: 1.5rem;        --text-h3--font-weight: 600;
  --text-lead: 1.125rem;     --text-lead--line-height: 1.75rem;     --text-lead--font-weight: 400;
  --text-body: 1rem;         --text-body--line-height: 1.5rem;      --text-body--font-weight: 400;
  --text-small: 0.875rem;    --text-small--line-height: 1.25rem;    --text-small--font-weight: 400;
  --text-caption: 0.8125rem; --text-caption--line-height: 1.25rem;  --text-caption--font-weight: 400;
  --text-label: 0.8125rem;   --text-label--line-height: 1rem;       --text-label--font-weight: 600;
  --text-chart-label: 0.75rem; --text-chart-label--line-height: 1rem; --text-chart-label--font-weight: 600;
  --text-chart-label--letter-spacing: 0.02em;
  --text-button: 0.875rem;   --text-button--line-height: 1.25rem;   --text-button--font-weight: 600;
  --text-title: 1.125rem;    --text-title--line-height: 1.5rem;     --text-title--font-weight: 600; /* deprecated: the deck's last uses */
  --font-weight-light: 300;  --font-weight-normal: 400;  --font-weight-medium: 500;  --font-weight-semibold: 600;  --font-weight-bold: 700;
  --radius-xs: 2px;  --radius-sm: 4px;  --radius-md: 8px;  --radius-lg: 16px;  --radius-pill: 32px;
  --radius-box: 22px; /* deprecated: the deck's last use */
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
  --motion-press: 120ms;  --motion-color: 120ms;  --motion-popover: 160ms;  --motion-pane: 160ms;
  --motion-sheet: 200ms;  --motion-exit: 120ms;
  --tooltip-width: 20rem;
```

### Section 4, Space, grid, shape: replace these three rows

```markdown
| Space | 2, 4, 8, 12, 16, 24, 32, 40, 48, 64 px, named `space-0.5` to `space-16` by Tailwind's step. Roles (Strata, the shell redesign): 4 between a label and its value; 8 from a heading to its first line, a stage label to its zone, the breadcrumb to the h1, a tooltip's parts; 12 inside controls and from a zone's number to its name; 16 between blocks in a zone, between panels, a zone row's top and bottom padding; 24 a panel's padding and after a finding; 32 from the page head to the first zone and before a stage label; 40 the page margin from 1200 px | spacing tokens |
| Radius | By role (Strata, the shell redesign: worldbank.org's button token is a pill; Strata keeps the pill for data so a control and a fact never share a shape). 4 (`radius-sm`): controls, meaning buttons, the box, inputs, selects, the view switch, sidebar items, key hints and tooltips. 8 (`radius-md`): containers, meaning panels, the side panel, cards, popovers, windows and the drawer's record cards. The pill (`radius-pill`): data, meaning status badges, citation markers, chips and the check pill. 16 (`radius-lg`): a bottom sheet's top corners. 2 (`radius-xs`): skeleton bars | border-radius tokens |
| Elevation | Panels and cards: none, a 1px `line` edge on `page`. A zone row: no edge, only the 1px `line` under it. Tooltips, popovers, windows and the Menu sheet: 1px `line` and `0 5px 25px rgba(160,158,143,.25)`. The drawer beside the page: a 1px `line` edge and no shadow | worldbank.org section shadow |
```

### Section 4: add a Motion subsection after the table, and replace section 10's "Motion 120 to 200ms" bullet with "Motion: section 4, Motion."

```markdown
### Motion

Strata (the shell redesign), after Emil Kowalski's decision framework: should it move, what is the movement for, which curve, how long. Strata is read many times a day, so most things do not move. Every duration is 120 to 200 ms.

| What | Movement | Curve | Time | Why |
|---|---|---|---|---|
| A tooltip | Opacity and scale 0.97 to 1, from the side that touches its trigger; a tooltip opened less than 300 ms after another closed appears at once | `ease-out` | 160 ms | Ties it to its number; moving along numbers stays fast |
| A popover or window | Opacity and scale 0.97 to 1, from its trigger | `ease-out` | 160 ms | Ties the window to what opened it |
| The evidence drawer | Opacity, and 12 px in from the right | `ease-out` | 160 ms | It arrives from the edge it lives on |
| The Menu sheet, a bottom sheet | Slides in from its edge, out the same way | `ease-drawer` in, `ease-out` out | 200 ms in, 120 ms out | It leaves the way it came |
| A primary or secondary button pressed | Scale 0.98 while pressed; back at once on release, because the transition is set only on `:active` | `ease-out` | 120 ms in, 0 out | The press is felt on press; the release snaps, since the system's answer is instant |
| Hover fills and link colors, pointer only | Color | `ease` | 120 ms | A calm hover |
| The range chart's comparison | Lane 2 and the dots, as today | `ease-out` | 160 and 120 ms | The comparison changed |
| The export success panel | Fade | `ease-out` | 200 ms | The screen's one entrance |

Never moves: page loads and route changes; the sidebar's width; a zone row opening; rows, cards and lists entering; numbers (never counted up); charts on load or rerun; a drawer's content when its source changes; skeletons (static, no shimmer); focus rings; anything that closes (tooltips, popovers, windows and the drawer close at once). Only `transform` and `opacity` move, apart from the chart's SVG attributes. Anything a person can trigger again before it ends uses a CSS transition, never a keyframe animation, and entrances use `@starting-style`, so a browser without it shows the element at once. Input is never locked while something moves. Hover styles live inside `@media (hover: hover) and (pointer: fine)`. A tooltip never opens because the page scrolled its number under a resting pointer; it waits for the pointer to move. Under `prefers-reduced-motion: reduce` nothing moves and nothing fades. This is a deliberate departure from the common advice to keep a gentle fade (Emil Kowalski's review-animations standard 8, "gentler, not zero"): no state in Strata needs a fade to be understood, and one rule is one test.
```

### Section 4: add a Phone baseline row

```markdown
| Phone baseline | Strata (the shell redesign), after mobile-native practice: `-webkit-tap-highlight-color: transparent` on the root; `touch-action: manipulation` on buttons and links; text inputs at 16px at least, so a phone never zooms into them; `100dvh` with a `100vh` fallback for the page column's height; `viewport-fit=cover` with `env(safe-area-inset-bottom)` padding on the Menu sheet and the draft bar; `overscroll-behavior: contain` on the sidebar and the drawer; button labels not selectable | Strata |
```

### Section 5, Components: replace the Buttons bullet's first sentence and the Cards bullet

```markdown
- **Buttons** (Strata, the shell redesign: worldbank.org's button token is a pill; Strata keeps the pill for data and gives controls 4px corners, so a control and a fact never share a shape). 4px corners, 1px border, 14px 600, at least 44px tall. Primary: `primary` fill, white text. Secondary: `primary` border and text on `surface`, `tint` hover. Ghost: `primary` text, `tint-hover` hover; on the `page` background a ghost button hovers to `tint` (`onPage`). A primary or secondary button scales to 0.98 while pressed (section 4, Motion).
```

(The rest of the Buttons bullet, from "A ghost button in a column of text sits flush", stays.)

```markdown
- **Cards and panels** (The Loop, with Strata's roles). `surface`, 1px `line`, 8px corners, no shadow. A card holds one item in a list; a panel holds open work: a block of evidence, a table or a form. Titles 80 characters or fewer, blurbs 140, eight cards per group at most. A panel never sits inside another panel.
```

### The two new components' tokens

The Number tooltip and the Evidence drawer use `--tooltip-width`, `--motion-popover`, `--motion-pane`, `--ease-out` and `--ease-drawer` above. Their full text lands with the number tooltip ticket (block 13a) and the check window ticket (block 13b).

---

## 2. The sidebar and the rail (the sidebar ticket)

### Section 2, Color: add after the navy paragraph

```markdown
Strata (the shell redesign): the sidebar sits on `page` with a 1px `line` right edge, so the only white surfaces are the work, the box and the drawer. An item hovers to `surface-2`. The current item is `tint` with a 3px `primary` bar on its left and its label in 600 `ink-heading`, the same current mark as the view rows, the box list's Enter option and a table row whose records are open.
```

### Section 5, "Shell and citation components": add Sidebar and Menu sheet; replace the Tabs bullet's first two sentences

```markdown
#### Sidebar

The navigation named "Main", beside the page from 1024px, sticky under the bar at the window's height. Home, then the applied view's sections among Packages, Projects, Lessons and Drafts, then at its foot Data, the data stamp and "Collapse the sidebar". Nouns navigate and verbs act, so the sidebar holds no verb but Collapse (Strata, the shell redesign).

| Variant | Use when | Look |
|---|---|---|
| Open | From 1440px by default, or when the person chose it | 224px; each item a 16px lucide icon (`house`, `package`, `folder-open`, `book-open`, `file-pen-line`, `database`) and its label in `small`, at least 36px tall, 4px corners |
| Rail | From 1024 to 1439px by default, or when the person chose it | 64px; icons only; the label in a tooltip to the right on hover and keyboard focus; sub-items and the stamp hide, and the Data tooltip carries the stamp's words |
| Menu sheet | Below 1024px | See Menu sheet |

| State | Look | Behavior |
|---|---|---|
| Default | Label in `ink`, icon in `ink-muted` | |
| Hover (pointer only) | `surface-2` fill | |
| Current section | `tint`, 3px `primary` bar inset left, label 600 `ink-heading`, icon `primary` | `aria-current="page"` on the section's own page, `"true"` on a page inside it, as `routes.ts`'s `matchRoute` names the section |
| A section's own page current | The sub-item carries the mark; the section keeps 600 and its `primary` icon | Sub-items show only under the current section: Following and All projects under Projects (World Bank staff); the reviewer pages under Lessons for the roles that have them, each with a count badge from the server hidden at zero; Data readiness and Sources and licenses under Data |
| Loading | Six static `surface-2` bars at the items' height | Until GET /api/me answers, so nothing moves when the view's items arrive |

Accessibility. Role: `nav` named "Main". Keyboard: Tab through items; "Collapse the sidebar" and "Expand the sidebar" are one button with `aria-expanded`. Screen reader: a rail tooltip is not the item's name; the name stays in the link. When a resize hides the focused control, focus moves to the control that now holds the same thing.

| Do | Don't |
|---|---|
| Keep each section once, one route each | Repeat a page's own list in the sidebar |
| Remember the person's open or rail choice in local storage, read by an inline script in `web/index.html` before the first paint | Change it by itself, or animate the width: the sidebar changes at once |
```

```markdown
#### Menu sheet

Below 1024px the sidebar's content opens from the left as a modal dialog named "Menu", `min(320px, 100vw - 48px)` wide, over the scrim, with the page and the bar inert. It slides in over 200ms on `ease-drawer` and back out over 120ms (section 4, Motion). The labelled Menu button (its word hidden from sight below 360px, so it keeps its name) opens it with `aria-expanded` and `aria-controls`; focus moves to the current page's item; Escape, the 44px "Close the menu" button and a press on the scrim close it and return focus to the Menu button. Below 768px the view switch sits at its foot (Strata, the shell redesign).
```

```markdown
- **Tabs.** Only for sibling views of one object, such as a project's Summary, Procurement, Timeline, Documents and Connections; a section's own pages are sidebar items (Strata, the shell redesign). 14px 600, 40px tall, a 3px `primary` underline on the selected tab and a 3px `line-strong` underline on hover, on light surfaces only.
```

(The rest of the Tabs bullet, from "Five tabs at most", stays.)

---

## 3. The top bar with the box (the bar ticket)

### Section 2, Color: replace the two paragraphs after the theme block's note

```markdown
Brand navy `#002244` (`navy`) is used only for the top bar, which carries the logo and the one box, as The Loop keeps it to "main navigation and WB logo"; text on it is white (about 16:1). Brand blue `#009fda` is used sparingly and never for text.

On the bar (Strata, the shell redesign), the view switch has a 1px white border, hovers to a `primary` fill and shows `focus-on-dark`; the box is `surface` with no border, since its edge is 16:1 on navy, and shows `focus-on-dark` around it while anything inside it has focus. A control inside the box shows `focus`.
```

If the deck's second draft (`deck/second-draft`) has merged and the user kept its navy slides, the first sentence keeps the deck's clause, as the deck session and the orchestrator agreed (`../deck-ticket.md`): "is used only for the top bar, which carries the logo and the one box, and the deck's navy slides, which carry the white logo (section 4, Deck frame)". Whichever of the two merges second writes it, and block 4's principle 2 follows.

### Section 5, Components: replace the Top navigation bullet

```markdown
- **Top bar** (WB navy; Strata, the shell redesign). The banner landmark. From 1024px one 56px row that sticks: the World Bank Group logo (section 9), 24px, the wordmark "Strata" (a link to Home), the one box, and the view switch ("View: World Bank staff ▾") 24px from the right edge. The box starts at the page's content edge when the sidebar is open and 32px after the wordmark when it is a rail, and is at most 640px wide; it keeps one row, and its scope chip drops "Within" when the box is narrower than 35rem. Below 1024px the bar does not stick and has two rows: the Menu button, the logo and the wordmark (and the view switch from 768px), then the box across the window. With a scope chip below 1024px the box's search icon hides, so the chip takes the first row and the text the second; below 360px the icon always hides. Below 768px the placeholder takes its short form ("Open a project or package, or ask", `box.placeholderShort`), so it is never cut, while the field's name keeps the whole sentence, and the "/" hint hides. The data stamp is not in the bar (see Freshness stamp). The view switch is a 32px control with 4px corners and a 1px white border; its popover, rows, past-date field, language choice and labels stay as ticket 40 set them, and a label may be at most 167px in the `button` style.
```

### Section 5, the component table: replace the first sentences of two rows

```markdown
| Scope chip | Inside the box, before the text, on a project or package page: 32px tall, pill, 1px `line-strong` border, "Within" in `small` `ink-muted` and the ID in mono (the ID only below 768px, and whenever the box is narrower than 35rem), and a 24px round remove button. From 1024px the box keeps one row. ...
| Freshness stamp | At the sidebar's foot, under Data, on the label's left edge; in the Data item's tooltip when the sidebar is a rail; at the Menu sheet's foot below 1024px (Strata, the shell redesign). `caption` in `ink-muted` with tabular numerals, a link to the Data page with a dotted underline, in a 24px line box. ...
```

(Each row keeps the rest of its text.)

### Section 10, Accessibility: add

```markdown
- The bar (Strata, the shell redesign). One banner landmark (the bar) holds the search landmark (the box) and the view switch. A skip link leads every page and shows below the bar, over the page, so it never covers the logo. When a resize below 768px hides the focused view switch, focus moves to the Menu button.
```

---

## 4. The page frame (the frame ticket)

### Section 1, Principles: replace principle 2

```markdown
2. **Quiet and blue.** A grey frame, white panels for the work, navy only in the bar that carries the logo, one blue for action. Other colors mark a state or a data category.
```

With the deck's navy slides kept (block 3 above), "navy only in the bar that carries the logo" reads "navy only where the logo is: the bar and the deck's navy slides".

### Section 4, Space, grid, shape: replace the Grid and Breakpoints rows, edit the Document column row, and add two rows

```markdown
| Grid | 12 columns; gutter 16 / 24 / 32 px (below 768 / from 768 / from 1024); margin 16 / 32 / 40 px (below 768 / from 768 / from 1200), set by the window, never by the page area, so the evidence drawer never moves the page's left edge; content at most 1280px wide, left aligned beside the sidebar. Strata (the shell redesign) | grid tokens |
| Breakpoints | 768, 1024 (1200, 1400 for wide tables), written in rem (48rem, 64rem, 75rem, 87.5rem). Strata: 360 (22.5rem) is used only by the Menu button's label and the box's icon, and 1440 (90rem) only by the sidebar's default. The bar follows the window. Under the bar, a page lays out by the page area's width (`@md/page:`, `@lg/page:`, `@xl/page:`), because the evidence drawer narrows it; a page that keeps its place beside the drawer lays out by the frame's width (`@container frame`, the window minus the sidebar) | worldbank.org media queries |
| Shell | Strata (the shell redesign). Bar 56px. Sidebar 224px open, 64px as a rail. `frame-top`, where sticky parts stick: 56px from 1024px, 0 below. `main` holds at least the window's height minus the bar | Strata |
| Page layouts | Strata (the shell redesign). **Wide**: lists, tables, dashboards and the plan check use all 12 columns, and when the drawer opens the page narrows and keeps its left edge. A page head that sets its title beside its actions does so by the page area (from 46rem), so a narrowed page stacks them | Strata |
```

In the **Document column** row, replace "In a window of 1200 px or more the column is measured against the window, not the page area the drawer narrows" with:

```markdown
From a frame of 1200 px the column is measured against the frame (the window minus the sidebar), not the page area the drawer narrows
```

### Section 5, the component table: replace the first sentences of the Answer panel row

```markdown
| Answer panel | The answer to a question asked from the box, as a panel at the top of the page column under the bar, above the page head, in the work's columns (1 to 7 on a workspace page, beside its side panel; 1 to 8 on a wide one from a page area of 1024px; all 12 below); "In short" in `label`, and its sentences in `lead`. ...
```

(The row keeps the rest of its text, from its second sentence.)

### Section 10, Accessibility: add

```markdown
- Sticky parts (Strata, the shell redesign): the bar from 1024px, the sidebar, the side panel, the drawer, a page head that holds the page's primary action, and the draft bar. The frame owns `frame-top` and one hook sets `scroll-padding-top` to the bar plus any sticky head, plus 8px, so a focused element is never under them.
- Short states never pull the footer into view: `main` holds at least the window's height minus the bar.
```

---

## 5. The workspace layout and the zone parts (the workspace ticket)

### Section 1, Principles: add 6, 7 and 8

```markdown
6. **The finding leads.** A page has at most one finding: the sentence that answers what the page is for, or, when Strata holds back (section 7, rule 16), the first-person sentence that says so. It is the largest type on the page, inside the first screen at 390 by 844 and 1024 by 768, and nothing else uses its style. A status sentence, such as a first visit or a first run, is not a finding: it takes `lead`.
7. **A panel only around open work.** The frame is grey and the work is white. A white panel holds evidence, a table or a form; a zone with only a sentence, one action or nothing yet is a row on the grey.
8. **Each person's next step first.** A page shows what the person who comes to it needs for the step they are on. The rest is one click away, on the thing it explains (a number, a row, a source line, a zone's name), never in a menu and never on another page.
```

### Section 4, Space, grid, shape: add to the Page layouts row, and remove the Document column row

```markdown
**Workspace**: pages read top to bottom while sources open (Home, the package workspace, a planned package, a draft, a lesson's review page) put the work in columns 1 to 7 and a side panel in columns 9 to 12, measured on the frame, so the drawer opens into columns 8 to 12 and the work keeps its place and width. An answer panel takes columns 1 to 7 above the page head, beside the side panel. It applies from a frame of 75rem. Below it the page is one column: an object's facts fold into one line in the page head with a button that opens them in the drawer (the package), a draft's state takes one line in the head (the draft), and other side panels follow the work (Home). A draft's notes are a table when the column is at least 560px wide, and cards below that.
```

### Section 5, "Shell and citation components": add Page head, Task zone, Foot strip, Stage label and Side panel; the component table's Page header and Collapsed section rows point to them

```markdown
#### Page head

Every page starts with it, in the work's columns (Strata, the shell redesign; replaces Page header).

| Part | Rule |
|---|---|
| Breadcrumb | Parents only, so an object's ID shows once in the head; each link in a 24px line box; below 768px the parent alone as a back link, which wraps and is never cut |
| `h1` | 24/32, 20/28 below 48rem; it takes focus when a route change moves to it |
| ID line | On an object's page, `small` mono `ink-muted`, 4px under the h1 |
| Purpose | One or two sentences in `body` `ink-muted`, at most 65 characters a line, 12px under what precedes it |
| Facts line | Below the workspace threshold on an object's page: one line of facts in `small` and a flush ghost button that opens them in the drawer ("Show the plan row") |
| Action | At most one primary action, at the head's right when the page area allows (46rem), under the purpose otherwise |
| Alert slot | Above the head, errors first, 24px above the breadcrumb when it holds any. When the page's one request failed, it holds the error alert (the copy file's sentence and a secondary "Try again"), the h1 names the page ("Home", "Procurement Plan", "Drafts") and nothing else draws |

States: loading keeps the real breadcrumb and holds the h1's lines with skeleton bars at the h1's height. The head sticks only when it holds the page's primary action (the plan check, from 1024px).
```

```markdown
#### Task zone

One step of a page's work (Strata, the shell redesign).

| Variant | Use when | Look |
|---|---|---|
| Panel | It holds open work: evidence, a table, a form | `surface`, 1px `line`, 8px corners; blocks 16 apart; each block of evidence ends in a Foot strip |
| Row | It is closed, holds only a sentence or one action, or has nothing yet | On `page`, no fill, no corners, a 1px `line` under it and over the first row of a run, 16px above and below its text; a transparent 1px edge so its number and name sit on the same x as a panel's |
| Numbered | The page's zones are a sequence (the package workspace, a planned package) | A 24px number column in `h2` size, 600, `ink-muted`, tabular, `aria-hidden` |
| Unnumbered | Everything else | The body starts 24px in |

| State | Look | Behavior |
|---|---|---|
| Open | Panel | |
| Closed | Row with its one-sentence summary and a Show button | The Show or Hide button is a flush ghost with `aria-expanded`, after the summary in the DOM, at the header's right from 768px; opening makes the row a panel in place, at once, with focus kept on the button |
| Loading | The real header over skeleton bars sized to what they stand for | |
| Error | An error alert with "Try again" in the body; the header stays | |
| No content | The first-person sentence and at most one link, as a row | |

Accessibility: each zone is a `section` named by its `h2`; a link to a zone's id opens it with focus on its heading. A zone is closed by default only when most readers skip it, and never when it holds the page's finding, a removed sentence, an Experimental badge or a refusal. A zone's tag (such as "PPSD section 3") sits at the header's right in `caption` `ink-muted`, or under its name at every width when an action holds the header's right (Start here's Remove). A failed block's error alert takes the block's place in the zone's body; the header and the zone's other blocks stay.

| Do | Don't |
|---|---|
| Put any action other than Show or Hide in the flow after its sentence, so "reveal" and "do" are told apart by place | Put two actions at the header's right |
| Open in place, at once | Animate the height or slide the content |
```

```markdown
#### Foot strip

The end of each block of evidence in a panel: the panel's full width, `page` background, a 1px `line` top edge, padding 16 and 24 (16 below 768px), on the body's left edge. It holds the block's Note, its coverage line and its source line, in `caption`, 8 apart, each at most 65 characters a line. A line that holds a checkable number, such as the coverage line's "49 of 65", is 24px tall, as section 10 keeps an inline number's line. Provenance always has this place (Strata, the shell redesign).
```

```markdown
#### Stage label

The stage of the zones that follow ("Planning", "Tender design"), in `label` on `page`, with a 1px `line` rule from 12px after its word to the column's right edge, 8px above the first zone of its stage and 32px after the zone before it. Once where the stage changes, never on every zone (Strata, the shell redesign; replaces the package sections' eyebrows).
```

```markdown
#### Side panel

An object's facts or state beside its work, in columns 9 to 12 of a workspace page from a frame of 75rem: a panel with 24px padding, an `h2` naming what it holds ("From the plan row", "State of this draft", "Waiting for you"), a definition list (labels in `label` over values in `small`, 16 apart; two columns when the panel's content is at least 18rem wide, long values across both), and its source line with a citation marker under a hairline where it has one. It sticks under the bar, 24px down. It hides while the drawer is open, because the drawer opens in its place. While its object loads, its labels stand over value bars and its source line keeps its space. A side panel that holds only a sentence, such as Waiting for you with no drafts, is a row in the side column, not a panel (Strata, the shell redesign).
```

```markdown
| Page header | See Page head (Strata, the shell redesign). |
| Collapsed section | Now the closed form of a Task zone (Strata, the shell redesign). Its rules for focus, the section link that opens it, its loading, error and no-content states, and its live region stay as ticket 31 set them; its look is the Task zone's row. |
```

---

## 6. Home (the Home ticket)

### Section 4: replace the Home's blocks row

```markdown
| Home's blocks | Strata (ticket 41; the shell redesign): Home uses the workspace layout. "Worth knowing" takes columns 1 to 7 and "Waiting for you" is the side panel in 9 to 12, from a frame of 75rem; below it they stack, "Worth knowing" first, so the reading and focus order never change. | Strata |
```

### Section 5: replace the first sentence of the Briefing heading row, the Start here strip row, and the Worth knowing title

```markdown
| Briefing heading | Home's `h1` (Strata, ticket 41; the shell redesign): a sentence-case date line in `label` ("Your briefing for Wednesday, October 28"), then one to five sentences the server builds from copy templates, in the `finding` style; the first-run and quiet sentences, which report a state, take `lead`. The public view's h1 is "Home", with its one sentence in `lead`. When an answer opens on Home, the sentences fold to the date line and the first sentence in `body`, with a flush ghost "Show the briefing" (`aria-expanded`) under them; closing the answer unfolds them. ...
| Start here strip | Strata (ticket 41; restyled by the shell redesign). A Task zone row under the briefing: "Start here" as its name, "Examples Strata set up for you" as its tag under the name at every width, Remove at the row's right in the place of the zone's Hide button, then the six example links in the ticket's order, each at least 32px tall. Its rules for who sees it, Remove, the undo row and "Show the examples again" stay as ticket 41 set them. |
```

```markdown
Worth knowing's name is "Worth knowing", and "Fixed checks, no model" is its tag at the panel's right, in `caption` `ink-muted`, replacing the middle dot that joined them; the public view's panel is "Closed projects" with the tag "Contracts traced from public records" the same way (Strata, the shell redesign). With no lines, Worth knowing is a Task zone row with its first-run or quiet sentence and its one link, and Waiting for you is a row in the side column with its empty sentence and "Go to Packages".
```

---

## 7. Projects and the project page (the Projects ticket)

### Section 5: replace the sentences of the Project header row about the agency line and the Follow control, and add to the Fact table row

```markdown
Under it, the implementing agency line in `body` `ink-muted`, kept to one line with a ghost "Show all agencies" when it needs more. The ID, country and status in the h1's line are weight 400. For World Bank staff the Follow control sits at the head's right when the page area allows, and under the agency line otherwise (Strata, the shell redesign).
```

Append to the **Fact table** row:

```markdown
On Summary, the tables sit two side by side from a page area of 75rem (Dates beside Money, Ratings beside Sectors and implementing agencies) and in one column below; their widths are measured on the page area beside the sidebar (Strata, the shell redesign).
```

---

## 8. Packages and the plan check (the Packages ticket)

### Section 5: add to the Plan check table row, and replace the Check line row's sentence on its indent

Append to the **Plan check table** row:

```markdown
Strata (the shell redesign): the plan check belongs to the Packages section (its address does not change), and its breadcrumb starts at Packages. Its order is the head, the finding with its method and change lines, the activities panel, "What changed" as a closed row that "See what changed" opens, and the baseline as a row with its action. A row's reference is a button that opens the row's records in the drawer: the reason, "What I checked", "From the plan row", the source, and "Open the activity" and "See the past range" as links; the row keeps the current mark while they show. The finding's count words mark the rows they count with `tint` and move focus to the first one's reference. The table has six columns from a page area of 60rem, three (Activity, Estimated (US$), What Strata found) from 40rem, since an open row shows the rest in the drawer, and cards headed by the badge below; no word in a cell breaks inside itself. The column head reads "Method and market approach". "What Strata found" opens its definition in a window. With no activity marked by a signal, the finding reads "No activity needs a look or is worth watching" (with its data notes), the head holds the check pill and no action, so it does not stick, and only data-note rows are marked. In a view without Packages (the public view), the plan check is lit as Projects and its breadcrumb starts at the project.
```

```markdown
Its text starts on the text edge of the panel it sits in, with no indent, on a `surface-2` block with 12px padding (Strata, the shell redesign; settles ticket 59's indent item).
```

---

## 9. The package workspace (the package ticket)

### Section 5: replace the first three sentences of the Package header and facts row, and add to the Range chart and Tables rows

```markdown
| Package header and facts | The package workspace's page head: the breadcrumb (Packages, then the project), the package's Description from its plan row as the `h1`, wrapped in full, never cut (section 3), its STEP reference in Roboto Mono 500 under it, and the purpose. The head does not stick; the box's scope chip names the package. The package's facts are its side panel, "From the plan row", in STEP's field names word for word: Method, Market Approach, Review Type, Estimated Amount (US$), Process Status and "In the plan", then the source line with a marker that opens the plan row in the drawer. Below the workspace threshold they are one line ("Request for Bids, Open - National, US$1,230,000, Pending Implementation") and "Show the plan row". ...
```

Append to the **Range chart** row:

```markdown
Strata (the shell redesign): when the time estimate holds back, lane 2 keeps its label in `chart-label` and the first-person sentence sits under the chart in `body`, with the neutral dashed-circle icon, never inside the lane. A number in the finding or the summary opens "Show the table" filtered to the rows it counts, scrolls the table's title under the bar and moves focus to the count line, which repeats the pressed number and no other ("Showing the 2 of 49 packages signed within 1.5 months."; "Showing the packages in the middle half, from 3.3 to 7.9 months."), with a flush ghost "Show all {total}" after it; the first counted row is then inside the first screen at 1440 by 900 and 390 by 844. A number and its "months" never break apart. Below 20 comparable packages the first-person sentence that holds back ("I'm not giving a range: only seven comparable packages. Here are all seven.") is zone 1's finding, in the `finding` style, the count follows in `body`, and the table opens with the page. A dot's tooltip sits above every dot in the lane, or below them all.
```

Append to the **Tables** row:

```markdown
In a card (Strata, the shell redesign), the row's name is its heading with no label over it, and the other values share a grid of 120px columns.
```

---

## 10. Lessons (the Lessons ticket)

### Section 5: add a row

```markdown
| Lessons page | Strata (ticket 39; the shell redesign). A wide page: the head, then the digest sentence as the page's finding (rule 43), or on a first visit its status sentence in `lead`, its caption and the sources note, then "Changed where you used it", "New", "Your reports" and "The library" in that order, each a Task zone: a panel when it holds lessons or reports, a row when it holds only its sentence. The reviewer pages are sidebar items under Lessons, not sub-tabs. A review page uses the workspace layout, with its history list as the side panel where it has one. |
```

---

## 11. Drafts (the Drafts ticket)

### Section 5: add to the State stepper and Draft bar rows, and add a Drafts list row

Append to the **State stepper** row:

```markdown
Strata (the shell redesign): on a draft's page it sits in the side panel "State of this draft", with what the draft was made from, when it was drafted and, once checked, "Checked by you on {date}."; below the workspace threshold the stepper takes one line in the page head, under the subtitle, and the rest of the side panel follows the draft.
```

Append to the **Draft bar** row:

```markdown
It spans the work's columns (Strata, the shell redesign). Before the act its first row says what exporting does, as today; after "Mark as checked" the hold line gives way to the decided line in `small` 600 `ink-heading`, "Checked by you on {date}." by role (`draft.tab.checkedYou`), Export to Word becomes the primary button and takes focus, and a polite status says "You marked these notes as checked. You can export them now." Nothing fades.
```

```markdown
| Drafts list | Strata (the shell redesign). One panel holding three groups, To check, Checked and Exported, each an `h2` with its count line in `caption` after it ("One draft.") and its rows: the draft's title as a link, then its project and the drafted, checked or exported line in `small`, then its notes and opened count in `caption`. Discarded drafts fold under the groups. With no drafts, a Task zone row with "You have no drafts to check.", its sentence and "Go to Packages". |
```

---

## 12a. How Strata works leaves Data (the refusal window ticket)

### Section 5: replace the Refusal row

```markdown
| Refusal | Plain body text under "In short": what I don't do, what I can do instead, and why I don't do it, each its own sentence from the copy file (`copy.refusals[key]`), never written by the model. Under it a flush ghost "See everything I turn down" opens a non-modal window, "What I turn down", that lists each refusal's lead and its reason from the same keys. Never an alert, an icon or the error state. A partial refusal opens "In short" and is followed by the answer (ticket 24; the shell redesign). |
```

### Section 5: add to the Readiness tables row

```markdown
Strata (the shell redesign): How Strata works is no longer a page: the deck at /present shows its figures, the refusal window holds "What I don't do", and `/data/how-strata-works` opens Data readiness.
```

### Sections 7, 9 and 11: edit the lines that name the page

- Section 7, the deck paragraph: "How Strata works keeps rule 5" becomes "The refusal window keeps rule 5".
- Section 9, third bullet: "Proposal figures and How Strata works figures carry no logo" becomes "Proposal figures carry no logo".
- Section 11, the deck paragraph: "For the deck and How Strata works" becomes "For the deck".

---

## 12b. Data readiness by the page area (the Data layout ticket)

### Section 5: add to the Readiness tables row, after 12a's sentence

```markdown
The Data pages lay out by the page area, never the window. Data readiness's headline is the page's finding; "What you can ask" and "Sources" are panels; "The hardest documents I read", "Plan pages the layout parser couldn't read" and "Fixes that would unlock the most" are closed Task zone rows with their one-sentence summaries. Data readiness and Sources and licenses are sidebar items under Data.
```

---

## 13a. The number tooltip (the number tooltip ticket)

### Section 5, "Shell and citation components": add Number tooltip; the Measure number and Dot tooltip rows point to it

```markdown
#### Number tooltip

The tooltip of every checkable number and every range chart dot: a Num in an answer, a draft, a section or a briefing, a Measure number on Data readiness, and a Dot (Strata, the shell redesign, after the user's earlier app). It says what the number is, where it came from, and what a click does, in that order, so a reader can trust a number before opening anything.

| Part | Text | Style |
|---|---|---|
| What | One sentence from the copy file for this number alone, filled with the tool's own values. "2" in "2 of 49 comparable packages": "Comparable packages signed within 1.5 months of their notice." "49" in the same sentence: "All comparable packages in the past range, including the four still open." A dot's What is its reference in mono, its months in `body` 700, then one sentence: "Kenya. Its notice was published September 17, 2021, and its contract was signed January 3, 2022." | `small` `ink` |
| From | Where the value came from, with its date: "From Procurement Notices and Contract Awards, through October 13, 2026." (`num.from.*`, one template per kind of number) | `caption` `ink-muted` |
| Action | What a click does, in words that name what opens, only when a click does it: "Select to see the two packages.", "Select to see all 49.", "Select to see its records." (`num.act.*`) | `caption` 600 `ink-heading` |

| Variant | Use when | Behavior on click |
|---|---|---|
| Rows | The number counts rows on the page or marks a band of them (a past range's count or statistic, a plan check's count word) | Opens the table filtered to its rows (the past range) or marks them where they already come first (the plan check), moves focus to the count line or the first row, and scrolls them under the bar |
| Record | The number comes from one record (a note's amount, a row's days, the plan's months) | Opens the record in the drawer |
| Window | A Measure number, a briefing's count word | Opens its window |
| Plain | An answer's number, matched by the verifier | Nothing more; no action line |
| Dot | A range chart's dot (DESIGN.md's Dot tooltip) | Opens the package's records in the drawer |

| State | Look | Behavior |
|---|---|---|
| Closed | The number with its dotted underline, tabular figures. A number with no tooltip and nothing to open is plain text with no underline | |
| Opening by pointer | Appears 150ms after the pointer rests, from the side that touches the number, over 160ms | A second number within 300ms of the last tooltip closing opens at once, with no movement. Nothing opens because the page scrolled a number under a resting pointer; the pointer has to move |
| Opening by keyboard | Appears at once | |
| Open | `surface`, 1px `line`, 4px corners, the popover shadow, 8 by 12px padding, at most `--tooltip-width` (20rem); under the number and left aligned with it, above it when there is no room below; a number inside the page's finding opens under the whole finding, so it never covers the sentence being read; a Dot's sits above or below every dot in the lane | Stays while the pointer is on the number or the tooltip; hides 100ms after it leaves both, at once |
| Dismissed | Hidden | Escape hides it until the pointer or the focus leaves the number |

Accessibility. Role: `tooltip`, the number's description (`aria-describedby`), never its name, so two numbers in one sentence that say different things are heard differently. A dot's tooltip is hidden from screen readers, because the dot's accessible name says the same, and its name says it opens the package's records. Keyboard: a number is a button in the tab order; focus shows the tooltip, Enter does what the action line says. Screen reader: hears the number, then the tooltip's three parts. Content on hover is dismissible, hoverable and persistent (WCAG 2.2, 1.4.13). A date, an "N of M" pair, or a number and its unit never breaks inside the tooltip.

| Do | Don't |
|---|---|
| Give each number its own What sentence; two numbers in one sentence share one only when they come from the same record and open the same thing | Reuse one number's sentence for its neighbour ("2" and "49" are different counts) |
| Name what the number is and where it came from, at the tool's rounding | Show a number the page does not show, except the record's own unrounded value behind a rounded amount, as the Signal line row already allows ("US$1.23 million" shows 1,230,000.00) |
| Promise only what the click delivers, and name it; a gate test opens every number and every dot whose tooltip has an action line and checks that it opened | Put a link or a button inside the tooltip |
| Give every number in one block the same timing and look | Underline a number that has no tooltip |
```

```markdown
| Measure number | See Number tooltip, Window variant. The window's own rules below stay. ...
| Dot tooltip | See Number tooltip, Dot variant: the reference, the months, one sentence with full dates, then the From and Action lines. Its timing rules below stay. ...
```

(Each row keeps the rest of its text.)

---

## 13b. The check window and the drawer (the check window ticket)

### Section 5: replace the Check line row's first sentences and add the window, and edit the Removed box row

```markdown
| Check line | Neutral, never green, in one `surface-2` block with the removed box under it, both on the block's text edge (Strata, the shell redesign): "Checked: 5 of 5 numbers match records; 2 of 2 quotes are on their pages." "Not checked: whether these are the right comparables." Then a flush text button, "How was that checked?", in `small` 600 `primary` with a dotted underline and `aria-haspopup="dialog"`, which opens a window titled "How I checked this answer" (or "this draft"). When the verifier removed a sentence, the window opens on "These counts include the two sentences I removed. The check line counts only the sentences I kept.", because the window counts every sentence written and the line only those on screen. Then the verifier's done line ("I ran six checks on the six sentences I wrote and removed two."), the six checks as an ordered list in the steps' own words (a draft's step 2 says "came back for this draft"), "A number passes only when a record holds it at the same rounding.", and the Answer ID, or "Draft ID {id}, run {run}", in mono, breaking anywhere. ...
```

(The row keeps the rest of its text, from "Its counts are the answer stream's".)

In the **Removed box** row, replace "Open by default under "In short"" with:

```markdown
Open by default, under the check line in the same `surface-2` block, after a 1px `line`
```

### Section 5, "Shell and citation components": add Evidence drawer, placement and motion; the component table's Evidence drawer row keeps its text after its first sentence and starts with a pointer

```markdown
#### Evidence drawer: placement, head and motion

The drawer holds the record or passage behind a claim, beside the claim (Strata, the shell redesign).

| Variant | Use when | Look |
|---|---|---|
| Beside the page | From 768px, by default | A column under the bar, sticky at the window's height. On a workspace page it fills from the work's columns plus a gutter to the window's edge, 384 to 600px, so the work keeps its place and width; on a wide page it is `clamp(384px, 40vw, 560px)` and the page narrows, keeping its left edge. A 1px `line` edge, no shadow |
| Over the page | Only if the user chooses it (`open.md`) | Fixed to the window's right edge at the same width, with a 1px `line-strong` left edge and the popover shadow, so it reads as lying on top; the page does not reflow, and its right columns sit under the drawer |
| Sheet | Below 768px | Full screen, modal, the page, the bar and the sidebar inert; slides up 24px over 200ms on `ease-drawer` |

| State | Look | Behavior |
|---|---|---|
| Opening | Opacity and 12px in from the right over 160ms on `ease-out` | Focus moves to its heading with `preventScroll`; the opener keeps the current mark (a row's `tint` and 3px bar, a dot's 2px `info-icon` ring, a marker's `tint`) |
| Open | The head: the title (the source's name, or a record's kind and reference) and one `caption` sentence that says what the source is ("Activity in the Northern Water Works Development Agency plan of October 9, 2026"), with the 44px close button; no eyebrow and no middle dots | On a list view it lands on the row that was clicked, marked with `tint`, scrolled into view under its head |
| Switching source | The new content replaces the old at once | |
| Closing | At once | Focus returns to the opener, or to the dot drawn in its place |

Accessibility. Role: a non-modal dialog named by its title from 768px; a modal sheet below. Keyboard: Escape closes it after a tooltip or window inside it; the close button is 44px. Screen reader: its heading takes focus on open.

| Do | Don't |
|---|---|
| Open beside the claim, so the claim and its source are on one screen | Open over the page's primary action |
| Keep one drawer for every kind of record | Animate its content or its close |
```

```markdown
| Evidence drawer | See "Evidence drawer: placement, head and motion" above for where it opens, its head and its motion (Strata, the shell redesign). Opens at what was clicked, with a switcher for the claim's other sources, ...
```

(The row keeps the rest of its text, from "Opens at what was clicked".)

---

## The deck: no change in this wave

The deck is rebuilt on its own branch, `deck/second-draft`. This wave's tickets do not edit `web/src/deck/*`; the tokens ticket keeps `--text-title` and `--radius-box` as deprecated aliases and exempts `web/src/deck/` from the uppercase rule until the deck branch's follow-up lands (listed with its lines in `tickets.md`, the tokens ticket's comments). When it lands, the two alias lines and the exemption leave DESIGN.md and `web/lint/rules.ts` in the same change.
