# Mobbin picks for the ask bar, and Option A refined

October 29, 2026. Design lead. The Mobbin pass that tickets 127 and 130 wait on. It reads with `docs/design/notes-2026-10-29/ask-bar-and-width-proposal.md` (the proposal) and changes no other file.

## What the pass found

Most products keep two boxes, one for search and one for asking: Linear has a Search page and "Ask Linear", Notion has Search and "Ask AI", Slite splits its header field into "Search" and "Ask", Apollo puts a search field in its bar and an assistant box on its page. Prism's one box is rarer. Its closest kin are Perplexity, whose one bar is the product, and the command palettes (GitHub, incident.io, GitBook), whose one field lists what Enter will do.

Three things hold across every bar I looked at:

- The bar sits on the column it serves, at that column's width, never centered on the window. Perplexity's follow-up bar takes the answer column; Notion's "Edit with AI" row takes the document column; Linear's selection toolbar centers on the list.
- The bar keeps a neutral edge and a soft shadow, and gives its one color to the control at its end. Only WRITER tints its edge (https://mobbin.com/screens/9652aa1a-2aeb-469c-8a84-12d4d01c788c), and that reads as its focus state.
- The control at the end keeps its place and changes its state with the text: Perplexity's send button turns from grey to teal once there is something to send, ChatGPT swaps its voice button for a send arrow.

None of them shows a name inside the bar; each uses its placeholder ("Ask a follow-up", "Ask Linear...", "Type / to search"). Prism's "Ask Prism" label is its own choice. I keep it, because the owner's complaint was that nothing in the box says Prism, and because it is the field's visible label (WCAG 3.3.2). It no longer rests on pairing with the answer's byline, since the tuck-away inventory of the same day (`tuck-away-inventory.md`, item 1) drops the visible "Prism, in short".

## The three picks

### 1. Perplexity, "Adding a follow-up question"

https://mobbin.com/flows/7a9f49c2-226d-469d-b2f0-4ab729a76f8f (the chip row is its second screen, https://mobbin.com/screens/b9da0940-b342-4ac5-8077-4241a02fd609)

What it does well. The bar sits at the foot of the answer column and takes that column's width, so its edges line up with the text above it and it reads as part of the thread, not as a control laid over the page. A quoted selection drops into the bar as a chip on its own row above the text, and the send button fills only once the bar holds something to send, a chip or text, so the bar's state can be read without touching it.

What Prism borrows. The bar's edges on the column it serves: the work's columns 1 to 7 on a workspace page, columns 3 to 10 on a wide page, and the draft bar's column on a draft. One fixed slot at the bar's end whose state follows the text: the "/" Key hint at rest, the Enter button once the box holds text. The chip row above the text when the bar is too narrow for both, which is the 390 px form below.

Not borrowed. The filled send button (Prism keeps one solid button per page, so the Enter button is outlined), the microphone and the model menu, and the pill corners (Prism's controls take 4 px).

### 2. incident.io, the command palette

https://mobbin.com/screens/f1b4ccbd-d6f6-4ccb-89b5-3c48d9fd2151

What it does well. One field answers with rows grouped by kind under small grey names ("Actions", "Navigation", "Incidents"), each row an icon, a label and a small mark at its end, so a typed word shows at once what kinds of thing it can mean. A foot strip names the keys in words ("To navigate", "To select"), so the palette teaches itself without a help page.

What Prism borrows. A foot strip on the One box list, in the Foot strip's look, with Key hints: "Enter chooses", "Up and Down move", "Escape closes". It shows where Key hints show (from 768 px, on a device that can hover) and is `aria-hidden`, since the combobox already names its keys. The list's rows keep their anatomy, which already matches: a 16 px icon, the label with any ID in mono, a `caption` line, and the Enter key hint at the end of the option Enter will choose. GitBook's palette (https://mobbin.com/screens/3a322387-f680-44e9-bc8f-8c9306eae093) has the same foot, quieter still: "Select", "Open", "Close" with their keys.

Not borrowed. The colored severity badges, and the modal. Prism's list stays a popover above the bar, so the page beside it stays usable.

### 3. Linear, the selection toolbar

https://mobbin.com/screens/3f36e39e-2b9e-4145-bee2-f43a3cf21f7b

What it does well. When rows are selected, a white bar floats at the foot of the list, centered on the list's column and not on the window, and a soft shadow is the only thing that lifts it off the white rows under it, so it reads as a tool held over the work rather than a part of the page. It holds a count and a word, "6 selected" and "Actions", so nothing in it needs decoding.

What Prism borrows. The rule that a floating bar centers on the column it serves, which is why the box sits on the work's columns on a workspace page and over the draft bar's column on a draft, and why its center may differ between a wide page and a workspace page (the owner's call of October 29). And the elevation: a shadow visibly heavier than a popover's, tinted from Prism's own navy (`shadow-float`), kept for the one part that floats over the work. Aboard (https://mobbin.com/screens/d5f21cd3-73d2-48ff-b9b9-6ed83ad1f73e) and LangChain (https://mobbin.com/screens/6fbcce8e-09c0-47df-b701-da468e82af09) float the same white bar.

Not borrowed. Appearing on demand (Prism's box is always there) and the dark variants (YNAB, ClickUp).

## Option A, refined

What changed from the proposal's Option A, and why:

1. No divider after the name. A divider between "Ask Prism" and the chip reads as two controls, which is what Slite's split field looks like. The chip's own border separates them.
2. The One box list shares the bar's shadow. While it is open the list is the bar's upper half, so it takes `shadow-float` too, and it gains the foot strip of key hints from pick 2.
3. "Within" shows when the bar is at least 42rem wide, where today it shows from 35rem. The name takes 100 px of the row, and at 1280 px on a workspace page (649 px) the row is otherwise 12 px short of the placeholder's 176 px.
4. The 390 px form has two heights: 48 px with one row, 96 px when a STEP reference's chip takes the first row. A P-code's chip fits beside the text, so a project page keeps one row.
5. The edge stays `primary`, the owner's call. Every bar seen keeps a neutral edge and gives its one color to the control at its end, so if the `primary` edge fights the page head's secondary buttons in the gallery, `line-strong` is the fallback, with no other change.

The rest stands as proposed: one row of 56 px from 1024 px (the two-row chat composer belongs to products where the composer is the page; Prism's page is the work), the name, the `primary` search icon, the scope chip and the field as today, the Enter button in the "/" hint's slot, and the edges on the grid.

### At 1440 px, the package workspace, at rest

One character is 16 px (90 characters). Each edge sits on its measured column. Words inside are shortened to fit.

```
+----------------------------------------------------------------------------------------+
| WBG  Prism                                                [View: World Bank staff v]  |
+---+------------------------------------------------------------------------------------+
|   | Packages > Water and Sanitation Development (P156634)   +------------------------+ |
|(H)| Drilling of 4 Number Exploratory Boreholes ...          | From the plan row      | |
|   | KE-NWWDA-229129-CW-RFB                                  | Method      Market     | |
|(F)|                                                         | Request for Open -     | |
|   | +----------------------------------------------+        | ...                    | |
|(P)| | 1  How long it took                          |        | Source ... (1)         | |
|   | |    Prism found                              |        +------------------------+ |
|(L)| |    2 of 48 comparable packages, fewer than   |                                   |
|   | |    1 in 10, were signed within the plan's    |   the side column stays clear     |
|(D)| |    2.1 months.                               |   of the box                      |
|   | |                                              |                                   |
|   | |    . .:::::.:.:  . ..    .     .  .          |                                   |
|   | |                                              |                                   |
|   | +----------------------------------------------+                                   |
|   |                                                                                    |
|   | +==============================================+                                   |
|   | |Q Ask Prism (Within KE-NWWDA-229129-CW-RFB x)|                                   |
|   | |               Ask about this package     [/] |                                   |
|   | +==============================================+                                   |
|   | x 104 to 847, the work's columns 1 to 7, one row of 56 px (two lines here because  |
|   | a character is 16 px), 16 px above the window's foot, shadow-float under it        |
+---+------------------------------------------------------------------------------------+
```

The bar alone, closer. One character is 8 px, so the bar's 743 px is 93 characters, and 14 and 16 px text runs at about one character a letter.

At rest. From the left: 12 px, the 20 px `search` icon in `primary`, 8 px, "Ask Prism" in `button` `ink-heading`, 12 px, the Scope chip, 12 px, the field with its placeholder in `ink-muted`, and the "/" Key hint 12 px from the right edge.

```
+===========================================================================================+
|  Q Ask Prism  (Within KE-NWWDA-229129-CW-RFB x)  Ask about this package              [/] |
+===========================================================================================+
```

With text. The Enter button takes the hint's slot: 40 by 40, `radius-sm`, a 1 px `primary` edge, a 16 px `corner-down-left` in `primary`, `tint` on hover, never filled, 8 px from the edge and 8 px from the top and bottom. Its name is the option Enter will choose, "Ask this" here, shown as its tooltip. The field's text starts where it started, so nothing the eye is on moves; the field scrolls as you type.

```
+===========================================================================================+
|  Q Ask Prism  (Within KE-NWWDA-229129-CW-RFB x)  How long did works contracts in Ke [<-] |
+===========================================================================================+
```

Focused and empty. The One box list opens above the bar at once, 8 px up, at the bar's width: `surface`, a 1 px `line` edge, `radius-md`, `shadow-float`. The hint line, then the page's suggested questions in a group named in `label` `ink-muted`, then the foot strip. The 2 px `focus` ring sits 2 px outside the bar while anything in it has focus.

```
+-------------------------------------------------------------------------------------------+
| Type a project ID such as P130164, a STEP reference, a loan number, or a question.        |
|                                                                                           |
| Ask about this package                                                                    |
|  > How long did packages like KE-NWWDA-229129-CW-RFB take from notice to signed contract? |
|  > How many packages like KE-NWWDA-229129-CW-RFB were advertised again, and why?          |
|  > Were packages like KE-NWWDA-229129-CW-RFB signed above or below their cost estimates?  |
|-------------------------------------------------------------------------------------------|
| [Enter] chooses   [Up] [Down] move   [Esc] closes                                         |
+-------------------------------------------------------------------------------------------+
                                           8 px
+===========================================================================================+
|  Q Ask Prism  (Within KE-NWWDA-229129-CW-RFB x)  Ask about this package              [/] |
+===========================================================================================+
```

With a question typed. The first row is the option Enter will choose: `tint` fill, a 3 px `primary` bar inset on its left, the "Enter" Key hint at its end. The bar's Enter button does the same thing, so Escape can close the list and the button stays.

```
+-------------------------------------------------------------------------------------------+
| [>] Ask this                                                                      [Enter] |
|     Within KE-NWWDA-229129-CW-RFB                                                         |
| [+] Plan a package from this sentence                                                     |
|     I'll read the criteria from your sentence and open a new package. You can change...   |
|-------------------------------------------------------------------------------------------|
| [Enter] chooses   [Up] [Down] move   [Esc] closes                                         |
+-------------------------------------------------------------------------------------------+
                                           8 px
+===========================================================================================+
|  Q Ask Prism  (Within KE-NWWDA-229129-CW-RFB x)  How long did works contracts in Ke [<-] |
+===========================================================================================+
```

On a wide page (Packages, the plan check) the same bar spans columns 3 to 10, x 325 to 1,179, with no scope chip and the wide placeholder, "Open a project or package, or ask a question". On a draft it centers over the draft bar's column, 16 px above it. At 1280 px the workspace bar is 649 px wide (x 104 to 753): the name stays, and the chip drops "Within". With the evidence drawer open on a workspace page the bar does not move.

### At 390 px, the package workspace, at rest

One character is 10 px (39 characters).

```
+-------------------------------------+
| = Menu  WBG  Prism                 |
+-------------------------------------+
| < Water and Sanitation Developme... |
| Drilling of 4 Number Exploratory    |
| Boreholes In Wajir County           |
| KE-NWWDA-229129-CW-RFB              |
|                                     |
| +---------------------------------+ |
| | 1 How long it took              | |
| | Prism found                    | |
| | 2 of 48 comparable              | |
| | packages, fewer than            | |
| | 1 in 10, were signed...         | |
| +---------------------------------+ |
|                                     |
| +=================================+ |
| | (KE-NWWDA-229129-CW-RFB x)      | |
| | Ask about this package          | |
| +=================================+ |
| x 16 to 374, two rows, 96 px,       |
| 16 px above the foot                |
```

The bar alone, closer, at 8 px a character (358 px is 45 characters). The name, the icon and the "/" hint hide, as the Ask bar row already has it below 768 px. A STEP reference's chip shows the ID only and takes the first row: 8 px, the 32 px chip, 8 px, the 40 px text row, 8 px, which is 96 px. Nothing shows in the end slot at rest, since "/" is a keyboard act; the Enter button appears with the first character, at the row's end, and the text's start does not move.

```
+===========================================+
| (KE-NWWDA-229129-CW-RFB x)                |
| Ask about this package                    |
+===========================================+

+===========================================+
| (KE-NWWDA-229129-CW-RFB x)                |
| How long did works contracts in Kenya [<-]|
+===========================================+
```

A project page keeps one row of 48 px, because a P-code's chip leaves the placeholder its 176 px. The Enter button then sits 4 px from the top and bottom.

```
+===========================================+
| (P156634 x)  Ask about this project       |
+===========================================+

+===========================================+
| (P156634 x) Does P156634 need a look? [<-]|
+===========================================+
```

The list opens above the bar at the bar's width, at most the window less the bar and 96 px, and scrolls inside. Its foot strip hides here, since Key hints hide on a device that cannot hover.

### The tokens it uses

From DESIGN.md, unchanged:

- Color: `surface` (the bar and the list), `page` (the list's foot strip), `primary` (the edge, the icon, the Enter button's edge and icon, the Enter option's 3 px bar), `ink-heading` (the name), `ink` (typed text, the chip's ID), `ink-muted` (placeholder, key hints, group names, caption lines), `line` (the list's edge and the foot strip's top), `line-strong` (the chip's border, the Key hint's box), `tint` and `tint-hover` (the Enter option, the Enter button on hover), `focus` (the ring).
- Shape: `radius-sm` (the bar, the Enter button, key hints), `radius-md` (the list), `radius-pill` (the chip).
- Type: `button` (the name), `body` (the field), `small` (the chip), `caption` (key hints, the hint line, second lines), `label` (group names), `--font-mono` (IDs).
- Space: 8 (icon to name, the button's inset, the bar to the list, the phone's padding), 12 (inside the bar, the foot strip's side padding), 16 (under the bar, and above a page's own foot bar). `--bar-height` (56 px) for the bar's height from 1024 px.
- Components: Ask bar, Scope chip, One box list, Key hint, Foot strip.
- Motion: none. The bar is always there, and the list opens and closes at once, as it does today.

New, each with its DESIGN.md line first:

- `--shadow-float: 0 1px 2px rgba(0,34,68,.12), 0 8px 24px rgba(0,34,68,.16)`, under the bar and its list (section 4, Elevation). `--shadow-popover` stays on every other popover, tooltip and window.
- The box's 1 px `primary` edge, drawn inside it (section 2's paragraph on the box, and section 5's Ask bar row).
- The list's foot strip and its three Key hints (section 5, One box list; copy keys `box.keys.choose`, `box.keys.move`, `box.keys.close`).
- "Within" from a bar of 42rem (section 5, Scope chip).
- The bar's place on the grid: `--work-inline` on a workspace page, columns 3 to 10 on a wide page, and `--ask-inset-start` and `--ask-inset-end` from `lib/sticky.ts` while a page's own foot bar sticks (section 5, Ask bar; section 10, sticky parts).
- The name "Ask Prism" (copy key `box.name`), as the field's visible label.

## Seen on the way, and left out

- Gemini's halo behind its box (https://mobbin.com/screens/8193ba34-c179-46f5-ba76-7506d15d78eb). A gradient glow; DESIGN.md allows no translucency, no fade and no new color.
- The two-row chat composers: ChatGPT (https://mobbin.com/screens/8229c408-df4e-4555-af78-87e736356db1), Claude (https://mobbin.com/screens/16cc5d91-2f00-4a92-9777-6dd57a63a6a4), "Ask Linear" (https://mobbin.com/screens/12fc9c16-9010-423f-9ea7-0b5a1567880e), Notion AI's panel (https://mobbin.com/screens/c21465fc-28fd-4c7e-992d-0a7d02c6466d). The composer is their page. Prism's page is the work, so the bar keeps one row.
- Split search and ask controls: Slite's header (https://mobbin.com/screens/fc669f91-90d3-4040-a326-d3be3a7a924a), Apollo (https://mobbin.com/screens/d365d8bf-344d-482d-88fa-d14564386be8), Linear's search page (https://mobbin.com/screens/a2f96ae5-202c-4747-a959-d33d7e5c0f72). Two boxes break the one-box rule.
- Filled send buttons and Square's blue "Search" (https://mobbin.com/sites/sections/c1325057-3418-4190-ab7b-99330f1c7db6), the World Bank's own data portal convention. One solid button per page, so the Enter button is outlined.
- GitHub's header palette (https://mobbin.com/screens/7b69b36d-15c3-43c2-9a67-fe19ddbe98ad) and the palette sheets of Juicebox, Magnific, StackAI and Mintlify. Option C's shape; the owner chose A. Their foot strip is the one thing taken (pick 2). GitHub's field at rest, "Type / to search" with its "/" key cap (https://mobbin.com/screens/51188a32-442e-418c-955b-69a0c4252726), is what Prism's "/" hint already does.
- Qatalog's composer (https://mobbin.com/screens/db6ec0a0-45da-4191-b1ca-30b9c412e1bf) writes "Enter to" in words beside its send button. Prism says it in the Enter button's name and the list's "Enter" hint instead, since the bar has no room for a sentence at 1280 px.
- Raycast and Arc are desktop apps and Mobbin's web library has neither (the Arc search returned Arcade). Their command bars are the palette family above, so nothing is lost.

## For ticket 130, seen on the way

Not picks, since the one-box rule does not reach them, but worth the builder's look:

- Remote's "Add an employee" stepper (https://mobbin.com/screens/5a7aed09-5be9-4ded-a7b6-b3ad8271db98): a vertical list of steps in the left column, done steps ticked, the current step numbered, one line a step, beside the form. Option W2's stacked step tracker in the right column, on `surface` rather than navy, since Prism keeps navy for the bar.
- Stripe's payment page (https://mobbin.com/screens/966b2f85-123b-4302-b505-08eb9b5a9724): a "Timeline" of dated events in the work column and a "Details" column at the right, label over value, with "Last updated" and "Source" as its last rows. That is W2's right column: the plan row's facts with their source line.
- Perplexity's Computer thread (https://mobbin.com/screens/1a53c476-0fb4-4bc4-be69-6e3317849477): a right column of rows, "Sources", "Scheduled", "Usage", each a label, a count and a way in, beside the work. A form for the plan check's "How I checked" panel.

## How I looked

Mobbin's MCP, October 29, 2026, web unless marked. Each query, and what it returned:

| Query | Returned |
|---|---|
| Perplexity answer page with the follow-up bar at the bottom | Perplexity, 8 screens |
| Notion AI prompt bar inside a document | Notion, 8 |
| Linear command menu over the issues list; Linear command palette | Linear, 12 (no palette; the search page, "Ask Linear", the selection toolbar, the issue page) |
| ChatGPT composer at the foot of a conversation | ChatGPT, 8 |
| Claude composer with a file chip | Claude, 8 |
| Dashboard header search with a keyboard shortcut hint | Quicken, Vapi, Juicebox, Gusto, incident.io, GitBook, fal, StackAI |
| AI assistant input with a context chip for the page or file | Sana AI, Voicenotes, WRITER, Langdock, Claude, Qatalog, Dropbox Dash, Apollo |
| Google search home page with a large centered box | Google Gemini, 6 |
| Raycast launcher window | StackAI, Juicebox, Mintlify, Magnific, Slite, Customer.io (no Raycast) |
| Arc browser command bar | Arcade, 5 (no Arc) |
| GitHub command palette from the header search | GitHub, 6 |
| Vertical step progress list in a side panel | Slite, Programa, Wrike, Todoist, Devin, Asana, Workable, Remote |
| Detail page with a sticky right sidebar of properties | Wrike, Plane, Asana, Slack, ClickUp, Bonsai, Linear, Twenty |
| Floating action toolbar at the bottom center of a table | Wrangle, YNAB, Midday, Qatalog, Mercury, ClickUp, LangChain, Aboard |
| Analytics stat card with a small chart and a source or updated line | Visitors, Lovable, Vercel, Whop, Cloudflare, Substack, Navattic, Perplexity |
| Stripe dashboard search with a slash key hint | Stripe, 6 |
| Perplexity adding a follow-up question (flow) | Perplexity, 3 flows |
| Perplexity answer screen with the ask bar (iOS) | Perplexity, 5 |
| Stripe payment detail page with a timeline | Stripe, 5 |
| Public statistics data portal hero with a search box (sections) | Clay, Firecrawl, Square, Antimetal, Serus, mymind |

The sketches follow the proposal's convention: one character at 16 px at 1440 (90 characters) and at 10 px at 390 (39 characters), each edge on its measured column, plus the bar alone at 8 px a character. The measurements of the page come from the proposal's section 1; nothing was measured again today.
