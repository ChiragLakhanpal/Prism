# 41: Home: the briefing and the Start here strip

**What to build:** Home answers before anyone types. Under the date, a briefing sentence whose counts match the lines below it ("One plan changed this week. One of its activities needs a look and two are worth watching. Two drafts are waiting for you to check."), built from fixed checks with no model, which the block's eyebrow says ("Worth knowing · fixed checks, no model"). Each worth-knowing line is one past-tense sentence with its source and one action ("Open the activity", "See what changed"). The Start here strip gives one example per stage (check a published plan, P156634; plan a package from a sentence; see a project's whole story, P130164; see a lesson change; check the data; see the public view), labeled "Examples Strata set up for you · Remove". A seed command creates the examples reviewers land on (the review notes on the NWWDA plan, the suggested PPSD rows for Kenya rural roads, followed projects, a lesson change), each labeled as an example, real where a source is named. "Waiting for you" lists drafts to check with their progress ("2 of 3 risk owners set") and empties as work is done. Home renders from precomputed records before any model call. The implementing agency and public views get their own Home content from the roles table.

Read first: the blueprint's Home wireframe and its "why" panels, "Navigation and roles" ("The first 60 seconds", roles table) and "A specialist's path"; DESIGN.md sections 5 and 7; docs/agents/areas/app.md.

**Blocked by:** 39 (The Lessons page, with versions and was and now in drafts); 40 (The view switch and the as-of date, applied by the server)

**Status:** ready-for-agent
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] The briefing's counts equal the counts of the lines below it, and Playwright sees no model request while Home renders.
- [ ] For World Bank staff, the first two worth-knowing lines match the Home wireframe's real lines from the NWWDA October 9, 2026 plan, and each "Open the activity" lands on that activity's page.
- [ ] Each of the six Start here links lands where it says; "Remove" hides the strip for that viewer and the choice persists.
- [ ] The seed command creates every example labeled as an example, and running it twice creates no duplicates.
- [ ] "Waiting for you" lists the viewer's drafts to check with their progress counts and shows an empty state once none remain.
- [ ] The implementing agency and public previews show the Home content their column of the roles table describes.
- [ ] Home loads within its budget on a throttled 3G profile.
- [ ] The page follows the Home wireframe and DESIGN.md sections 5 (cards, at most eight per group) and 7 (drafts are "to check", never "to approve"); first-run and quiet-week states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
