# Area brief: design

Tickets with `Area: design` go to `design-lead`: the design-system foundation in code, shared components, and the deck's figures.

Read: all of `DESIGN.md`, the blueprint's "Design rationale" and "Screens" sections (`docs/blueprint/strata-blueprint.html`), and `.claude/agents/design-lead.md`.

- DESIGN.md's tokens, type scale, spacing, grid and components live in code in one place, and every screen uses them from there.
- Each component ships with all its states and a Playwright screenshot at 1440, 1024 and 390 px.
- One command captures any route in every state against the mocked API, so design reviews are repeatable.
- Figures use the `diagram-design` skill with the `strata-wb` profile (DESIGN.md section 11), and `hairline-create` for isometric line figures.
- The World Bank logo appears only in the private demo's nav bar, with the footer disclaimer (DESIGN.md sections 8 and 9).
