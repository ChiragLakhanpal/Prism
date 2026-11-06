# Good morning: the shell redesign, round 3

Written October 27, 2026 at 2:02 AM PDT, after the second critic's review. Open these in order. All are in `<scratchpad>/redesign/design/`.

1. `prototype.html` in a browser. Press "Prototype controls" at the bottom right. Its eight page links walk the demo: Home, Packages, the plan check, the package, All projects, Lessons, Drafts, a draft. Four switches:
   - **Rail at rest**: By width (the plan: labels from 1440 px, icons below), Labels (always open), Icons (always a rail). Try it at your laptop's width.
   - **Evidence drawer**: Beside the page (the plan) or Over the page. Open a row's records on the plan check to see the difference.
   - **Data**: Real (the test fixture), Longest (the longest real strings), Empty or few (the empty states; on the package page, seven comparables, where I hold back the range; on the plan check, no signals), Error (each page's failed load).
   - **View**: Staff, Agency officer, Public. The view switch in the navy bar opens the same choice. Home is drawn for all three; All projects and the plan check for the public too.
   - Things to try first, the three the second critic said must land: hover "49", then "2", on the package page, and see two different sentences; press "2" and see the two packages it counts, right under the count line, with "Show all 49"; on a draft, press "How was that checked?" and read why its counts differ from the check line.
   - Then: hover a dot on the chart; press "Mark as checked" on a draft; on Home, "Show an answer asked from Home"; the package page with Data on Empty or few.
2. `plan.md`, section 0.1 (each of the second critic's points and what I changed), then 6 (why World Bank fit outranks a louder look), 8.0 (what each page shows, to whom) and 8.5 (empty, few and error).
3. `open.md`, the calls that are yours, each with my pick.
4. `tickets.md` (16 tickets in build order, each with the gate seconds it adds) and `design-md.md` (the DESIGN.md text, by ticket).

The plan in ten lines:

1. One bold move: each page's finding in Open Sans Light at 28 px, the largest type on the page; everything else is quiet.
2. Palette: no new color. Navy only in the bar; the deck's five fixed colors are the app's own.
3. Type: finding 28 light, h1 24, h2 18/600, body 16, caption 13; capitals only inside charts; a status sentence takes lead, not the finding style.
4. Shell: a navy bar with the box; a grey sidebar, open from 1440 px and a rail below; the stamp at its foot.
5. Panels: a white panel only around open work; closed or one-sentence zones are rows on the grey.
6. Each page shows the next step first, for staff, an officer or the public; the rest is one click away on the thing it explains (plan 8.0).
7. Motion: tooltips, windows and the drawer enter in 160 ms; a press eases in and snaps back; nothing else moves; none under reduced motion.
8. From fairshare: every number says what it is, where it came from and what a press opens; a press lands on its rows; "How was that checked?".
9. Folds in polish items from tickets 58, 59, 60 and 62 (plan section 14); How Prism works leaves Data.
10. Yours: the rail at rest, the drawer's placement, when the tickets run, the logo, dark theme (no).

The three decisions to make:

1. **The rail at rest** (open.md item 2): I would keep By width.
2. **The drawer's placement** (open.md item 3): I would keep it beside the page; over the page covers the plan check's "Draft review notes".
3. **When the tickets run** (open.md item 6): I would start "Tokens, fonts and lint" now (it edits no page file and nothing in the deck) and the rest, the class sweep first, after the functional tickets merge. The wave has about 4 seconds of gate time to spend.

What the night built from this plan:

(The orchestrator fills this in.)
