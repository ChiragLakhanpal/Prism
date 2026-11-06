# The ask bar and the page width: options

October 29, 2026. Design lead. A proposal for the owner: it changes no code and no other file.

The owner's direction of October 29, 2026:

> "On the packages page, all the content is squished to the left, which made sense from a UX perspective, but now the ask bar is at the bottom."
>
> "Give the ask bar more umf, it looks lost amongst the content, doesn't stand out."

What every option below keeps:

- One box for lookups and questions. The same combobox, the same intent rules (`web/src/lib/intents.ts`), the same One box list with its suggested questions, the scope chip, the Packages modes ("Check a plan", "Plan a package"), and "/" from anywhere outside a field.
- The answer opens at the top of the page column, as today.
- No translucency, no fade, and no new color. Motion stays inside DESIGN.md section 4's table.

## 1. The problem, measured

At 1440 by 900 with the rail, the package workspace keeps its work to 743 of the 1,296 px content width (columns 1 to 7), and its one side panel is 412 px tall, so the 553 px beside the work is empty grey on 87 percent of the page's height; the plan check leaves a 637 by 240 px empty block beside its finding. The ask box is a 640 by 40 px white field centered on the page column (x 432 to 1,072), so on the package workspace it sits 277 px right of the work's center, shares no edge with anything on the page, and moves 281 px when the drawer opens, while only a 1 px edge and a faint warm-grey shadow set it apart from the white panels it floats over.

The numbers behind those two sentences, from the local copy at http://127.0.0.1:50263 (Chromium, the rail at rest, World Bank staff in their own view):

| Page | Window | Content box | What the content uses | What is empty |
|---|---|---|---|---|
| Packages (/packages) | 1440 by 900 | x 104 to 1,400 | The list spans all 12 columns (x 105 to 1,399) | Nothing beside it. The list is not the squeezed page |
| Plan check (NWWDA, October 9, 2026) | 1440 by 900 | x 104 to 1,400 | Head and activities table span 12 columns. The finding and the method sentences stop at x 763 | 637 by 240 px beside the finding (y 245 to 485). The end rows keep their text to about x 715 |
| Package workspace (KE-NWWDA-229129-CW-RFB) | 1440 by 900 | x 104 to 1,400 | Work x 104 to 847 (743 px, 57 percent). Side panel x 989 to 1,400, 412 px tall, sticking 24 px under the bar | The 553 px right of the work on 87 percent of the page's 3,115 px. On every screen after the first, the side column is empty from y 492 to the window's foot |
| Package workspace | 1280 by 800 | x 104 to 1,240 | Work x 104 to 753 (649 px, 57 percent). Side panel x 883 to 1,240 | 87 percent, as at 1440 |
| Home (first visit) | 1440 by 900 | x 104 to 1,400 | Work x 104 to 847, side x 989 to 1,400 | 80 percent of the height beside the work |
| Any page | 1024 by 768 | x 96 to 992 | One column, 896 px | Nothing. The box (x 224 to 864) is centered on the content |

| The ask box | 1440 by 900 | 1280 by 800 | 1024 by 768 | 390 by 844 |
|---|---|---|---|---|
| Place | x 432 to 1,072 | x 352 to 992 | x 224 to 864 | x 16 to 374 |
| Size | 640 by 40 | 640 by 40 | 640 by 40 | 358 by 40; 358 by 76 with a scope chip |
| Its center against the work's center, on the package workspace | 277 px right | 244 px right | 0 | 0 |
| How much of it lies over the work | 415 of 640 px | 401 of 640 px | all | all |
| With the evidence drawer open | x 151 to 791, so its left edge moves 281 px; the work stays at x 104 to 847 | | | |

Its look: `surface` (#ffffff) on `page` (#f5f7f9) is 1.07:1, so the fill does not separate it, and over a white panel or a table row the fill is the same white. What separates it is a 1 px inset `line-strong` edge and `0 5px 25px rgba(160,158,143,.25)`, a warm grey at 25 percent that nearly vanishes over white. It is 40 px tall, under the 44 px of every button on the page, and its words are a 16 px placeholder in `ink-muted` beside a 16 px `ink-muted` icon. Nothing in it says "Strata", so it reads as one more field.

The page today, the package workspace at 1440 by 900, scrolled into the zones:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | ...zone 1's chart and its foot strip...                 +------------------------+ |
|(H)|                                                         | From the plan row      | |
|   | +----------------------------------------------+        | Method      Market     | |
|(F)| | Where the steps stand                        |        | Request for Open -     | |
|   | |                                              |        | Bids        National   | |
|(P)| | (v)----( )----(v)----(v)----(v)----(!)       |        | ...                    | |
|   | | Bid    Bidding Bid    Bid    Contr. Contract |        | Source ... (1)         | |
|(L)| | invit. doc.    open.  eval.  signed complet. |        +------------------------+ |
|   | | Done   No date Done   Done   Done   Late by  |                                   |
|(D)| |                                     1,840 d. |                                   |
|   | +----------------------------------------------+                                   |
|   | 2  Planned date for each step     Show             empty grey, 553 px wide, on     |
|   | ------------------------------------------------   87 percent of the page height   |
|   | 3  Procurement risks and what helped                                               |
|   |    None of the three projects with                                                 |
|   |    comparable packages has a completion                                            |
|   | ------------------------------------------------                                   |
|   | 4  Procurement approach options                                                    |
|   |                      +---------------------------------------+                     |
|   |                      | Q (KE-NWWDA-229129-CW-RFB x) Ask a.. /|                     |
|   |                      +---------------------------------------+                     |
+---+------------------------------------------------------------------------------------+
```

How it got here. The plan (`docs/design/redesign-2026-10/plan.md`, section 7.9) left-aligns the content and keeps the air on the right, where the evidence drawer opens; the box then sat in the bar, starting on the content's left edge. Ticket 113 moved the box to the bottom center of the page column at the owner's request of October 27, 2026. The content kept its left axis and the box took a center axis, so a workspace page now has two axes and the box lines up with neither. The 113 critique scored this alignment 3 and named the fix for a page's own foot bar (`.notes/113-critique-r2.md`, item A); the same fix applies to the work.

## 2. The ask bar: three options

### Option A. A stronger floating bar, on the grid

The box stays where the owner put it, floating at the window's foot, and gains presence by size, a name, an edge and its own elevation. It also takes the work's columns, so it sits under what you read: columns 3 to 10 on a wide page, the work's columns 1 to 7 on a workspace page, and the columns of a page's own foot bar (the draft bar, the grade bar) while one sticks.

Patterns to look up on Mobbin: Perplexity's follow-up bar pinned under an answer thread ("Ask follow-up"), ChatGPT's and Claude's composer at the foot of a chat, and Notion AI's prompt bar ("Ask AI anything"). Mobbin's pattern searches "Chat input" and "Search bar" find more. What I borrow: a visible name inside the bar, a send control that says what Enter will do, and a shadow heavier than the page's popovers, kept for the one part that floats over the work.

At 1440, the package workspace:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages > Water and Sanitation Development (P156634)   +------------------------+ |
|(H)| Drilling of 4 Number Exploratory Boreholes ...          | From the plan row      | |
|   | KE-NWWDA-229129-CW-RFB                                  | Method      Market     | |
|(F)|                                                         | Request for Open -     | |
|   | +----------------------------------------------+        | ...                    | |
|(P)| | 1  How long it took                          |        | Source ... (1)         | |
|   | |    Strata found                              |        +------------------------+ |
|(L)| |    2 of 48 comparable packages, fewer than   |                                   |
|   | |    1 in 10, were signed within the plan's    |   the side column stays clear     |
|(D)| |    2.1 months.                               |   of the box                      |
|   | |                                              |                                   |
|   | |    . .:::::.:.:  . ..    .     .  .          |                                   |
|   | |                                              |                                   |
|   | |    ...                                       |                                   |
|   | |                                              |                                   |
|   | +----------------------------------------------+                                   |
|   |                                                                                    |
|   | +==============================================+                                   |
|   | | Q  Ask Strata | (KE-NWWDA-229129-CW-RFB x)   |                                   |
|   | |                 Ask about this package  [/]  |                                   |
|   | +==============================================+                                   |
|   | x 104 to 847, the work's columns 1 to 7, 56 px tall,                               |
|   | 16 px above the window's foot, the float shadow under it                           |
+---+------------------------------------------------------------------------------------+
```

At 1440, a wide page (Packages, and the same on the plan check):

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages                                        [Check a plan] [Plan a package]    |
|(H)| +--------------------------------------------------------------------------------+ |
|   | | You have no packages in progress and one checked plan.                         | |
|(F)| | Package or plan        Type      Country     Project      Last worked on       | |
|   | +--------------------------------------------------------------------------------+ |
|(P)|                                                                                    |
|   |               +=====================================================+              |
|(L)|               | Q Ask Strata | Open a project or package, or ask [/]|              |
|   |               +=====================================================+              |
|(D)| x 325 to 1,179: columns 3 to 10, centered on the content                           |
+---+------------------------------------------------------------------------------------+
```

At 390:

```
+-------------------------------------+
| = Menu  WBG  Strata                 |
+-------------------------------------+
| < Water and Sanitation Developme... |
| Drilling of 4 Number Exploratory    |
| Boreholes In Wajir County           |
| KE-NWWDA-229129-CW-RFB              |
|                                     |
| +---------------------------------+ |
| | 1 How long it took              | |
| | Strata found                    | |
| | 2 of 48 comparable              | |
| | packages, fewer than            | |
| | 1 in 10, were signed...         | |
| +---------------------------------+ |
|                                     |
| +=================================+ |
| | (KE-NWWDA-229129-CW-RFB x)      | |
| | Ask about this package    [<-]  | |
| +=================================+ |
| x 16 to 374, 16 px above the foot   |
```

The look, left to right:

- The bar is 56 px tall from 768 px, the navy bar's height (`--bar-height`), so the two parts of the frame share one size. Below 768 px one row is 48 px, and with a scope chip it takes two rows, about 84 px.
- `surface` fill, `radius-sm` corners (it stays a control), and a 1 px `primary` edge in place of `line-strong`. That is the secondary button's edge, which reads as "act here" (10.31:1 on `surface`, 9.60:1 on `page`).
- A new elevation step, `shadow-float`: `0 1px 2px rgba(0,34,68,.12), 0 8px 24px rgba(0,34,68,.16)`, tinted from brand navy, under the bar alone. Today's popover shadow stays on popovers.
- A lucide `search` icon at 20 px in `primary`.
- The name "Ask Strata" in `button` (14/20, 600) `ink-heading`, then a 24 px `line` divider, 12 px on each side. It pairs with the answer's byline. You ask under "Ask Strata", and the answer opens under "Strata, in short" (DESIGN.md section 1, principle 6). The name hides when the box is narrower than 40rem, as "Within" already hides below 35rem, and below 768 px.
- The scope chip and the field as today, the field in `body` (16 px).
- At rest, the "/" Key hint at the end. Once the box holds text, the hint's place holds the Enter button: 40 by 40, `radius-sm`, a 1 px `primary` border, a 16 px lucide `corner-down-left` in `primary`, `tint` on hover. It does what Enter does, and its name says so ("Ask this", "Open P130164"). It is never filled, so each page keeps one solid button (the blueprint's Von Restorff row).

Tokens from DESIGN.md: `surface`, `primary`, `ink-heading`, `ink-muted`, `line`, `tint`, `focus`; `radius-sm`; type `button`, `body`, `caption`; space 12 inside and 16 under the bar; `--bar-height`; the Key hint, Scope chip, One box list and Byline components. New, with a DESIGN.md line first: `shadow-float` (section 4, Elevation), and the box's `primary` edge (section 2's paragraph on the box).

What changes in `web/src`:

- `styles/app.css`: the `ask-bar` utility takes its width and place from the grid: columns 3 to 10 from a page area of 64rem, 2 to 11 from 48rem, all 12 below; on a workspace page from a frame of 75rem, the work's columns, from the `--work-inline` the frame already computes. `--shadow-float` joins `@theme`.
- `components/OneBox.tsx`: the 56 px row, the name and divider, the 20 px `primary` icon, the `primary` edge, and the Enter button in the "/" hint's slot.
- `components/IntentBox.tsx`: hands OneBox the selected option's label for the Enter button's name.
- `lib/sticky.ts`: while a page's foot bar sticks, writes `--ask-inset-start` and `--ask-inset-end` from that bar's edges, so the box centers over it (113's deferred item 1, as the critique wrote it).
- `copy.ts` and `gallery/copy.ts`: `box.name` ("Ask Strata") and the Enter button's name. `gallery/pages.tsx`: the gallery's box.
- Tests: the place and size checks in `web/tests/shell.spec.ts` and `box.spec.ts`, the draft bar case in `drafts.spec.ts`, and `axe.ts`.

Accessibility:

- The field gets a visible label, "Ask Strata", and its accessible name starts with those words (WCAG 3.3.2 and 2.5.3). The placeholder sentence becomes its description.
- The Enter button is 40 by 40 (2.5.8), named by the option Enter will choose, and shows only while the box holds text, so it never needs a held state.
- The focus ring stays: 2 px `focus`, 2 px outside the box, while anything in it has focus.
- The bar covers 72 px of the window's foot instead of 56. `useStickyPadding` measures the part, so the bottom scroll padding grows with it and Tab never leaves a focused element under the box (2.4.11).
- The `primary` edge is 9.60:1 on `page` (1.4.11 needs 3:1). The shadow is decoration.
- At 320 px the name hides and the bar reflows to the window less 32 px (1.4.10). Nothing moves, so reduced motion needs nothing.

Risk: a bigger bar covers more of each screen (72 of 900 px, 8 percent, up from 6), and its center now differs between a wide page and a workspace page.

### Option B. Docked under the bar on content pages, the first tool on Home

On Home the box is the page's first tool, in the work's columns right under the briefing, with the three suggested questions shown under it instead of waiting for focus. On every other page it docks in a white band under the navy bar, starting on the content's left edge, and sticks with the bar from 1024 px. This is the blueprint's own wireframe ("The box sits in a white band under the navy bar on every page") and the laws table's Jakob's law row ("search at the top").

Patterns to look up on Mobbin: the search engine pattern, a large box centered on the home page and a box docked at the top of every results page (Google, Bing). data.worldbank.org does the same: a large search on its home page and a smaller one in the header of its inner pages. GitHub's header search is the docked half. What I borrow: the box as the home page's first act, and a fixed top place everywhere else.

At 1440, a content page:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | +----------------------------------------------+  the band: surface, 64 px,        |
|(H)| | Q Ask Strata (KE-NWWDA-229129-CW-RFB x) Ask /|  a line under it; sticks with     |
|   | +----------------------------------------------+  the bar from 1024 px             |
|(F)|------------------------------------------------------------------------------------|
|   | Packages > Water and Sanitation Development (P156634)                              |
|(P)| Drilling of 4 Number Exploratory Boreholes ...          +------------------------+ |
|   | KE-NWWDA-229129-CW-RFB                                  | From the plan row      | |
|(L)|                                                         | Method      Market     | |
|   | +----------------------------------------------+        | ...                    | |
|(D)| | 1  How long it took                          |        | Source ... (1)         | |
|   | |    Strata found                              |        +------------------------+ |
|   | |    2 of 48 comparable packages, fewer than   |                                   |
|   | |    1 in 10, were signed within the plan's    |                                   |
|   | |    2.1 months.                               |                                   |
|   | |                                              |                                   |
|   | +----------------------------------------------+                                   |
|   |                                                                                    |
|   | nothing floats at the window's foot                                                |
+---+------------------------------------------------------------------------------------+
```

At 1440, Home:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Your briefing for Thursday, October 29                  +------------------------+ |
|(H)| One plan changed in the past 15 days. One of            | Waiting for you        | |
|   | its activities needs a look.         (finding)          | ...                    | |
|(F)|                                                         | Go to Drafts           | |
|   | +==============================================+        +------------------------+ |
|(P)| | Q Ask Strata | Open a project or package [/] |                                   |
|   | +==============================================+                                   |
|(L)|   Ask, for example                                                                 |
|   |   > How long did works contracts in Kenya take?                                    |
|(D)|   > Which Kenyan plans changed this month?                                         |
|   |   > What went wrong in rural water packages?                                       |
|   |                                                                                    |
|   | +----------------------------------------------+                                   |
|   | | Worth knowing                                |                                   |
|   | +----------------------------------------------+                                   |
+---+------------------------------------------------------------------------------------+
```

At 390, a content page:

```
+-------------------------------------+
| = Menu  WBG  Strata                 |
+-------------------------------------+
| +---------------------------------+ |
| | Q Open a project or package..   | |
| +---------------------------------+ |
|-------------------------------------|
| < Water and Sanitation Developme... |
| Drilling of 4 Number Exploratory    |
| Boreholes In Wajir County           |
|                                     |
| +---------------------------------+ |
| | 1 How long it took              | |
| | Strata found                    | |
| | 2 of 48 comparable              | |
| +---------------------------------+ |
|                                     |
| band and bar scroll away together   |
```

Tokens from DESIGN.md: `surface` (the band), `line` (its bottom edge), `line-strong` (the box's edge), `radius-sm`, space 8 around a 48 px box, `--bar-height`, `frame-top` (56 px becomes 120 px from 1024 px on content pages); on Home, the box as in Option A and the One box list's suggestion rows. New: none, but DESIGN.md's Top bar, Ask bar, One box list, Answer panel and section 10 rows change back toward their state before ticket 113.

What changes in `web/src`:

- `components/Frame.tsx`: a band slot in the page column under the header, sticky at `frame-top`, on every page but Home; the foot slot goes.
- `App.tsx` and `pages/HomePage.tsx`: Home renders the box in its work column under the briefing.
- `components/OneBox.tsx`: the list opens below the box again (`top-full` in place of `bottom-full`).
- `styles/app.css`: the `ask-bar` utility becomes the band; `--frame-top` adds the band from 1024 px.
- `lib/sticky.ts`: the top padding counts the band; the box leaves the bottom padding.
- `components/AnswerPanel.tsx`: the scroll target sits under a 120 px top.
- `components/DraftBar.tsx`, `pages/DraftPage.tsx` and `components/Judging.tsx`: the 64 px room and the 96 px spacer kept above the foot bars go.
- `web/index.html`: the first paint holds the band's 64 px, so nothing moves when the app arrives.
- Tests: `shell.spec.ts`, `box.spec.ts`, `answer.spec.ts`, `drafts.spec.ts`, `routes.spec.ts`, `home.spec.ts`, `sticky.ts`, `axe.ts`.

Accessibility:

- The box's search landmark comes before `main` on content pages, after the skip link, as people expect of a site search. "/" still reaches it.
- Sticky chrome at the top grows from 56 to 120 px, and on the plan check, whose head sticks, to about 216 of 900 px (24 percent). `scroll-padding-top` follows it, so focus is never hidden (2.4.11), but less of each screen is left for the work.
- Below 1024 px the band scrolls away with the bar, as the bar does today, so a phone keeps its screen. "/" then scrolls the page to the top to focus the box, which loses the reader's place.
- Nothing floats at the foot, so 113's foot-bar alignment and padding cases go away.

Risk: it undoes the owner's request of October 27 on every page but Home, and it stacks 120 px or more of sticky chrome over the work.

### Option C. A launcher in the rail and a command sheet

At rest nothing covers the page. A launcher heads the rail, above Home, and "/" or a press opens the box in a sheet centered on the frame, with the list under the field and the page's suggested questions in view at once. Choosing "Ask this" closes the sheet and opens the answer at the top of the page column, as today.

Patterns to look up on Mobbin: the command palette, also called the command menu (Linear's Cmd+K, Arc's command bar, Vercel's dashboard search, and GitHub's command palette, which its header's "Type / to search" opens). Raycast's window is the model for the foot of key hints; Raycast is a desktop app, so look at its own site if Mobbin lacks it. What I borrow: a sheet near the top third of the window, the list below the field, and a foot that names the keys.

At 1440, the sheet open on a package page:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages > Water and Sanitation Development (P156634)                              |
|[Q]| Drilling of 4 Number Exploratory ...   (the page, under the scrim)                 |
|   |                                                                                    |
|(H)|                 +------------------------------------------------+                 |
|   |                 | Q  Ask Strata | (KE-NWWDA-229129-CW-RFB x)     |                 |
|(F)|                 |                 Ask about this package         |                 |
|   |                 |------------------------------------------------|                 |
|(P)|                 | Ask about this package                         |                 |
|   |                 | > How long did packages like this take?        |                 |
|(L)|                 | > How many were advertised again, and why?     |                 |
|   |                 | > Were they signed above their estimates?      |                 |
|(D)|                 |                                                |                 |
|   |                 | Type a project ID such as P130164, a STEP      |                 |
|   |                 | reference, a loan number, or a question.       |                 |
|   |                 |                                                |                 |
|   |                 |                                                |                 |
|   |                 |                                                |                 |
|   |                 |------------------------------------------------|                 |
|   |                 | [Enter] choose  [Up] [Down] move  [Esc] close  |                 |
|   |                 +------------------------------------------------+                 |
|   |                 x 296 to 1,016 (720 px), its top 96 px down the window             |
+---+------------------------------------------------------------------------------------+
```

At 390, the launcher in the bar and the sheet open:

```
+-------------------------------------+
| = Menu  WBG  Strata        [Q Ask]  |
+-------------------------------------+
|                                     |
|+-----------------------------------+|
|| Ask Strata                  [x]   ||
||                                   ||
|| +-------------------------------+ ||
|| | (P156634 x) Ask about thi..   | ||
|| +-------------------------------+ ||
||                                   ||
|| Ask about this project            ||
|| > Which activities are late?      ||
|| > How did similar works go?       ||
|| > What changed since March?       ||
||                                   ||
||                                   ||
|| a sheet over the scrim, 16 px     ||
|| corners at its top                ||
|+-----------------------------------+|
```

The parts:

- The launcher in the rail: 40 by 40, `surface`, a 1 px `primary` edge, a 20 px `primary` `search` icon, `radius-sm`, and the rail's tooltip "Ask Strata" with the "/" Key hint. With the sidebar open, a 40 px row that looks like a field: "Ask Strata" and the "/" hint. Below 1024 px, a 44 px "Ask" button in the navy bar with the view switch's white edge.
- The sheet: a modal dialog named "Ask Strata", at most 720 px wide (the frame less its margins), centered on the frame, its top 96 px down the window; `surface`, `radius-md`, 1 px `line`, the popover shadow, over `scrim`. The box sits at its top (56 px, no edge of its own, a `line` under it), the One box list fills the body and scrolls inside, and a foot in the Foot strip's look (`page`, a 1 px `line` top) names the keys with Key hints ("Enter chooses", "Up and Down move", "Escape closes").
- Below 768 px the sheet fills the screen and rises from the bottom with `radius-lg` top corners, over `motion-sheet` on `ease-drawer`, as the Menu sheet does, with a 44 px close button.
- From 768 px it opens with the popover motion (opacity and scale 0.97 to 1, 160 ms, `ease-out`) and closes at once.

Tokens from DESIGN.md: `surface`, `page`, `line`, `primary`, `scrim`, `ink-heading`, `ink-muted`; `radius-sm`, `radius-md`, `radius-lg`; `motion-popover`, `motion-sheet`, `motion-exit`, `ease-out`, `ease-drawer`; the Key hint, Foot strip, Scope chip and One box list components. New, with a DESIGN.md line first: `scrim` behind the command sheet at every width (today it is only behind full-screen sheets below 768 px), and a launcher in the Sidebar, which today holds no verb but Expand and Collapse.

What changes in `web/src`:

- A new `components/AskSheet.tsx`: the dialog, its focus handling, and the key-hint foot.
- `components/Sidebar.tsx`: the launcher above Home in the open, rail and Menu sheet forms. `components/TopNav.tsx`: the "Ask" button below 1024 px.
- `components/Frame.tsx`: the foot slot goes; the page is inert while the sheet is open, as for the Menu sheet.
- `components/OneBox.tsx`: the list lays out below the field inside the sheet instead of as a popover above it. `components/IntentBox.tsx`: opens and closes the sheet and returns focus.
- `lib/packages.ts`: `enterBoxMode` opens the sheet in its mode for "Check a plan" and "Plan a package".
- `lib/sticky.ts`, `components/DraftBar.tsx`, `pages/DraftPage.tsx`, `components/Judging.tsx`: the box leaves the foot, so its padding and the room above the foot bars go.
- `styles/app.css`, `copy.ts`, `web/index.html` (the rail's first paint holds the launcher).
- Tests: `shell.spec.ts`, `box.spec.ts`, `answer.spec.ts`, `drafts.spec.ts`, `start-here.spec.ts` (the sidebar's order), `gallery-frame.spec.ts`, `axe.ts`.

Accessibility:

- The launcher is a button named "Ask Strata", with `aria-haspopup="dialog"`, `aria-expanded` and `aria-keyshortcuts="/"`.
- The sheet is a modal dialog: focus goes to the field, the rest of the page is inert, and Escape or the close button returns focus to the launcher, or to where focus was when "/" was pressed.
- After "Ask this", focus moves to the question's heading in the answer panel. "Close the answer" returns it to the launcher, since the box is gone.
- Nothing rests at the foot, so no focused element can sit under the box (2.4.11), and the bottom scroll padding goes.
- Under reduced motion the sheet appears and leaves at once.

Risk: at rest the box is a 40 px icon in a 64 px rail, so a new reader, such as the panel, may not find it, which is the opposite of more presence.

## 3. The content width: two options

Both options apply where the frame is at least 75rem, as the workspace layout does today. At 1024 px with the rail, and below, every page stays one column, and nothing there changes.

### Option W1. One wide column, and the zones use the right side

The package workspace and the planned package become wide pages, as the plan check already is. The head spans 12 columns, with the plan row's facts at its right in place of the side panel. Each zone spans 12 columns: its sentences keep to 65 characters on the left, its controls and short facts take its right four columns beside them, and its chart, tables and step tracker run the zone's full width.

At 1440, the package workspace:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages > Water and Sanitation Development (P156634)   Method       Market App.   |
|(H)| Drilling of 4 Number Exploratory Boreholes ...          Request for  Open - Nat.   |
|   | KE-NWWDA-229129-CW-RFB                                  Review Type  Estimated     |
|(F)| This page shows how comparable packages went...         Post         300,000.00    |
|   |                                                         Signed       Source (1)    |
|(P)|                                                                                    |
|   | +--------------------------------------------------------------------------------+ |
|(L)| | 1  How long it took                                                            | |
|   | |    Strata found                                       Planned months [ 2.1 ]   | |
|(D)| |    2 of 48 comparable packages, fewer than                                     | |
|   | |    1 in 10, were signed within the plan's             Dates I draft            | |
|   | |    2.1 months.                                        (8.1 middle)(x 15.4)     | |
|   | |                                                                                | |
|   | |    . .::::::.::.:.:   . . .      .        .       .  . ..                      | |
|   | |    |  [====|=====]          the chart across the zone                          | |
|   | |                                                                                | |
|   | |--------------------------------------------------------------------------------| |
|   | |    Note ... coverage 48 of 64 ...    Source: Procurement                       | |
|   | |                                      Notices, Contract ...                     | |
|   | +--------------------------------------------------------------------------------+ |
|   | +--------------------------------------------------------------------------------+ |
|   | | Where the steps stand                                                          | |
|   | | (v)-----------( )-----------(v)-----------(v)-----------(v)-----------(!)      | |
|   | | Bid invitation Bidding doc.  Bid opening  Bid evaluation Contract     Contract | |
|   | +--------------------------------------------------------------------------------+ |
+---+------------------------------------------------------------------------------------+
```

At 390 (as below a frame of 75rem today):

```
+-------------------------------------+
| = Menu  WBG  Strata                 |
+-------------------------------------+
| < Water and Sanitation Developme... |
| Drilling of 4 Number Exploratory    |
| Boreholes In Wajir County           |
| Request for Bids, Open - National,  |
| US$300,000.00, Signed               |
| Show the plan row                   |
|                                     |
| +---------------------------------+ |
| | 1 How long it took              | |
| | 2 of 48 comparable...           | |
| | Planned months [ 2.1 ]          | |
| | Dates I draft (8.1)(15.4)       | |
| | the chart, full width           | |
| +---------------------------------+ |
```

The parts:

- Page head: breadcrumb, `h1`, ID line and purpose in columns 1 to 7. The plan row's five facts in columns 9 to 12 of the head, as a definition list on the grey (`label` over `small`, two columns), its source marker on its last line. Below a page area of 75rem they fold into the facts line with "Show the plan row", as today.
- Task zone: a new aside slot. From a zone 60rem wide, the zone's sentences keep to `max-w-prose` and its aside takes the zone's right four columns. Zone 1's aside holds "Planned months" and "Dates I draft for this package".
- The past range's chart runs the zone's width, from 647 px today to about 1,190 px at 1440. The step tracker gets about 200 px a step, so its labels keep to one line.
- Foot strip: from a panel of 60rem, the note and the coverage line on the left, the source line on the right.
- The evidence drawer: as on every wide page, the page narrows and keeps its left edge, and the zones lay out again at the narrower width, at once, with no motion.
- The plan check: its head and table do not change. "What changed since the plan of March 5, 2026" and "Baseline for delay" sit side by side, in columns 1 to 6 and 7 to 12. The empty block beside the finding stays.

Tokens and components from DESIGN.md: the 12-column grid, its 32 px gutter, `max-w-prose`, `space-6` panel padding, `space-8` from the head to the first zone, `label`, `small`, `caption`; Page head, Task zone (Panel), Foot strip, Step tracker in its row form, the range chart. New, with a DESIGN.md line first: the Task zone's aside, the head's facts at its right, and two lines out of section 4's Page layouts (the package workspace and the planned package leave Workspace for Wide). The plan's section 6, which keeps the chart at 647 px so the drawer can open beside it, changes too.

What changes in `web/src`:

- `pages/PackagePage.tsx` and `pages/PlannedPackagePage.tsx` leave `components/Workspace.tsx` for the wide grid.
- `components/PageHead.tsx`: a facts slot at the head's right. `components/PackageFacts.tsx`: draws the facts there.
- `components/TaskZone.tsx`: the aside slot. `components/PastRange.tsx`, `components/TimeEstimate.tsx` and `components/RangeChart.tsx`: the controls move to the aside, and the chart takes the zone's width.
- `components/FootStrip.tsx`: the two-column form.
- `components/PlanCheck.tsx` and `pages/CheckPlanPage.tsx`: the two end rows side by side.
- `styles/app.css`: the drawer's width rule for `[data-workspace]` no longer applies to the package pages.
- Tests: `package.spec.ts`, `package-tracker.spec.ts`, `planned-package.spec.ts`, `time-estimate.spec.ts`, `wrapping.spec.ts`, `skeletons.spec.ts`, `sweep.spec.ts`, `check-plan.spec.ts`.

Accessibility:

- The reading and focus order stay as they are: the finding, then the zone's controls, then the chart.
- Lines keep to 65 characters inside a 1,200 px zone, so a wide zone never makes a long line (DESIGN.md's 72-character limit on prose).
- At 200 percent zoom on a 1440 px window, the page area is 720 px, so the page is one column again. At 320 px it reflows as today.
- When the drawer opens, focus stays on the opened mark, but the zone it sits in lays out again. A screen magnifier user can lose their place.

Risk: when the drawer opens, the zones and the chart lay out again under the reader, which the workspace layout was built to prevent (the plan's section 7.1, principle 5).

### Option W2. Two columns, and the right one holds the state

The package workspace keeps its two columns, and the right column holds what the reader needs on every screen: the plan row's facts at the top, then "Where the steps stand" as a list that sticks under the bar for the rest of the page. The plan check gets a right column beside its finding, "How I checked", which gathers the method, the comparison with the earlier plan and the baseline. The evidence drawer still opens in the right column's place, so nothing moves.

At 1440, the package workspace:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages > Water and Sanitation Development (P156634)   +------------------------+ |
|(H)| Drilling of 4 Number Exploratory Boreholes ...          | From the plan row      | |
|   | KE-NWWDA-229129-CW-RFB                                  | Method      Market     | |
|(F)|                                                         | Request for Open -     | |
|   | +----------------------------------------------+        | Source ... (1)         | |
|(P)| | 1  How long it took                          |        +------------------------+ |
|   | |    Strata found                              |        +------------------------+ |
|(L)| |    2 of 48 comparable packages, fewer than   |        | Where the steps stand  | |
|   | |    1 in 10, were signed within the plan's    |        | (v) Bid invitation     | |
|(D)| |    2.1 months.                               |        |  |  Done Sep 17, 2021  | |
|   | |                                              |        | ( ) Bidding document   | |
|   | |    . .:::::.:.:  . ..    .     .  .          |        |  :  No date            | |
|   | |                                              |        | (v) Bid opening        | |
|   | |    ...                                       |        |  |  Done Oct 19, 2021  | |
|   | +----------------------------------------------+        | ... two more done      | |
|   | 2  Planned date for each step        Show               | (!) Contract complete. | |
|   | ------------------------------------------------        |     Late 1,840 days    | |
|   | 3  Procurement risks and what helped                    | Source: the plan ...   | |
|   |                                                         +------------------------+ |
|   |                                                                                    |
|   | +==============================================+                                   |
|   | | Q  Ask Strata | (KE-NWWDA-229129-CW-RFB x)   |                                   |
|   | |                 Ask about this package  [/]  |                                   |
|   | +==============================================+                                   |
+---+------------------------------------------------------------------------------------+
```

At 1440, the plan check:

```
+----------------------------------------------------------------------------------------+
| WBG  Strata                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages > Water and Sanitation Development (P156634)                              |
|(H)| Northern Water Works Development Agency     (Nine checked) [Draft review notes]    |
|   | Procurement Plan of October 9, 2026                                                |
|(F)| ---------------------------------------------------------------------------------- |
|   | Strata found                                            +------------------------+ |
|(P)| One activity needs a look and two are                   | How I checked          | |
|   | worth watching; three have data notes.                  | Checked: 9 activities  | |
|(L)|                                                         | Delay from: the first  | |
|   | I checked every activity against its own dates,         | published plan date    | |
|(D)| its estimate and the project's closing date.            | Compared with Mar 5,   | |
|   |                                                         | 2026: 2 re-estimated   | |
|   |                                                         | Baseline: none saved   | |
|   |                                                         | [Save as baseline]     | |
|   |                                                         +------------------------+ |
|   |                                                                                    |
|   | +--------------------------------------------------------------------------------+ |
|   | | Activities in this plan                         Showing 6 of 9 activities.     | |
|   | | Activity  Method and market approach  Review  Estimated (US$)  Status  Found   | |
+---+-+--------------------------------------------------------------------------------+-+
```

At 390, the package workspace (as today):

```
+-------------------------------------+
| = Menu  WBG  Strata                 |
+-------------------------------------+
| < Water and Sanitation Developme... |
| Drilling of 4 Number Exploratory    |
| Boreholes In Wajir County           |
| Request for Bids, Open - National,  |
| US$300,000.00, Signed               |
|                                     |
| +---------------------------------+ |
| | 1 How long it took ...          | |
| +---------------------------------+ |
| +---------------------------------+ |
| | Where the steps stand           | |
| | (v) Bid invitation  Done        | |
| | ( ) Bidding doc.  No date       | |
| +---------------------------------+ |
| 2 Planned date for each step        |
```

The parts:

- Package workspace, right column: "From the plan row" as today at its top, scrolling with the page. Under it, 16 px down, the step tracker's Card, which sticks 24 px under the bar for the rest of the page. The tracker reads its own width (411 px at 1440, 357 px at 1280, under its 36rem row threshold), so it draws its stacked list with no change: each step's node, label, state and date, the line running down at the nodes' centers. Stacked, the card is about 615 px tall, so it fits under the bar in a 900 px window (804 px of room) and an 800 px one (704 px). It sticks only while the window is at least 45rem tall, and scrolls with the page in a shorter one.
- Zone 2, "Planned date for each step", now sits beside the tracker it explains.
- Below a frame of 75rem the tracker stays where it is today, after zone 1.
- Plan check, beside the finding: from a page area of 75rem, the finding and the method's first sentence in columns 1 to 7, and "How I checked" in columns 9 to 12, a Side panel whose definition list holds "Checked" (nine activities, against their own dates, their estimates and the project's closing date), "Delay measured from" (the first published planned date, and why), "Compared with" (the plan of March 5, 2026, two re-estimated, with "See what changed", which opens the change tables where they are today) and "Baseline" ("None saved yet", with a secondary "Save as the baseline"). The baseline row leaves the page's end. The activities table keeps all 12 columns, since six STEP columns need a 60rem frame. Beside the drawer the panel follows the method sentence.

Tokens and components from DESIGN.md: the workspace layout's columns 1 to 7 and 9 to 12, `space-4` between the side column's cards, `space-6` under the bar, `frame-top`; Side panel (labels in `label` over values in `small`), Card, Step tracker in its stacked form, Foot strip, Buttons (secondary), Text link. New, with a DESIGN.md line first: the Side panel row's rule on what sticks (the column's last card, not the whole panel), the Step tracker row's place from a frame of 75rem, and the Plan check table row's head band.

What changes in `web/src`:

- `components/Workspace.tsx`: the side slot spans the grid's height and no longer sticks as a whole; its `[data-side-sticky]` child sticks.
- `pages/PackagePage.tsx` and `pages/PlannedPackagePage.tsx`: the tracker renders in the side column from a frame of 75rem and after zone 1 below it, through a new `lib/useFrameAtLeast.ts`, the frame's twin of `lib/usePageAtLeast.ts`, which the judging page uses for the same reason. One place renders at a time.
- `components/StepTracker.tsx`: no change; it reads its width.
- `pages/CheckPlanPage.tsx` and `components/PlanCheck.tsx`: the head band and the "How I checked" panel. `components/BaselinePanel.tsx`: its sentence and button move into the panel. `components/ChangeTables.tsx`: "See what changed" opens them in place.
- `styles/app.css`: the side slot's sticky rule moves to `[data-side-sticky]`. `copy.ts`: the panel's title and labels.
- Tests: `package-tracker.spec.ts`, `package.spec.ts`, `planned-package.spec.ts`, `check-plan.spec.ts`, `skeletons.spec.ts`, `wrapping.spec.ts`, `sweep.spec.ts`.

Accessibility:

- The DOM order follows what the eye sees at each width, because the tracker renders in one place only, chosen by the frame's width (WCAG 1.3.2, 2.4.3).
- The tracker's arrow keys move focus inside a sticky part, so they use `preventScroll` while it sticks, as section 10 already requires of sticky parts.
- The tracker sticks only when the window can show all of it, so its foot is never out of reach (the 45rem height rule).
- The plan check's panel is a `section` named by its `h2`, after the method sentence in the DOM, so a screen reader hears the finding, then how it was checked, then the table.

Risk: the step tracker that ticket 115 built as a row becomes a list at the widths the owner uses, and its place now depends on the frame's width.

## 4. Recommendation

**The ask bar: Option A.** It keeps the owner's October 27 placement and the one box's behavior, and answers "more umf" with things a reader sees at once: a bar as tall as the navy bar, the name "Ask Strata" that pairs with the answer's "Strata, in short", a `primary` edge that says "act here", and a navy-tinted shadow kept for the one part that floats. Putting its edges on the grid matters as much as the look. On a workspace page it sits under the work instead of straddling the work and the empty column, it no longer moves 281 px when the drawer opens, and the same rule centers it over the draft bar, which closes the alignment item left from ticket 113. Option B gives the clearest place, but it undoes the owner's request on most pages and stacks 120 px of chrome over the work. Option C clears the page but hides the box at rest, which is the opposite of what the owner asked for.

**The width: Option W2.** It keeps the workspace's promise that nothing moves when the drawer opens, and it fills the right column with what a reader needs on every screen of a package: where its steps stand. Today the tracker shows once, between zone 1 and zone 2, squeezed into 743 px with "Late by 1,840 days" broken over two lines. In the right column it stays in view beside the zones that explain it. On the plan check, the same move fills the empty block beside the finding with how the check was done and the baseline, which today sit at the page's end. Option W1 gives the chart more room, but the zones lay out again whenever a source opens, and it leaves the plan check's empty block. With Option A, the page reads as two columns: the work and its ask bar on the left, the package's state on the right.

**The order to build them:**

1. **The ask bar on the grid** (Option A's place only: `styles/app.css` and `lib/sticky.ts`, the place checks in `shell.spec.ts`, `box.spec.ts` and `drafts.spec.ts`, and DESIGN.md's Ask bar row). About 90 minutes. It fixes the misfit the owner sees on every workspace page, and W2 needs it. At 1280 px a box centered on the page column reaches 109 px into the side column, where the sticky tracker's foot would be.
2. **The ask bar's look** (Option A's height, name, edge, `shadow-float` and Enter button: `components/OneBox.tsx`, `components/IntentBox.tsx`, `copy.ts`, the gallery, DESIGN.md sections 2 and 4). About 3 hours with its tests.
3. **The steps in the right column** (Option W2 on the package workspace and the planned package). About 3 hours.
4. **"How I checked" beside the plan check's finding** (Option W2 on the plan check). About 3 hours. It touches neither the box nor the workspace, so it can run beside step 3.

Each step needs DESIGN.md's lines first, a design review at 1440, 1280, 1024 and 390 px, and the rule of October 25 on when design tickets run, which the orchestrator applies.

Decisions for the owner:

- The box's edge: `primary` (my choice, it reads as "act here") or `line-strong` (today's control border, quieter).
- Whether the box may sit at a different center on a wide page (the content's center) and a workspace page (the work's center). The other choice is columns 1 to 7 on every page, which never moves but is not centered on a wide page.
- Whether the step tracker may be a list in the right column at 1280 and 1440 px, where ticket 115 made it a row.

## How I measured

- The local copy at http://127.0.0.1:50263, in Playwright's Chromium at 1440 by 900, 1280 by 800, 1024 by 768 and 390 by 844, with the rail at rest: Packages, the plan check (`/projects/P156634/procurement/northern-water-works-development-agency`), the package workspace (`/packages/KE-NWWDA-229129-CW-RFB`) and Home; the box at rest, focused with "/" (its suggestions open) and with a question typed; the workspace scrolled to 900 and 1,800 px; the evidence drawer open from the side panel's source marker; and the plan check at its end.
- "Empty on 87 percent of the page's height" counts 8 px bands of `main` in which no text and no filled or bordered element reaches past the work's right edge plus 8 px.
- Scripts and screenshots are in this session's scratchpad, `<scratchpad>/askbar/` (`shoot.cjs`, `measure2.cjs`, `shoot2.cjs`, `drawer.cjs`, `tracker.cjs`, `sketch.py`, and `shots/`), and go when the session ends; the scripts read nothing but the running app, so they can be run again.
- The sketches put one character at 16 px at 1440 (90 characters) and at 10 px at 390 (39 characters), with each edge on its measured column. Words inside them are shortened to fit.
