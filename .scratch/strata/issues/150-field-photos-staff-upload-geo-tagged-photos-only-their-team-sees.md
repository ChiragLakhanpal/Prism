# 150: Field photos: World Bank staff upload geo-tagged photos that only their team sees, and the brief cites them

**What to build:** The one source of the deep research the public cannot give: photos World Bank staff take on a mission. On the Deep research tab (ticket 149), a staff viewer can add a JPEG or PNG (up to 10 MB, up to 20 per project); the server reads the photo's EXIF date and GPS position (add `Pillow` as a dependency, pinned), stores the file and its fields through the uploads store's path (`src/strata/uploads/store.py`; the file itself kept in the app state's volume on the workspace and beside the local DuckDB file here, never in the repo), and the access rule (`src/strata/server/access.py`) shows it only to the uploader's team, labelled "Official Use Only · visible to your team", with "Uploading never submits anything" beside the control (DESIGN.md rule 39). A stored photo becomes an item of ticket 147's shape with kind `field_photo`, `public_from` null and `team` set, so a run by a viewer of that team cites it in the brief ("A photo taken at Baricho on <date> by a World Bank staff member shows ...", where the writer may describe only what the uploader wrote in the caption field, never the pixels); a run by anyone else never sees it. A photo without GPS is kept with `location` null and the brief says so.

Tests on seams 2 and 3: a photo with EXIF GPS and date yields an item with location and `observed`; one without yields `location` null; a viewer outside the team gets no item from `research_evidence` and 403 from the photo route; the file never lands in the repo; the size and count limits refuse politely. Keep the gate under 150 seconds (one small fixture photo with EXIF made by the test).

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD after 147 and 149 have merged, or against their interfaces with mocks if started earlier. Write every new sentence with the name Prism. No design review.

Read first: `src/strata/uploads/store.py`, `src/strata/server/uploads.py`, `src/strata/server/access.py`, `config/uploads.toml`, ticket 147's item shape, ticket 149's tab.

**Blocked by:** 147, 149

**Status:** done
**Area:** app
**Phase:** P5
**Design review:** no

- [ ] A staff viewer adds a geo-tagged photo on the Deep research tab and sees it listed with its date and place; the file is stored outside the repo (Playwright and route tests).
- [ ] The photo is an item of kind `field_photo` for the uploader's team only; another viewer's run never sees it and the photo route answers 403 (tests).
- [ ] The brief cites the photo by its caption and date, never by what the pixels show (test on a recorded writer answer).
- [ ] The gate passes under 150 seconds on the worktree.

## Comments

- November 5, 2026, orchestrator: opened at 18:02 PST as the stretch ticket of the night; built only when 147 to 149 have merged with time to spare.
- November 5, 2026, merger: merged on the integrated branch `worktree-agent-adfa26ba0a813e559` (head c492ce9d, where an integrator joined tickets 152, 155, 150, 154 and the four research branches of ticket 153, each gated on commit) into build/strata as merge commit 01f76c67, with history, because the history scan found no keys in the branch's commits. The gate on the merge commit passed in 168.3 seconds, under tonight's 180-second limit; the integrator's final gate on the branch passed in 154.5 seconds. The secret scan on build/strata after the merge found no keys. The worktree that built it, `.claude/worktrees/agent-adfa26ba0a813e559`, is removed after this commit. The branch stays.
  - Evidence: tonight's rule from the user (November 5, 18:05 PST) is essentials only, with no review or verify round, so the integrator's report is the evidence. Field photos: each photo item carries its team, the brief carries `team_key`, and the photos live in the table `strata.ops.field_photos` and the volume of the same name. `web/tests/research.spec.ts` and `web/tests/field-photos.spec.ts` ran 15 tests and passed; the brief, photo, tools and benchmark tests ran 106 and passed. The gate took 168.3 seconds on the merge, over the 150 seconds the last criterion names and under tonight's 180-second limit.
  - Workspace results: none run tonight. Ticket 151's agent runs the six steps under "Tickets 150, 152, 153, 154 and 155, the second deploy of the Prism night" in `docs/workspace-catchup.md`, steps 1 and 2 for the photo table, the brief's new column, the volume and their grants.
