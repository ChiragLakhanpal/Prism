# 06: The app shell, deployed as a Databricks App that acts as the viewer

**What to build:** A reviewer opens Strata's URL and lands in the real app: the navy bar with the World Bank logo and the five tabs, the box band with the data-freshness stamp, and the footer, deployed as a Databricks App in the shared workspace and acting as each viewer. The stamp is read from strata.ops with the viewer's own forwarded token, bound per request and never kept in a module global. Every tab route exists and states its purpose under its title, with an honest empty state that says what will appear there; Home shows its title and purpose until the briefing ticket fills it. Deployment uses fairshare's app deploy script and avoids PLAN.md section 12's traps (a lean requirements file without the agent-framework metapackage, explicit personal-access-token authentication, an async key provider). Each request records viewer, route, view and time in strata.ops for the adoption measures, and sends a trace to Application Insights. Before any app state is written, a timed probe settles PLAN.md section 18's question (Lakebase or strata.ops for app state) and the answer is recorded, as an ADR if Lakebase wins. If day-one test 6 failed, the same build also runs as the Container Apps copy behind Entra sign-in.

Read first: docs/PLAN.md sections 2, 8, 12 and 18; DESIGN.md sections 5, 8, 9 and 10; the blueprint's "Navigation and roles" section and Home wireframe; the day-one results document; docs/agents/areas/app.md.

**Blocked by:** 02 (Design-system foundation); 03 (Credentials, Azure caps and the day-one tests); 04 (The strata catalog and the bundle skeleton)

**Status:** ready-for-agent
**Area:** ops
**Phase:** P1
**Design review:** yes

- [ ] One deploy command builds and deploys the app and prints its URL; the deployed app starts in the App environment with the lean requirements file.
- [ ] Two different workspace users open the app and the data-freshness query runs as each of them, shown by the warehouse's query history or the identity route.
- [ ] A server test sends overlapping requests as two viewers and each response carries its own viewer's identity.
- [ ] A reviewer with an outside email opens the deployed app, or, if day-one test 6 failed, opens the Container Apps copy after Entra sign-in.
- [ ] Every route in PLAN.md section 8 except the deck renders its title, a one-sentence purpose, an empty state and the footer, checked by Playwright; unknown routes show a not-found page in the same frame.
- [ ] Each request writes one usage event to strata.ops, and a request to the deployed app produces a trace in Application Insights.
- [ ] The Lakebase probe's timings and the decision are written down before any app state exists.
- [ ] The navigation, band and footer match DESIGN.md section 5 (top navigation, tabs) and section 8 (footer text), and the blueprint's Home wireframe layout; the logo is the official file, unaltered, at least 24px tall with clear space of half its height (DESIGN.md section 9).
- [ ] Below 768 px a labeled Menu holds the tabs, the layout reflows at 320px, a skip link leads every page, and axe finds no WCAG 2.2 AA violations on any route (DESIGN.md section 10).
