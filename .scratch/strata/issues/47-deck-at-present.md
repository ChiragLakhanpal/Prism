# 47: The deck at /present, and How Strata works

**What to build:** The deck tells Strata's story at /present, in World Bank style, and nothing in the app links to it; its URL lives in the proposal and the README. The title slide carries the World Bank logo and the line "built for the World Bank Group's procurement intelligence assessment", each figure carries the logo in one corner, and every slide carries the independent-demo footer. Figures are built with the diagram-design skill using the strata-wb profile, plus at least one isometric line figure from hairline-create. Speaker notes go with every slide. Every number on a slide or in the notes passes the same number check as the proposal. The deck moves by keyboard and each slide meets WCAG 2.2 AA. The Data tab's How Strata works page shows the same figures with plain captions, without linking to the deck. None of fairshare's deck content comes over.

Read first: DESIGN.md sections 6, 8, 9 and 11; the blueprint's "Navigation and roles" (the panel "The deck") and "From an empty repo to a rehearsed demo"; the diagram-design and hairline-create skills; docs/agents/areas/design.md.

**Blocked by:** 46 (The proposal by module, with the rubric map, every number measured)

**Status:** done
**Area:** design
**Phase:** P3
**Design review:** yes

- [ ] /present serves the deck, and a Playwright sweep of every app route finds no link or menu item pointing to it.
- [ ] The title slide shows the official World Bank logo unaltered, at least 24px tall with clear space of half its height (DESIGN.md section 9); every figure has the logo in one corner; every slide carries the DESIGN.md section 8 footer word for word.
- [ ] Figures are built with diagram-design under the strata-wb profile and match DESIGN.md section 11's colors and type; at least one figure comes from hairline-create.
- [ ] The number check passes on every slide and its speaker notes.
- [ ] Arrow keys move between slides, the speaker notes view opens, and axe finds no WCAG 2.2 AA violations on any slide.
- [ ] How Strata works shows the same figures with plain-language captions and no link to the deck.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/47-deck-at-present, as soon as ticket 46 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
- October 26, 2026, merger: merged strata/47-deck-at-present (head 1d3ddadc: three commits of work, b1a67353, 780fc783 and 3902aa38, and two merges of build/strata) into build/strata as merge commit bf9c7214, with history, since the branch's commits hold no key-shaped line. The worktree that built it was `.claude/worktrees/wf_b78fa5cb-ded-47`; I removed it and kept the branch. No dependency file and no gate file changed; I ran `scripts/install` before the merge commit anyway. Nothing conflicted. The merge adds:
  - the deck at `/present` (`web/src/deck/`): 16 slides, the reading view at `/present/page` and the speaker notes window at `/present/notes`
  - the eight figures (sources in `web/figures/`, drawings in `web/src/figures/`): seven from diagram-design under strata-wb, and the hairline core sample on the vendored kernel
  - the deck's data build: `src/strata/proposal/deck.py`, the `python -m strata.proposal deck` command and `web/public/deck/data.json`
  - the live recorder `ops/proposal/record_demo_live.py`, `config/deck.toml`, and the World Bank's light logo (`web/src/assets/world-bank-logo-light.svg`)
  - the figures on How Strata works
  - the deck's tests (`tests/test_deck_data.py`, `tests/test_deck_figures.py`, `tests/record_deck_api.py`, `web/tests/deck.spec.ts`, and the route sweep in `web/tests/sweep.spec.ts`), with DESIGN.md's additions
  - The gate: the merge commit's gate passed in 126.4 seconds. By hand on build/strata after the merge, it passed in 133.3 seconds at 09:33 PDT, under the 150-second limit. The slowest lanes were python (98.0 seconds) and web-2's Playwright half (84.0 seconds).
  - Notes that passed, both at 1d3ddadc. The code review approved round 2 with no blocking finding and six follow-ups (`.notes/47-review-r2.md`; round 1 is `.notes/47-review.md`). Design review is off until every functional ticket has merged, under the user's rule of October 25, 2026.
  - Verify (`.notes/47-verify-r2.md`): pass on all six criteria on the fixture. The real numbers and the deployed App are parked, and the visual parts are deferred. The verifier's gate run passed in 127.3 seconds; deck.spec and sweep.spec passed 13 tests in 7.0 seconds.
    - Criterion 1: `/present` serves 16 slides outside the app's frame. The server answers 200 for `/present`, `/present/3`, `/present/page` and `/present/notes`. The sweep opens all 28 page kinds in `web/src/routes.ts` and finds no link to the deck, and a planted probe showed it catches four forms of deck link.
    - Criterion 2: the light logo's SHA-256 equals the file on data.worldbank.org. On the title slide it is at least 24 px tall, with clear space of half its height. Each of the 10 figure frames carries one logo in its credit row, and every slide's footer matches DESIGN.md section 8 word for word.
    - Criterion 3: the skill's export of each of the 7 sources equals the committed SVG, and `self_check.py --offline` passes. The colours are the section 11 palette plus `#ffffff`. The hairline figure passes the skill's build and validate.
    - Criterion 4: the proposal's number check finds no problem over all 16 slides, their notes and presentation mode, for the fixture, the committed file and the fixture with the estimate. Each of 7 planted numbers failed the check. These match their rows: 2,198 passages, 39 documents, 625 of 650 pages, 239 of 603, 49 comparables, 45 of 52 and 6 of 6.
    - Criterion 5: the arrow keys, Page Up, Home and End move the deck, and the notes window follows it. Axe found no WCAG 2.2 AA violation on any slide, in all three datasets, with the table twins open and in the reading view.
    - Criterion 6: How Strata works draws the same SVG markup as the deck, with first-person captions and text versions, no logo and no link to the deck.
  - Workspace results: none ran. Every key is set, but the second session runs every workspace step from a snapshot of the commit, so the merger ran none. Three blocks are parked in `docs/workspace-catchup.md` for a snapshot of bf9c7214 or later:
    - Step 1: run `uv run python -m strata.proposal deck` in the same commit that brings ticket 46's `docs/proposal/snapshot.json`. Proof: `test_the_committed_deck_data_is_built_from_the_committed_snapshot` and the gate pass.
    - Step 2: run `uv run --frozen python ops/proposal/record_demo_live.py --env-file .env`, then the deck command again, and commit `docs/proposal/demo-package.json` and `web/public/deck/data.json` together. Proof: the gate passes.
    - Step 3: deploy the App with `--keep-secrets`, then arrow through all 16 slides at `/present`. Proof: `/present/8` draws the demo package's range chart, and How Strata works has no deck link.
    - The builder's third note, which inputs mean rebuilding both deck files, is not a workspace step. It went to ticket 49, for the change drill notes.
  - Decisions parked for the user:
    - The design brief's decisions are listed under "Ticket 47" in `.notes/parked-decisions.md`. The review and verify notes park no new ones.
    - Kept as built: the light logo's text alternative reads "World Bank Group logo", as the artwork does (DESIGN.md section 9).
    - Only you can fill this one: `config/deck.toml`'s `presenter_name` and `presentation_date` are empty. Fill both before the panel, then run `uv run python -m strata.proposal deck` and `uv run --frozen python tests/record_deck_api.py`.

  **Deferred to the design pass**

  - Captures at widths other than 1440, print, and hover and focus captures.
  - The title-fits-two-lines test.
  - Slide 15's source line runs into the footer rule (review round 1, item 10).
  - The `#ffffff` node fills in the figures, which DESIGN.md section 11's palette does not list.
  - The arrow keys move the slide while a definition window is open (verify finding 3).
  - Visual polish in general.

  - Follow-ups for the PM, not blocking:
    1. Most urgent, verify finding 1: `web/tests/deck.spec.ts:39` calls `spawnSync` on the number check with its input piped in and no `timeout`. The verifier measured a hang in about 5 of 820 runs on this computer. `spawnSync` blocks the worker, so a hang can stall the gate until the 150-second limit, in about 1 to 3 gates of every 100. The fix is in test code only: write the input to a file, pass it as `stdio: [fd, "pipe", "pipe"]`, and add `timeout: 30_000`. An orphaned worker from this hang was still running at 09:35 PDT (pid 2765, with Python child pid 2823). I left it, as the verifier did.
    2. Verify finding 2: the number check skips a chart's whole `<figure data-source-key>`, so a number typed into a chart's own words would pass.
    3. Review round 2's six follow-ups, each with its exact fix in `.notes/47-review-r2.md`:
       - If the deck's chunk fails to load, the page stays blank (the verifier's probe G confirmed it).
       - The award gap check misses a stray row next to the gap, and a renamed gap raises a bare StopIteration.
       - Slide 13's "five" reads today's config, not the hindsight run's.
       - Slide 8 says "found only 0 comparable packages" when the tool abstained before counting.
       - A source-level guard is needed for the states that open only inside the app.
       - How Strata works still puts the hairline kernel and the deck's copy in the 1.7 MB first bundle.
  - Ticket 49 waited on 45, 47 and 48. 45 and 48 are done, so it starts from this merge: its Status is now in-progress, with the orchestrator's dispatch comment. The P3 phase gate, which waited on 46 and 47, can run now.
- October 27, 2026, orchestrator (19:22 PDT): step 2 ran from 050365f9's snapshot (02:07 UTC, exit 0): the demo package's comparables and estimate are recorded and the deck's data rebuilt (the catch-up block "Ticket 47, step 2 of 3 ran").
