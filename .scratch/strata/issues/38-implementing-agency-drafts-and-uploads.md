# 38: Implementing agency drafts: planned dates, a STEP row and private uploads

**What to build:** An implementing agency's procurement officer checks their plan before submitting it, on a private upload of their STEP export or on the latest published version, and leaves with a planned date for every STEP step, PPSD risk rows and a STEP row they can paste. First, settle PLAN.md section 18's open question: whether STEP exports a plan to Excel, and in what layout; if it cannot be confirmed, accept the Procurement Plan template's columns and record that. Uploads are Official Use Only: stored in strata.ops with the uploader's team from the roles file, filtered by team on every route and tool, never added to the shared search index, and never shown to anyone else; the screen says so. The agency's writers produce PPSD risk rows (the same Short Form and Long Form rules) and a planned date for every STEP step from the delay model. The STEP row exports as CSV in STEP's own columns with planned dates filled and everything else (references, actual dates, ratings) left to the officer and STEP. Shared copy says "implementing agency", never PIU.

Read first: docs/PLAN.md sections 1, 4, 6 and 18; the blueprint's "Where Strata enters the work" and "Navigation and roles" (the implementing agency column); DESIGN.md sections 5 and 7; docs/agents/areas/app.md.

**Blocked by:** 27 (A planned date for each STEP step, from the delay model); 36 (Suggested PPSD risk rows and the Project Paper summary, exported to Word)

**Status:** in-progress
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] The answer to the STEP export question is recorded, with a parsed sample if one was available or the fallback format if not.
- [ ] An officer in team A uploads the fixture plan and gets its check; a viewer in team B gets no rows from any route or tool, and a question about the upload is refused as a must-refuse case.
- [ ] A test proves no upload text ever reaches the shared search index.
- [ ] Every activity in the upload gets a planned date for each STEP step from the delay model, each naming its comparables count or abstaining below 20.
- [ ] The STEP row CSV has exactly STEP's columns, with planned dates filled and references, actual dates and ratings empty.
- [ ] The agency's PPSD rows follow the Short Form and Long Form rules and carry footnotes.
- [ ] The upload screen shows "Official Use Only · visible to your team" (from the copy file); screens follow the blueprint's implementing agency column and DESIGN.md sections 5 and 7; states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/38-implementing-agency-drafts-and-uploads, as soon as ticket 36 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
