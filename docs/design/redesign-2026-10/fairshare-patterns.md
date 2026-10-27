# fairshare, read for Strata's design lead

Written October 26, 2026 from the repo at `../fairshare` (read only; nothing was run). The deployed app needs a sign-in, so everything below comes from the code, the specs under `docs/superpowers/specs/`, the Playwright tests under `web/e2e/` (which pin the exact copy and the exact behaviour), and the two screenshots of the running app that the repo keeps for its deck. Paths are relative to the fairshare root; `file:line` points at the line in that file.

Screenshots copied next to this file:

- `ask-still.png` (2560 by 1440): the Ask screen after "Why is Harbor Business Travel down in September?", with the folded summary strip, the answer with every number underlined, the check line, the breakdown card and the floating bar. A real screenshot of the Databricks App (`docs/diagrams/README.md:111-140` says how it was taken).
- `precall-still.png` (2560 by 1440): Delegate with a pre-call page open beside its list: the sidebar's agent status lines, the compact page list, the page's check line, three titled sections with underlined numbers, and the sticky Approve bar with its consequence sentence.
- `02-answer-checked.png` and `03-delegate.png`: not screenshots but the deck's figures of how an answer is checked and how agents draft and people decide. Kept for the reasoning, not the look.

One name to clear up first: `web/src/components/Notes.tsx` is the presenter's speaker-notes window for the `/present` deck, not a citation component. The thing in fairshare that works like a citation is the checked number (`Num.tsx`) with the fact behind it, the check line, and the "Show the numbers" and "Show the query" panels. Section 3 covers that chain. Strata's plan already names the pieces it means to reuse (`Answer`, `Num`, `Document`, `Term`, `DefinitionWindow`, `Steps`, `Skeleton`, `Table`; strata `docs/PLAN.md:116`), so these notes go past the component names into how each one behaves and why it feels right.

## 0. What fairshare is, in two paragraphs

An airline agency-sales agent over one metric view: one screen that opens on the month's summary (one sentence, five numbers, the three agencies that moved, who is behind pace, and "worth knowing" lines from fixed queries), with a chat bar over it for people who do not write SQL (`README.md:8-21`). Every number in an answer comes from a tool call, a deterministic verifier removes any sentence it cannot match, and the query is one click away. A second mode, Delegate, holds four agents that write pages overnight and wait for a person to approve each one (`README.md:32-42`).

Stack: Vite, React 19, TypeScript, Tailwind v4, Radix (tooltip, popover, dialog, dropdown), Motion for springs; no chart library, no markdown renderer, no state library (`docs/superpowers/specs/2026-10-14-react-app-design.md:44`; `web/package.json:13-23`). Served by FastAPI in the same process as the Python harness, deployed as a Databricks App with the viewer's own identity.

## 1. Information architecture

### Routes and the shell

- Three routes, decided by `location.pathname` in `web/src/App.tsx:46-51`: `/` (the app), `/present` (the deck; `?notes` opens the speaker window), `/brief/:runId` (a shareable approved brief, `BriefPage.tsx`).
- The shell is a sticky sidebar that animates between 256 px and a 56 px icon rail (`App.tsx:259`; the choice is remembered in localStorage, `lib/store.ts:16,43,51`), then a column with the top bar and the mode area (`App.tsx:266-298`).
- Two modes, Ask and Delegate, as a segmented switch under the wordmark (`Sidebar.tsx:25-28, 134-142`); a white pill slides between them with `layoutId` (`Sidebar.tsx:47-49`). The modes trade places along a diagonal: Delegate arrives from the right, Ask from the left (`App.tsx:268-297`; `lib/motion.ts:14-32`).
- The top bar holds the scope (a region select and a month picker) and two quiet facts: "The data runs through September 2026." and "Open the sales dashboard" (`TopBar.tsx:12-23`). The scope is mirrored in the URL (`App.tsx:25-28, 101-107`), so a link carries the month.
- Keyboard: "/" focuses the box, Escape folds the summary when no window is open (`App.tsx:151-163`), Enter sends, the Send button becomes Stop while an answer runs (`FloatingBar.tsx:26-33, 51-52`).

### Ask: what shows first, what waits

| Screen | Shows first | Hidden until asked | Where |
|---|---|---|---|
| First screen (no conversation) | A greeting with the date, a one-sentence headline, five big numbers with a label and a one-line note each, the movers (one sentence per agency with "Why did this happen?"), who is behind pace, "Worth knowing this month" lines, then the floating bar with three suggested questions and the footer "Every number comes from a query on your data. See how this works." | The definition of a KPI word (hover), its check (click), the formula (one click deeper); the Share menu (copy, email, PDF); a signal's rows (click a number); Delegate's waiting pages (one line with a link) | `Summary.tsx:56-116`; `FloatingBar.tsx:35-56`; `App.tsx:249-254` |
| After the first question | The summary folds into one sticky sentence (the strip); the question sits at the top of the view; the answer types out, then its check line and buttons appear; the related "worth knowing" line for that agency; three follow-up chips | The breakdown (open by default only for a "why" answer), the numbers (rows per tool call), the query (SQL, "Copy the query", "Open in Genie"), the "How was that checked?" popover, the "more" menu (copy, email, PDF, CSV) | `App.tsx:276-292`; `SummaryStrip.tsx`; `Conversation.tsx:28-31, 47-58`; `Answer.tsx:63-65, 120-164` |
| The strip | One sentence with the five numbers in bold, "Show the summary" at the right, `aria-expanded` | The full summary unfolds in place above the conversation; Escape folds it; "This month's summary" in the sidebar unfolds it; "Start a new chat" returns to the summary | `SummaryStrip.tsx:11-19`; `App.tsx:216-223, 280-287`; `lib/store.ts:65-71, 81-86` |
| Monday brief (a quick action) | A conversation turn with one check badge per verified sentence, typed out, then the notes, the red box for removed sentences, Approve and send, Edit, Export | A link to share, only after approval | `Brief.tsx:56-104`; `App.tsx:201-214` |
| Definitions | Nothing on its own: the spec rules out a Definitions page and a How-it-works page | A dotted KPI word: hover for one line, click for a 440 px window; "How was that checked?" and "See how this works" open the one "How this app gets an answer" window with the path a question takes and the twenty test questions | `react-app-design.md:13`; `Term.tsx`; `DefinitionWindow.tsx`; `HowItWorks.tsx` |

Loading and the scope: the summary and the signals load separately so the five numbers never wait for the lines (`App.tsx:140-149`); old lines stay until the new month's arrive, and show only when they belong to the month on screen (`Summary.tsx:45-47`); the page dims to 60 percent and is `aria-busy` while a new scope loads (`Summary.tsx:57`).

Filters: one region select (`Select.tsx`, a Radix menu with the chosen item filled blue) and one month picker that opens a year grid, greys out months with no data and says "Months with no data yet are greyed out." (`MonthPicker.tsx:37-48`; `copy.ts:238`). The agency picker for the two quick actions is a dialog with a search box and "No agency matches that." (`AgencyPicker.tsx:24-31`).

### Delegate: three depths

- Depth 0, Overview: one line ("Nothing needs a decision right now." or "Three pages wait for your decision."), chips for the agents that are busy or waiting, then each agent as a section with its one-liner and the pages waiting under it (`Overview.tsx:21-48, 52-64`).
- Depth 1, one agent: the eyebrow "Delegate", the agent's name, what it does and when it runs, the scope control plus "Run now" with a time hint ("About two minutes for four pages."), the stepper that is the explanation when idle and the progress while it runs, then its pages with a checkbox for bulk approval (`AgentView.tsx:94-139`; `Stepper.tsx`).
- Depth 2, one page: the list collapses to a 300 px compact column with a back link, and the page opens beside it as a document (`AgentView.tsx:74-89`; `Document.tsx`). Views slide in from the right going deeper and from the left coming back; the direction comes from the depth (`Delegate.tsx:30-36`; `lib/motion.ts:19-21`).
- The sidebar carries one status line under each agent ("Running, page 1 of 2", "12 pages waiting", "Last run needs nothing from you", "Not run yet", "The last run failed") with a dot whose tone matches (`lib/runs.ts:71-81`; `Sidebar.tsx:41-44, 151-163`), and polls every two seconds while anything runs, so the dot pulses even from Ask (`App.tsx:81-99`).
- The home page says "Two pages wait for your decision in Delegate. Open Delegate" (`Summary.tsx:62-64`; `copy.ts:145-146`), so the two modes point at each other.

### Persistence

Conversations, the collapsed sidebar, the mode and the Delegate position live in localStorage per browser (`lib/store.ts:15-19, 38-46`); a reload turns a pending turn into "The page was reloaded before the answer arrived. Ask again." (`store.ts:40`; `copy.ts:65`). Only approved briefs and decisions go to the server.

## 2. Tooltips

### How they are built

- Radix Tooltip everywhere. One `Tooltip.Provider` wraps the app with `delayDuration={200}` (`App.tsx:257`); `Term` wraps itself in its own provider at 200 ms (`Term.tsx:17`); `Num` sets 150 ms on its root (`Num.tsx:13`); the sidebar rail's `Tip` uses 150 ms (`Sidebar.tsx:32`). All content goes through `Tooltip.Portal`.
- Look: a dark `ink` pill, white 13 px text, `max-w-[300px]` or `[320px]`, `side="bottom" align="start" sideOffset={6}`, rounded 6 px, `shadow-lg` (`Term.tsx:23`; `Num.tsx:19`). The rail's tips open to the right (`Sidebar.tsx:35`). The `menu` class grows the tip from its trigger in 140 ms and fades it out in 100 ms, using Radix's transform-origin variable (`styles.css:69-71`); reduced motion turns the animation off (`styles.css:80-81`).
- Triggers:
  - A KPI word is a real `button` with the `term` class: a dotted grey underline, `cursor: help`, which turns solid blue on hover (`Term.tsx:20`; `styles.css:24, 72-73`). Focus opens it too (Radix), and Escape closes it (`web/e2e/smoke.spec.ts:123`).
  - A checked number is a `span` with `role="button"`, `tabIndex={0}` and an Enter or Space handler, with the `num` class (the same dotted underline). A span and not a button so the period after it wraps with it (`Num.tsx:1-3, 15-16`; `styles.css:54`).
  - Icon buttons in the collapsed rail (`Sidebar.tsx:74-119`).
  - Two places use the native `title` attribute instead: the column heads of the test table (`HowItWorks.tsx:86`) and a judge's reason on a pass/fail mark (`HowItWorks.tsx:27, 92-94`). These never open from the keyboard.

### What a tooltip says, and where

| Kind of fact | Text | Trigger | Files |
|---|---|---|---|
| A KPI word | One plain sentence ("Fair share is AA's share of the scheduled seats on a market, weighted by what the agency sold there.") followed by what a click does: "Click the word for the full definition and how it is checked." or, for pace, which has no SQL twin, "Click the word for the full definition." | the five stat labels on the summary | `Term.tsx:5-13, 24`; `Summary.tsx:30, 49-55`; pinned by `smoke.spec.ts:118-128` |
| A checked number | "{raw} is {column in words} for {row context}. It came from "{query label}", which read {table}. Click to see the rows." (for example: "$46K is the dollars at stake for Harbor Business Travel. It came from "agreement checks", which read ops.agreement_checks. Click to see the rows.") | every underlined number in an answer, a signal line, a Delegate page and its email | `copy.ts:195-196`; `lib/runs.ts:192-201` (the hint), `150-175` (column names in words), `180-188` (the row's context); used by `Answer.tsx:89`, `Signals.tsx:16`, `Document.tsx:45`; pinned by `smoke.spec.ts:214-217` |
| A number quoted from a public page | "{raw} is quoted from source [3], a public page listed under the sources. Click to see it." | prospect research pages | `copy.ts:197`; `runs.ts:194` |
| A rail icon | The full label of the action, or the agent's name and its status line ("Agreement watch: 3 alerts waiting") | the collapsed sidebar | `Sidebar.tsx:74-119` |
| Who you are | "You are signed in as {email}. Every query runs with your permissions." | the initials circle in the rail | `Sidebar.tsx:119`; `copy.ts:21` |

Two things to notice. The hover never carries a number the page does not already show: it names the column, the row and the query, and the click is the way to the rows. And the tooltip's last sentence promises only what the click will deliver (the test at `smoke.spec.ts:118-128` exists to keep that promise).

Caveat for Strata: the KPI one-liners and the plain definitions are string tables in `Term.tsx:5-12` and `DefinitionWindow.tsx:9-17`, not in `copy.ts`. Strata's copy lint would reject that.

## 3. The citation chain: a number, its fact, its rows, its query

### The data shape

- The verifier marks each sentence and each number in it: `{sentence, status: verified | flagged, numbers: [{raw, source, fact}]}` (`harness/verifier.py:129-135`). `source` names where the number matched: a tool call as `tool#k` ("run_sql#1", "ask_metrics#2"; `Answer.tsx:17-20`), a fact block's name on a Delegate page ("numbers", "opportunity"; `harness/agents.py:37-47`), `signals#k` for a home-page line (`lib/signals.ts:32-34`), or `web:...` for a public source. `fact` is `column=value` ("aa_revenue=330114.0") or "source [3]: 12%". A sentence that is a "Source:" or "Could not verify" line carries no numbers and is a `note` (`server/serialize.py:10-12`).
- A removed sentence is kept as `{sentence, reason}` with the reason "no query supports $999K" (`verifier.py:121-123`).
- A tool call carries `{i, tool, args, sql, rows, note, preview (at most 50 rows), genie {conversation_id, message_id, url}, ms}` (`harness/facts.py:60-62`; `web/src/lib/types.ts:30`). A Delegate fact carries `{name, label, sql, source (the table), rows}` (`types.ts:81`), and a public source `{title, url, published, snippet}` (`types.ts:82`).

### How a number attaches to a sentence

`proseParts(text, numbers)` splits a sentence's text around each `raw` number in order (`lib/runs.ts:132-147`), and the renderer turns each number into a `Num` and each string into a span (`Answer.tsx:80, 89`; `Document.tsx:32-52`; `Signals.tsx:16`). Nothing is added to the sentence: no marker, no superscript. The number itself is the citation, with the dotted underline as the only sign.

### What opens, and how

- Hover or focus: the one-sentence hint above (section 2).
- Click, Enter or Space on a number in an answer: the "Show the numbers" panel opens and the page scrolls to the call's rows, which carry the id `call-{source}` (`Answer.tsx:75-78, 138-147`). Each block is headed "Genie returned 12 rows." or "The query returned 1 row." and holds a `Table`.
- Click on a number in a Delegate page: the same, with `fact-{name}` and the heading "The month's numbers: 1 row." (`Document.tsx:101-105, 198-207`; `copy.ts:232`); a `web:` number scrolls to the sources list instead (`Document.tsx:102, 256-272`).
- Click on a number in a "worth knowing" line: the rows open inline under that line, in a bordered card headed "{label}: {n} rows, read from {table}." (`Signals.tsx:19-24`).
- "Show the query": the SQL in a `pre.sql` block (12.5 px mono on the surface colour, `styles.css:34`), headed "Genie wrote this query against the sales metrics view and answered in 14 seconds." or "The agent ran this query.", with "Copy the query" (which turns into a check and "Copied" for 1.5 s, `Feedback.tsx:31-40`) and "Open in Genie" (`Answer.tsx:148-164`; `Document.tsx:208-220`).
- The breakdown for a "why" answer is open by default (`Answer.tsx:65`): a card headed "Here is where the $65K went.", three bars for volume, mix and share from a centre line, the signed amounts at the right, a sentence that says the parts add up and whether fair share moved, and a five-row market table (`Answer.tsx:29-56`).

### The check line, the popover and the red box

- Under every answer: a check icon and one sentence from `trustLine` (`lib/share.ts:53-62`): "All 10 numbers in this answer came from the query results." / "The 3 numbers you can see came from the query results." (when something was removed) / "This answer has no numbers to check." / "Nothing above passed the check." / for a refusal "I did not guess. Everything above is either a query result or a clear statement of what the data does not have." / for a cached answer "Every number in this answer was checked against its query when it was recorded." (`copy.ts:68-76`).
- "How was that checked?" is a dotted-underlined button after it that opens a 420 px popover: a title, two sentences on what the checker does ("compared each of its 10 numbers with the query results, at the same rounding"), the benchmark line, "See how this app gets an answer.", and links to the MLflow trace and the Genie conversation (`Answer.tsx:98-108`).
- "I could not verify {what}." lines follow, each with an info icon (`Answer.tsx:111-113`).
- The red box: a `red-tint` card with "I removed one sentence before showing you this answer." in bold red, then, in muted text, `It said "{sentence}" and {reason}.` for each one (`Answer.tsx:114-119`; `Brief.tsx:81-86`; `Document.tsx:191-196`; `copy.ts:74-76`). When every sentence was removed, the body itself becomes "I could not show this answer. Every sentence in it carried a number that no query returned, so I removed them all. You can open the query to see what came back, or ask again more narrowly." (`copy.ts:76`; `share.ts:49-52`).
- A Delegate page opens with the same line in its own words: "All 39 numbers on this page came from the queries, at the same rounding. Nothing was removed. Hover a number to see what it is and where it came from." (`Document.tsx:187-190`; `copy.ts:191-194`; pinned by `web/e2e/delegate.spec.ts:155`).

### Where the dates are

- A cached answer: "This answer was recorded on {date}, because no model is connected right now." (`copy.ts:102`; `Answer.tsx:93`).
- A definition's check: "A SQL copy of the Power BI measure was checked against this definition on October 12, and all 250 values matched." or "... and 3 values did not match." (`copy.ts:136-137`; `DefinitionWindow.tsx:28-29, 41-43`).
- A page's version: "Version of October 20 at 7:25 AM, for Priya Raman, September 2026." (`lib/runs.ts:29-36, 60-62`; `Document.tsx:170`), and its decision: "Approved by dana@example.com on October 14 at 10:15 PM." (`runs.ts:44-50`; `delegate.spec.ts:170`). Earlier versions are listed with "Open" and the current one with "This version" (`Document.tsx:273-286`); an earlier version opened says so at the top and offers "Open the current version" (`Document.tsx:160-165`).
- A public source: "[1] {title} ({published}) "{snippet}"" with an external-link icon (`Document.tsx:256-272`).
- The test table: "Last measured between October 12 and October 19, 2026." (`HowItWorks.tsx:40-43, 97`).

### The definition window

A click on a KPI word raises a `fairshare:kpi` event that one window at the app root listens for (`Term.tsx:20`; `App.tsx:336-344, 302`). The window (`DefinitionWindow.tsx:30-53`) is 440 px: the display name as the title, the plain definition, a skeleton while the definitions load, the dated check line with a check icon, "Show the formula" that reveals the metric view expression in a `pre.sql` and "The exact wording:" from the definitions table. Definitions are fetched once and kept (`DefinitionWindow.tsx:23-25`).

## 4. Visual polish

### Tokens

Twelve colours and one font stack in Tailwind's `@theme` (`styles.css:3-17`): `ink #36495a` (body), `ink-2 #627a88` (secondary), `line #d0dae0` and `line-2 #e6ebef` (hairlines), `surface #f2f5f8`, `blue #0078d2` (actions, links, checks, gains), `navy #00467f` (wordmark, hover), `red #c30019` (a drop or a removed sentence, nothing else), `tint #e6f1fb` and `tint-line #b9d6ef` (selected, active), `red-tint #fbe9eb`, `grey #9da6ab` (dotted underlines, idle steps). The spec says where each colour may go and nowhere else (`react-app-design.md:16`). Body is white, the sidebar `surface`.

Contrast, measured from the hex values: `ink-2` on white is 4.51:1 and `blue` on white 4.55:1, both just over AA for normal text; `grey` on white is about 2.5:1 and `#C4CCD2` (disabled months, `MonthPicker.tsx:44`) lighter still, so the "hard" tag (`HowItWorks.tsx:90`), the idle stepper labels (`Stepper.tsx:19, 24`), the queued rows (`ItemRows.tsx:71`) and the off-path outline entries (`Notes.tsx:294`) fail AA. The deck's redesign spec saw this and darkened its text colours to `#006cbf` and `#5a7181` to clear 4.5:1 (`docs/superpowers/specs/2026-10-20-deck-redesign-design.md:67-72`; `web/src/deck/ramp.ts:13-16`). White on the `ink` tooltip is about 9:1.

### Type

- Families: "American Sans", "AmericanSans Var", then Inter, Helvetica Neue, Arial (`styles.css:16`); Inter and Geist Mono are loaded from Google Fonts (`web/index.html:9`). Geist Mono is used only by the deck's labels (`deck/ramp.ts:14, 39-41`) and `ui-monospace` for SQL (`styles.css:34`).
- Scale, from the spec (`react-app-design.md:16`) and the CSS: display 34/600 with -0.02em tracking, 1.05 line height and tabular numerals (`.t-display`, `styles.css:26`); title 26/600 -0.02em (`.t-title`, `:27`); label 12/600 uppercase +0.06em in `ink-2` (`.t-label`, `:25`); body 15/1.5 (`:20`). In components: answer and page prose 15.5/1.6 (`Answer.tsx:88`; `Document.tsx:37`), row sentences 14.5 (`Summary.tsx:91`), secondary 13.5, buttons and tooltips 13, hints 12.5, sidebar group labels 11 uppercase (`Sidebar.tsx:180`). Deck: title 40, body 28, note 20, display 56, mono label 12 (`deck/ramp.ts:19-24`).
- Numbers: `tabular-nums` on the display, the table cells, the clock and the step timer; `money()` writes $4.49M, $330K, $1,245 with a true minus sign; `pct()` one decimal; `pts()` "1.2 pts"; `upDown()` "up 0.8%" / "down 16.4%" / "unchanged" (`lib/format.ts:1-33`).

### Spacing and surfaces

- One reading column of 760 px for the summary, the conversation and a page (`App.tsx:250`; `Conversation.tsx:47`; `Document.tsx:159`); 960 for the Delegate overview, 1040 for an agent (`Overview.tsx:21`; `AgentView.tsx:94`); side padding 24 px in the column, 40 px on Delegate pages.
- Blocks are 28 to 36 px apart (`mt-7`, `mt-9`); rows are hairlines: `border-t` on each, `last:border-b`, 13 px of padding above and below (`Summary.tsx:91, 108`; `ItemRows.tsx:46`).
- Radii: 6 px menus and tooltips, 8 px buttons and chips, 10 px cards and panels, 14 px the floating bar, 12 px the user bubble with one 4 px corner (`Conversation.tsx:50`).
- The floating bar is translucent with a blur and a gradient fade above it so content scrolls underneath (`FloatingBar.tsx:35`; `styles.css:29-31`); the strip is translucent with an `edge-fade` under it (`SummaryStrip.tsx:12, 18`); the Approve bar and the bulk-selection bar are sticky at the bottom on `white/95` with a blur (`Document.tsx:292`; `AgentView.tsx:143`). `prefers-reduced-transparency` makes all of them solid white (`styles.css:36-38`).
- Print: `.no-print` hides the chrome and `printElement` marks one element as the `print-target` so "Save as a PDF" prints only the answer (`styles.css:39-51`; `lib/export.ts:29-42`; tested in `smoke.spec.ts:141-154`).

### Tables

`Table.tsx` (18 lines): 13 px text, a semibold `ink-2` header on a `line` border, hairline rows, 6 px cell padding; a column is right-aligned when the first row's value is a number; integers get thousands separators and decimals at most two places, in `tabular-nums`; at most fifty rows; `overflow-x-auto`; empty rows become "The query returned no rows." (`Table.tsx:3, 9, 12`). Column heads are the raw column names (the hint, not the table, puts them in words). The test table in HowItWorks is a grid with `t-label` heads and four mark columns (a blue check, a red cross, a hollow dot) with `aria-label` pass/fail (`HowItWorks.tsx:22-31, 84-96`).

### Charts

No chart library in the app (`react-app-design.md:44`). The one chart is the breakdown: three `div` bars from a centre line, blue for a gain, red for a drop, grey for mix, the signed amount in the same colour at the right, and a sentence under it that states the sum and whether fair share moved (`Answer.tsx:29-55`). Progress is a thin bar that fills left to right (`Stepper.tsx:27-29, 37`). The deck's charts are SVG built in Python with the diagram-design plugin, in the same palette, with "synthetic data" in the band of every figure that prints data (`docs/diagrams/README.md:149-158`).

### Empty states

Sentences, never blank space: "No agency moved more than a point of share this month." (`copy.ts:31`), "There is no decomposition for this month yet." (`:142`), "This agent has not run yet. Press Run now to start it." and "The last run found nothing to flag." (`:173-174`), "Nothing needs a decision right now." (`:153`), "The query returned no rows." (`Table.tsx:3`), "No agency matches that." (`AgencyPicker.tsx:31`), "The test questions are not available in this deployment." (`copy.ts:118`).

### Loading

- Shape, not words: shimmering bars in the layout the content will take, so nothing jumps when it lands; each skeleton is `aria-busy` with a `role="status"` label (`Skeleton.tsx:1-3, 21-58, 61-93`). On the two first-paint screens the Flight Symbol glides in once along the takeoff diagonal (`Skeleton.tsx:12-18`). The test pins that the loading state is a skeleton and not a line of text (`smoke.spec.ts:225-242`).
- While an answer runs, a step list: a pulsing ring for the current step, a check for the finished ones in past tense with their time ("Genie answered in 14 s.", "I checked every number in under a second."), a running seconds counter after two seconds, the step's workings under it (the question Genie was asked, the first line of the SQL in mono, the agency and month), and hints that change with the wait: silent for ten seconds, then "This usually takes 15 to 30 seconds...", at 45 s the warehouse note, at 90 s a way out (`Steps.tsx:26-43`; `lib/steps.ts:10-49`; `copy.ts:52-62`).
- In a list, a "writing" row with two grey bars and a pulsing dot, and queued rows that say "Waiting for its turn." (`ItemRows.tsx:57-79`).

### Motion

One vocabulary in `lib/motion.ts`: a spring with no bounce over 0.35 s for anything that changes position (the fold, the sidebar width, the mode pill), enter in 0.22 s ease-out, leave in 0.12 s ease-in (`motion.ts:7-11`); views slide 12 px in from one side and 6 px up, out the other way (`:25-32`); rows rise 6 px with a stagger of 35 ms up to eight rows (`:35-40`); a stat moves to its new value over 450 ms instead of jumping, and never counts up from zero on first paint (`:49-74`; `Summary.tsx:26`). In CSS: the overlay fades in 180 ms, a dialog pops from 0.98 scale in 200 ms, menus grow from their trigger, a pressed button scales to 0.97, a chevron nudges 2 px on row hover (`styles.css:58-79`). A fresh answer or page types itself out over 0.5 to 2.5 s, numbers appearing whole, and its checks and buttons fade in once it has (`lib/typing.ts:32-36`; `Answer.tsx:79-92`; `Document.tsx:144-155`). The check draws itself after an approval (`Feedback.tsx:10-17`). Every component checks `useReducedMotion` first and the CSS media query stops the rest (`styles.css:80-85`).

### Accessibility details worth copying

The strip is a button with `aria-expanded` (`SummaryStrip.tsx:12`); the mode switch uses `aria-pressed` and a `role="group"` label (`Sidebar.tsx:134-141`); list rows use `aria-current` (`ItemRows.tsx:28`; `Sidebar.tsx:146, 154`); the severity dot is `role="img"` with the word as its label (`ItemRows.tsx:9-13`); skeletons and toasts are `role="status"`; every dialog has a `Title` and a `Description`; checkpoint checks carry an `sr-only` word (`Notes.tsx:205`); a number is reachable by Tab and opens on Enter (`Num.tsx:15-16`); the collapsed rail is a `nav` named "Sidebar, collapsed" (`Sidebar.tsx:72`).

## 5. Copy voice

- One file, `web/src/copy.ts` (280 lines), with the rule on its first line: "Every string a person reads, as full sentences a 10th grader follows. Buttons stay short verb phrases." (`copy.ts:1`; `CLAUDE.md:15`: no jargon, nothing that sounds like a model wrote it, no em dashes). Three helpers keep grammar right: `numberWord` (one to ten in words), `capital`, `minutesWord` ("a minute", "two minutes") (`copy.ts:2-9`), and every count-bearing line is a function that handles one and many (`copy.ts:30-39, 73-76, 153, 180, 191-193`).
- The app says "I" for its own acts and "you" for the reader: "I removed one sentence before showing you this answer.", "I could not verify ...", "I did not guess.", "I am writing the brief from this month's queries.", "I give up on my own after five minutes." (`copy.ts:54, 68, 74, 76`; `App.tsx:204`).
- Every action says its consequence before and after: "Approving records the brief and opens an email draft with the verified text. Nothing is sent until you press send in your mail client." (`copy.ts:100`), "Approving records a Pre-call pack in the CRM stand-in and opens this email in your mail app. Nothing is sent until you press send there." (`:224`), "Rejected. Nothing was sent or recorded." (`:230`), "Change the words, not the numbers. Any number you add is checked against the same facts before it can go out." (`:223`), "Opens in your mail app when you approve. You press send there." (`:217`).
- Buttons are verb phrases that name the thing: "Show the query", "Hide the breakdown", "Open in Genie", "Copy the query", "Approve and send", "Write my Monday brief", "Prepare for an agency call", "Run now", "Start a new chat" (`copy.ts:14-19, 78-92, 162`).
- Honesty words: the CRM is always "the CRM stand-in" (`copy.ts:148, 233`); "Not in the data: whether the agency changed a preferred-carrier setting." (`:218`); a cached answer says it is cached and why (`:102`); a refusal is a first-class answer with its own trust line (`:68`).
- Time and dates in words: "October 14 at 10:15 PM", "September 2026", "Good morning, Chirag. Monday, October 26, 2026" (`lib/runs.ts:29-36`; `lib/format.ts:26-40`).
- Strings that escaped the file (Strata's lint would catch these): the KPI one-liners and definitions (`Term.tsx:5-12`; `DefinitionWindow.tsx:9-17`), "Here is where the $65K went." and the tool names in words (`Answer.tsx:22, 38`), the popover's title and body (`Answer.tsx:102-103`), the path tiles (`HowItWorks.tsx:9-15`), "The query returned no rows." (`Table.tsx:3`), the agency search placeholder and empty line (`AgencyPicker.tsx:24, 31`), "Open the app" and "Loading the brief." (`BriefPage.tsx:18, 20`), the stat labels and notes (`Summary.tsx:50-54`), and the sentences assembled in JSX for the movers and the strip (`Summary.tsx:94`; `SummaryStrip.tsx:14`).

## 6. What made it pleasant, and what not to carry over

### Pleasant, from the code

1. The first screen is already an answer: a sentence, five numbers, three movers, who is behind, and what is worth knowing, with the box over it. A reader has something to react to before typing (`Summary.tsx`; `docs/walkthrough.md:18-29`).
2. Every number explains itself in one sentence on hover and opens its rows on a click, with no marker in the prose. The sentence names the column in plain words, the row, the query and the table (`runs.ts:192-201`).
3. Disclosure is one click deep and in place: the breakdown, the numbers and the query are panels under the answer, not pages; a definition is a window over the word; help is a window from the footer. No Definitions page, no Help page (`react-app-design.md:13`).
4. Context never leaves: the summary folds into a one-line strip that stays sticky above the conversation and unfolds in place (`SummaryStrip.tsx`; `App.tsx:276-292`).
5. The wait is narrated: named steps in past tense with their timings, the step's workings, a seconds counter, and hints that change at 10, 45 and 90 seconds (`Steps.tsx`; `lib/steps.ts`).
6. Nothing unchecked is ever on screen: the typing effect only starts after the verifier has run, and the buttons appear after the text (`lib/typing.ts:1-4`).
7. The check line and the red box make the verifier visible without a score: a count sentence, a popover that explains the check, and the removed sentence quoted with its reason (`Answer.tsx:94-119`).
8. The stepper is the explanation when idle and the progress when running, so a reader learns what an agent does by watching it (`Stepper.tsx`; `runs.ts:85-107`).
9. The Approve bar states the consequence before the act and the decision with who and when after it; the status text swaps with a cross-fade (`Document.tsx:292-307`).
10. The sidebar's one status line per agent, and the home page's "Two pages wait for your decision", make the second mode present without a badge count (`runs.ts:71-81`; `copy.ts:145`).
11. Small truths: the URL carries the scope; months with no data are greyed and the picker says so; "Copy the query" says "Copied" in place; the share link is offered only after approval, with the label "Copy a link (after you approve)" until then (`Brief.tsx:97`; `copy.ts:97-98`).
12. Reduced motion and reduced transparency are honoured in every component and in CSS, and print is designed, not left to the browser.

### Not to carry over

1. Hex colours inline in twelve places (`Summary.tsx:53-54, 92, 94`; `SummaryStrip.tsx:14`; `Answer.tsx:43, 45, 115`; `Brief.tsx:82`; `Document.tsx:192`; `AgentView.tsx:125`; `MonthPicker.tsx:44`). Strata's rule is tokens only; the red box's border `#F0C7CC` has no token at all.
2. Strings outside the copy file (the list in section 5). Strata's lint fails a component that renders text not from `copy.ts`.
3. The `grey` token as text colour: about 2.5:1 on white. Strata's `ink-muted` is 6.69:1; use it or a `neutral` state for idle and off-path items.
4. The typing effect: a page of 39 checked numbers holds its buttons back for up to 2.5 s, and a reader who wants the query waits. Strata's answers are longer and carry citation markers; show them at once, or keep the effect for the first answer only and at a third of the length.
5. The dotted underline as the only sign of a citation. It is quiet, which suits a demo, but Strata's citation marker and source chip already carry the accessible name and the evidence card. Keep fairshare's hover sentence inside Strata's marker, not its underline.
6. Native `title` tooltips on the test table's column heads and marks (`HowItWorks.tsx:27, 86`): mouse only.
7. Custom DOM events for the toast and the definition window (`App.tsx:309-344`; `lib/export.ts:5-7`). They work in a small app; Strata already has a non-modal window rule and would keep a context or a store.
8. `mailto:` as the export (`lib/export.ts:25-28`) and conversations in localStorage (`lib/store.ts`). Strata's drafts and reports live on the server, and its draft bar already says what exporting is not.
9. The hidden "Recent" list in the collapsed rail: the rail's Recent icon only expands the sidebar (`Sidebar.tsx:97`).
10. Colour as the only sign on the breakdown bars (red for a drop, blue for a gain): the signed amount beside each bar saves it, but Strata's rule is that a status is a word, never a colour, so the bar would also need its word.

## 7. Ten patterns Strata could adopt

Each one: the pattern, the fairshare file it comes from, and where in Strata it would go. All ten keep Strata's rules: the number is a tool's, the claim names its record or paragraph, the strings go in `web/src/copy.ts`, colours and spacing are tokens, the control works by keyboard, the copy is plain and has no em dashes.

1. **The number that explains itself.** Hover or focus on a tool number gives one sentence: what the number is in plain words, which row it sits on, which query returned it and which table that query read, then "Click to see the rows." (`web/src/lib/runs.ts:192-201` with `columnWords` at `150-175` and `rowContext` at `180-188`; the template at `web/src/copy.ts:195-196`; the trigger in `web/src/components/Num.tsx:13-19`). In Strata: the tooltip of every tool number in the package page's five sections and on the Home briefing, as the text of Strata's Measure number and of a Num inside a signal line: "{raw} is {the measure's words} for {STEP reference}. It came from {tool} on {record set}. Click to see the records."
2. **Click a number, land on its rows.** The click opens the rows panel and scrolls to the one call that returned the number, by an element id made from the citation's source (`web/src/components/Answer.tsx:75-78, 138-147`; `web/src/components/Document.tsx:101-105, 198-207`). In Strata: a click or Enter on a tool number opens the evidence drawer at that record row (sections 1 and 2 of the package page, the readiness tables), with "Show the query" under it as fairshare's query panel does (`Answer.tsx:148-164`: the SQL, "Copy the query" that says "Copied" in place, and the time it took).
3. **The check line with its "How was that checked?" popover.** One count sentence under every answer, and a dotted button that opens a 420 px popover explaining what the checker compared, at what rounding, and linking the trace (`web/src/components/Answer.tsx:94-110`; the sentence variants in `web/src/lib/share.ts:53-62` and `web/src/copy.ts:68-76`). In Strata: the check line under "In short" on the Home briefing, the package page and a draft gains a "How was that checked?" popover that names the verifier's counts (numbers, quotes, dates as their own clause) and links the run ID.
4. **The removed sentence stays in view, with its reason.** A red-tint box: "I removed one sentence before showing you this answer." in bold, then `It said "{sentence}" and {reason}.` in muted text, and when nothing survives, the first-person body that says so and offers the query (`web/src/components/Answer.tsx:114-119`; `web/src/copy.ts:74-76`; `web/src/lib/share.ts:49-52`). In Strata: the removed box under the check line in the answer panel and on drafts, with the verifier's reason in the same shape ("no record supports US$1.2 million").
5. **The tooltip promises only what the click delivers.** A KPI word's hover ends with "Click the word for the full definition and how it is checked." only when a check exists, and "Click the word for the full definition." when none does; the window then shows the plain definition, the dated check with its count, and "Show the formula" one click deeper (`web/src/components/Term.tsx:5-24`; `web/src/components/DefinitionWindow.tsx:39-49`; the test that keeps the promise, `web/e2e/smoke.spec.ts:118-128`). In Strata: the step labels (rule 26) and the readiness column heads: the hover's last sentence says whether the window will show a check, and the window shows "Measured Oct 23, 2026: 528 of 603 contracts" with "Show the query" one click deeper.
6. **Fold the briefing into a strip.** On the first question the five numbers fold into one sticky sentence with their values in bold, a "Show the summary" toggle with `aria-expanded`, Escape folds, the sidebar's link unfolds in place, and "Start a new chat" returns to the full view (`web/src/components/SummaryStrip.tsx:11-19`; `web/src/App.tsx:216-223, 276-292`; `web/src/lib/store.ts:65-71, 81-86`). In Strata: when the answer panel opens on the Home briefing, the briefing's lead sentence becomes a sticky strip above the panel, so the day's numbers stay one line tall and one press away.
7. **"Worth knowing" lines with one action each, and the box's examples follow them.** Each line is a template sentence from a fixed query, with its checked numbers, a severity dot named by a word, and exactly one verb link (ask, open the agent's page, open the definition); the three chips under the box are built from the lines' questions (`web/src/components/Summary.tsx:103-115`; `web/src/components/Signals.tsx:9-26`; `web/src/lib/types.ts:56-59`; `web/src/lib/signals.ts:7-14`). In Strata: the Home briefing's signal lines (rule 33) each end with one verb link ("Open the project", "Ask why"), and the one box's example sentences follow the day's signals instead of a fixed list.
8. **Loading as shape, waiting as narration.** Skeleton bars in the final layout, marked busy, never a sentence; while an agent runs, a step list in past tense with timings, the step's workings (the first line of the SQL, the scope), a seconds counter after two seconds, and hints that change at 10, 45 and 90 seconds (`web/src/components/Skeleton.tsx:21-58`; `web/src/components/Steps.tsx:26-43`; `web/src/lib/steps.ts:10-49`; `web/src/copy.ts:52-62`). In Strata: the answer panel while the Foundry agent runs ("I am reading the plan.", "The query ran in 3 s.", "I checked every number in under a second.") and the plan check table's skeleton under its real column heads.
9. **The bar that says what the act does, then who did it and when.** A sticky bottom bar whose status sentence names the consequence before the act ("Approving records a note in the CRM stand-in. Nothing else is sent.") and the decision after it ("Approved by {who} on October 14 at 10:15 PM."), the text cross-fading on change, and an edit that adds a number no fact supports refused with the sentence quoted (`web/src/components/Document.tsx:292-307`; `web/src/lib/runs.ts:44-50, 122-126`; `web/src/copy.ts:224-230`; `web/e2e/delegate.spec.ts:189-203`). In Strata: the draft bar on Drafts keeps its fixed sentence and adds the decided line by role ("Checked by their author on March 4, 2026 at 9:12 AM."), and a Lessons review decision reads the same way.
10. **The related line under an answer.** Under an answer that names an agency, the one "worth knowing" line about that agency this month appears with the lead "Worth knowing for September 2026:", found by matching the agency's name in the question and the answer (`web/src/components/Conversation.tsx:32-45`; `web/src/lib/signals.ts:19-29`). In Strata: under an answer asked within a project, the project's one signal line or the readiness line for the source the answer leaned on, so the answer carries its context without another click.

Five smaller ones, if there is room: the scope in the URL with months greyed where there is no data and a sentence that says so (`web/src/App.tsx:25-28, 101-107`; `web/src/components/MonthPicker.tsx:37-48`) for the as-of date in the view switch; the stepper that is both the explanation and the progress (`web/src/components/Stepper.tsx`; `web/src/lib/runs.ts:85-107`) for the nightly job on Data readiness; the one status line per agent in the sidebar (`web/src/lib/runs.ts:71-81`) for the Drafts tab's count; "Copy a link (after you approve)" as a disabled label that explains itself (`web/src/components/Brief.tsx:97`; `web/src/copy.ts:97-98`) for a draft's export before its sources are opened; and the grammar helpers `numberWord` and `minutesWord` (`web/src/copy.ts:2-9`) for Strata's "one to nine in words" rule.
