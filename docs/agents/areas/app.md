# Area brief: app

Tickets with `Area: app` build the FastAPI service, the React app, the Databricks App deployment, the exports and the deck route.

Read: `docs/PLAN.md` section 8, all of `DESIGN.md`, and the blueprint's "Navigation and roles" and "Screens" sections (`docs/blueprint/strata-blueprint.html`), especially your screen's wireframe and its three "why" panels.

- DESIGN.md is the design system: its tokens, type scale, components and writing rules. A deviation needs a line in DESIGN.md first.
- Build the screen the blueprint draws. When you depart from the wireframe, say why in your report.
- Every number explains itself on hover and opens its rows; every citation opens the evidence drawer at its passage.
- Design every state: loading (skeletons sized to the content), empty, error, abstention and populated.
- The viewer's forwarded token is bound per request, and the view switch's previews can only take things away.
- `/present` serves the deck, and nothing in the app links to it.
- Ports come from environment variables with free-port defaults, so several worktrees can run the app side by side during reviews.
- Playwright covers each screen against a mocked API. `design-lead` and `design-critic` review every user-visible change.
