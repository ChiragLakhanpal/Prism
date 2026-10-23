# 33: Genie, the benchmark, Foundry evaluations and the full gate

**What to build:** Structured questions go through a Genie space defined in code, and one command runs the full gate: the offline gate, the Genie benchmark, the benchmark through the live answer contract, and Foundry evaluations. The Genie space is built from code from the gold metric views, with trusted SQL and its own benchmark questions, adapted from fairshare's Genie setup. The ask_genie tool (one registry entry) calls the conversation API as the viewer and returns rows with evidence ids, warming a cold warehouse before it gives up. The benchmark file holds four kinds of question (SQL with ground-truth SQL, documents with expected citations, estimates with expected ranges or abstentions, and the must-refuse set), run by fairshare's benchmark runner adapted to them. Foundry evaluations (groundedness, relevance, task adherence and tool use) run after an Entra sign-in. Results go to strata.ops evaluation results with run ids, and each target that is missed is named with its gap, as P2's exit criterion asks.

Read first: docs/PLAN.md sections 6, 10 and 12 (Known traps); ADRs 0001 and 0003; CLAUDE.md rule 4; docs/agents/areas/agent.md.

**Blocked by:** 17 (Every structured source, for every country, kept as published); 24 (All six checks in the verifier, and the must-refuse set)

**Status:** ready-for-agent
**Area:** agent
**Phase:** P2
**Design review:** no

- [ ] The Genie space deploys from code, a second deploy reports no change, and its benchmark pass rate is recorded in strata.ops.
- [ ] ask_genie returns rows with evidence ids as the viewer, and its first call after the warehouse has gone idle succeeds within the timeout.
- [ ] The benchmark file covers every must-refuse category in PLAN.md section 6 and at least ten questions of each other kind.
- [ ] A test fails when a registry tool has no benchmark question (CLAUDE.md rule 4).
- [ ] The full gate command runs end to end, writes results with run ids, and fails naming the gap when a target is missed.
- [ ] Foundry evaluation scores for groundedness, relevance, task adherence and tool use are stored per run.
- [ ] A question added to the benchmark file runs in the next full gate with no other change.
