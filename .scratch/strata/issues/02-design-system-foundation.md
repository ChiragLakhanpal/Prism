# 02: Design-system foundation: tokens, type, core components and the copy file

**What to build:** Every later screen is assembled from one set of tokens and components that already follow DESIGN.md, so UI tickets compose rather than invent. This lands the color, state and radius tokens from DESIGN.md section 2 in the Tailwind v4 theme; self-hosted Open Sans and Roboto Mono with the fallback metrics from section 3 and the type scale; space, grid, breakpoints, elevation, scrim and target sizes from section 4; and the components in section 5: the top navigation (navy bar with logo slot, wordmark, five tabs and the view switch pill), the box band (the one box, focused by "/", and the data-freshness stamp), the independent-demo footer, buttons, tabs, cards, tables, alerts, lucide icons, the status badge, the citation marker, the check line, the coverage line and the removed box. fairshare's Answer, Num, Document, Term and DefinitionWindow, Steps, Skeleton and Table are ported and restyled; Num enforces the number rules in DESIGN.md sections 6 and 7. The copy file becomes the only home of user-facing strings, guarded by a copy lint in the gate. A development-only gallery shows every component in its states and is never linked or shipped.

Read first: DESIGN.md sections 1 to 10; GLOSSARY.md; docs/agents/areas/design.md; the blueprint's "Design rationale", "Words" and "Screens" sections.

**Blocked by:** 01 (Repo scaffold with fairshare's rules, hooks, shell and the offline gate)

**Status:** ready-for-agent
**Area:** design
**Phase:** P0
**Design review:** yes

- [ ] A test compares every token in DESIGN.md section 2's theme block with the app theme and finds the same names and values.
- [ ] Fonts load from the app's own bundle with no external font requests, and the fallback face uses the size-adjust and override values in DESIGN.md section 3.
- [ ] The gallery's navigation, box band and footer match the blueprint's Home wireframe and DESIGN.md section 5: a 56px navy bar, a logo slot at least 24px tall with clear space, the tabs Packages, Projects, Lessons, Drafts and Data in that order, the selected tab with a 3px primary underline, and the pill "View: World Bank staff ▾".
- [ ] The footer reads, word for word, the DESIGN.md section 8 disclaimer on every page the gallery renders.
- [ ] Num renders 6 of 12 as "6 of 12" and never as a percentage, renders 31 of 37 as "31 of 37" beside "about 8 in 10", and formats thousands, K, M and B and decimals as DESIGN.md section 6 specifies, checked against literal expected strings.
- [ ] The status badge shows Needs a look, Watch and No signals, each with its own icon shape and its text; the citation marker's accessible name follows "Source 1: Implementation Completion and Results Report, June 30, 2021, paragraph 54"; the check line uses the neutral state, never success green (DESIGN.md section 5).
- [ ] axe finds no WCAG 2.2 AA violations in the gallery; every interactive element shows a 2px focus outline with 2px offset; targets are at least 24 by 24px and buttons 44px tall; motion stops under reduced-motion; the gallery reflows at 320px with no horizontal scroll (DESIGN.md section 10).
- [ ] The gate fails when a copy-file string contains an em dash, an exclamation mark, a DESIGN.md section 7 rule 19 word (for example "flag", "approve", "slippage"), "the Bank" outside a fixed term, or "PP" for Procurement Plan, and passes once it is removed.
- [ ] A lint rule fails the gate when a component renders a user-facing string that is not from the copy file.
- [ ] Every component ships with all its states (default, hover, focus, disabled, loading and, where it applies, empty, error and abstention), and one command captures Playwright screenshots of each at 1440, 1024 and 390 px against the mocked API, so design reviews are repeatable.
- [ ] The gallery route is absent from a production build.
