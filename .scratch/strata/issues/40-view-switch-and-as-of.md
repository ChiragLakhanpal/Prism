# 40: The view switch and the as-of date, applied by the server

**What to build:** A World Bank staff member previews honestly what an implementing agency officer or the public would see, and anyone can replay a page as of a past date. The pill at the right of the navy bar ("View: World Bank staff ▾") offers World Bank staff, an implementing agency officer at NWWDA, and the public, and adds the view parameter to the URL. The server applies that view's rules on every route and tool, following the roles table in the blueprint: a preview can only take things away, and checking and exporting are refused in previews (the buttons are disabled with a reason). A banner that never collapses says, for example, "Preview of what an implementing agency officer at NWWDA sees. You are still signed in as yourself." The public view shows only Projects, Lessons and Data, with no signals, time estimates or disagreements on active projects, and contract trails for closed ones. The as-of parameter applies a date to every tool call on the page, with its own banner and "Back to today"; marks on the project timeline offer "See Strata as of this date".

Read first: docs/PLAN.md section 8; ADR 0002; the blueprint's "Navigation and roles" (the roles table and the panel "The view switch"); DESIGN.md sections 5 and 10; docs/agents/areas/app.md.

**Blocked by:** 23 (Disagreements on screen: the project timeline and the disagreement card); 37 (Following, project signals and the mission brief); 38 (Implementing agency drafts: planned dates, a STEP row and private uploads)

**Status:** in-progress
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] A test enumerates every capability per view and proves the implementing agency and public views are subsets of the World Bank staff view.
- [ ] In either preview, the server refuses every check and export route with a reason, and the UI shows those actions disabled with the same reason.
- [ ] In the public view only Projects, Lessons and Data appear; P156634, an active project, shows no signals, time estimates or disagreements; P130164, a closed project, shows its contract trail and timeline.
- [ ] The preview banner reads as in the blueprint, never collapses, is reachable by keyboard, and the view survives navigation through the URL.
- [ ] On P130164 with the as-of date August 26, 2016, the timeline shows nothing after that date, no ICR passage is retrievable, and the scripted answer's tool calls all carry the date; "Back to today" clears it.
- [ ] The pill and banners follow DESIGN.md section 5 (top navigation, Alerts) and the blueprint's "The view switch" panel; states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/40-view-switch-and-as-of, as soon as ticket 38 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
