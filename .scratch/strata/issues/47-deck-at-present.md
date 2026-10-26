# 47: The deck at /present, and How Strata works

**What to build:** The deck tells Strata's story at /present, in World Bank style, and nothing in the app links to it; its URL lives in the proposal and the README. The title slide carries the World Bank logo and the line "built for the World Bank Group's procurement intelligence assessment", each figure carries the logo in one corner, and every slide carries the independent-demo footer. Figures are built with the diagram-design skill using the strata-wb profile, plus at least one isometric line figure from hairline-create. Speaker notes go with every slide. Every number on a slide or in the notes passes the same number check as the proposal. The deck moves by keyboard and each slide meets WCAG 2.2 AA. The Data tab's How Strata works page shows the same figures with plain captions, without linking to the deck. None of fairshare's deck content comes over.

Read first: DESIGN.md sections 6, 8, 9 and 11; the blueprint's "Navigation and roles" (the panel "The deck") and "From an empty repo to a rehearsed demo"; the diagram-design and hairline-create skills; docs/agents/areas/design.md.

**Blocked by:** 46 (The proposal by module, with the rubric map, every number measured)

**Status:** in-progress
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
