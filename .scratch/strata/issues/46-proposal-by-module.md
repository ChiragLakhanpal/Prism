# 46: The proposal by module, with the rubric map, every number measured

**What to build:** The panel reads a technical proposal written by the assessment's four modules, in which every number links to a result the build measured. Module 1 covers ingestion, the knowledge model and document reading; Module 2 the estimates and agentic retrieval; Module 3 the verifier, guardrails and the evidence ladder; Module 4 the three loops, KPIs and the phased rollout (World Bank staff in two countries, then implementing agencies, then a public read-only view). A rubric map ties each section to its dimension and points. Every number cites its source (a strata.ops evaluation result, a data readiness measure, a benchmark run, a backtest, the hindsight test or a query), and a number check fails if any number lacks one, dates, years and section numbers excepted. The proposal also carries cost caps and actual spend, the change drill, the short list of what is designed but not built (matching the app's labels), Neo4j as the production option, the deck's URL and the repo. The README gains the deck URL and how to run Strata. Figures come from the design lead, built with the diagram-design skill and the strata-wb profile. Every draft goes through the unslop skill.

Read first: docs/assessment.md; docs/PLAN.md sections 13 and 17; DESIGN.md sections 7, 8 and 11; GLOSSARY.md; the blueprint's "Where Strata earns each point"; docs/agents/areas/docs.md.

**Blocked by:** 45 (All three dashboard pages and the KPIs)

**Status:** in-progress
**Area:** docs
**Phase:** P3
**Design review:** yes

- [ ] The proposal's sections follow Modules 1 to 4 of the assessment, and its rubric map lists all four dimensions with their points and the sections that earn them, as in the blueprint's "Where Strata earns each point".
- [ ] The number check passes on the proposal, and fails when an unlinked number is planted in a copy.
- [ ] The "designed, not built" list matches every such label in the app.
- [ ] The proposal and the README both give the deck's URL, and the README explains how to run Strata and the demo-ready command.
- [ ] The copy lint run over the proposal finds no em dash, no DESIGN.md section 7 rule 19 word, no "the Bank" outside a fixed term and no "PP" for Procurement Plan, and the unslop pass is recorded.
- [ ] Dataset attributions and any quoted Open Knowledge Repository work follow DESIGN.md section 8 word for word.
- [ ] Figures use the strata-wb profile's colors and type (DESIGN.md section 11) and DESIGN.md section 6's chart rules.

## Comments

- October 25, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/46-proposal-by-module, as soon as ticket 45 landed. All ten keys are set, but the Free Edition warehouse's daily limit holds every live step, so each one is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
