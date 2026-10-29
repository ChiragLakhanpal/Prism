# 130: The package workspace uses its right column, and the plan check fills the space beside its finding

**What to build:** On October 29, 2026 the owner said the Packages content was "squished to the left". The design lead measured the local copy (`docs/design/notes-2026-10-29/ask-bar-and-width-proposal.md`, read first): the Packages list already spans the twelve columns; the squeezed page is the package workspace, whose work takes 743 of the 1,296 px (columns 1 to 7) while the 553 px beside it stay empty on 87 percent of the page's height, and the plan check, with an empty 637 by 240 px block beside its finding. Build the lead's Option W2: the package workspace keeps two columns, and the right column holds the plan row's facts (the reference, the method, the estimate and the plan date) and then "Where the steps stand" as a vertical list that stays in view under the top bar while the person reads the zones (ticket 115's row becomes a list at 1280 and 1440 px, as the lead recommends; the row stays at 1024 px where the page is one column); the drawer still opens in that column's place so nothing else moves. On the plan check, a "How I checked" panel fills the empty block beside the finding: the method in one sentence, the comparison with the previous plan version, and the baseline, each with its source. Build after ticket 127 lands (the box on the grid comes first, or the centred box reaches 109 px into the right column at 1280 px). Prove it with the package and plan check specs at 1440, 1280, 1024 and 390 px, the steps tracker's specs updated for the list, the drawer's placement unchanged, axe clean; keep the gate under 150 seconds.

Read first: `docs/design/notes-2026-10-29/ask-bar-and-width-proposal.md` (Option W2's sketches and files), `web/src/pages/Package*` and the task zones (ticket 101), `web/src/components/StepTracker*` (ticket 115), the plan check page (ticket 100), `DESIGN.md`'s layout rows.

**Blocked by:** 127 (the box on the grid first), and the Mobbin pass before it

**Status:** ready
**Area:** web
**Phase:** P4
**Design review:** no

- [ ] On the package workspace at 1440 and 1280 px, the right column holds the plan row's facts and the step tracker as a vertical list that stays in view under the top bar; at 1024 px and below the page is one column with the row as before (specs measure both).
- [ ] The drawer opens in the right column's place and nothing else moves (a spec measures the zones before and after), and ticket 115's state rules hold in the list.
- [ ] On the plan check, the "How I checked" panel beside the finding shows the method, the comparison with the previous version and the baseline, each with its source, at 1440 and 1280 px; axe is clean at the four widths.

## Comments

- October 29, 2026, orchestrator: parked at 14:05 PDT at the owner's word ("parking the design related stuff so that the lead can use mobbin's mcp for inspo and the build"); the lead's proposal moved to docs/design/notes-2026-10-29/ so a builder in a worktree can read it.

- October 29, 2026, orchestrator: opened at 13:30 PDT from the design lead's proposal of the same day.
