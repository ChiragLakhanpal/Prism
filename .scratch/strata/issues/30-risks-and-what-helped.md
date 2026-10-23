# 30: Procurement risks and what helped, on the package workspace

**What to build:** When someone starts a new package, Strata surfaces the procurement risks that came up again and again for comparable packages, each with what helped and the report that says so: section 3 of the package workspace, "Procurement risks and what helped" (PPSD section 3). A risk-table builder, written as a workflow step so the hindsight test can reuse it with an as-of date, calls get_lessons, find_comparables and search_passages for the package and returns at most five risks ranked by fit and evidence. Each row gives the risk, how often it came up (for example "6 of 31 completion reports", naming the reference class), what helped (a lesson statement) and its sources as citations (the ICR paragraph, the ICR Review, IEG's lesson). The rows pass the six checks like any answer. Each row has a checkbox that selects it for drafting, saved with the package. Clicking a source opens the evidence drawer at that passage with a switcher for the claim's other sources (such as ICR ¶54, ICR Review 10.b and the related award notices) and the info badge "IEG's review restates this lesson" when IEG restated it.

Read first: docs/PLAN.md sections 5 and 6; the blueprint's Package workspace wireframe (section 3) and Evidence drawer wireframe, with their "why" panels; DESIGN.md sections 5 and 7; docs/agents/areas/agent.md.

**Blocked by:** 15 (Plan a package from a sentence); 29 (The knowledge loop: proposed lessons with verified quotes, the review queue and versions)

**Status:** ready-for-agent
**Area:** agent
**Phase:** P2
**Design review:** yes

- [ ] With the scripted agent on the fixture, the rural roads package's table includes "Cost estimates below market rates" with what helped "Base works estimates on market rates to avoid rebidding", citing ICR P130164 ¶54 and the ICR Review, with its count taken from the tool.
- [ ] Called with P130164's approval date as the as-of date, the builder uses no lesson or passage made public after that date.
- [ ] The builder returns at most five risks per package, in the same order for the same tool results.
- [ ] Every count names its reference class and denominator, and no percentage appears below 20 cases.
- [ ] A source click opens the drawer at its passage with the switcher listing the claim's other sources and, for ¶54, the badge "IEG's review restates this lesson", as in the Evidence drawer wireframe.
- [ ] Row selections persist when the package is reopened.
- [ ] The section carries the eyebrow "Planning · PPSD section 3" and follows the Package workspace wireframe and DESIGN.md section 5 (tables, citation markers, info badge); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
