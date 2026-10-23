# 13: One cited answer through the Foundry agent and the verifier

**What to build:** A question goes in over HTTP and comes back as a cited answer that passed the verifier, through the Foundry agent with every tool run in the app as the viewer (ADR 0003). The orchestrator is a Foundry prompt agent whose instructions are versioned in the repo and synced the way fairshare's agent sync does it, with its tool list generated from the registry and content filters and Prompt Shields on the question and on tool results. The answer loop runs over the Responses API: the question and its scope (scope chip, as-of date, view, language) go to the agent; its tool calls run through the registry as the viewer; results go back; at most three rounds; then the agent returns claims as JSON (one sentence each, with its kind, evidence ids, the numbers and dates it states, and any quote with its passage id). This ticket builds verifier checks 1 to 3 (every number and date matches a returned row or sits inside a quote from a cited passage that is not a table summary; every cited id came back this turn; every quote is word for word on the cited page), removes failing sentences with their reasons, and streams the answer contract's events (steps, sentences with evidence ids, the evidence, check counts, removed sentences, and a final event with the run id and both trace ids). Every run is logged in strata.ops. Offline, a scripted agent replays recorded outputs; a recording command captures them from the live agent.

Read first: docs/PLAN.md section 6; ADRs 0001 and 0003; the blueprint's "How an answer gets checked before anyone sees it"; the spec's Seams (seam 3) and "The agent and the answer contract"; docs/agents/areas/agent.md.

**Blocked by:** 11 (The first 20 documents read into numbered passages and made searchable)

**Status:** ready-for-agent
**Area:** agent
**Phase:** P1
**Design review:** no

- [ ] With the scripted agent on the fixture, "Why were works contracts in P130164 advertised again?" streams steps, then an answer whose sentence cites ICR P130164 ¶54 and states "108 of 328", with check counts showing every number matched and every quote found on its page.
- [ ] A scripted case in which the model says bids were usually opened within 45 days has that sentence removed with the copy-file reason "No record supports this number.", and the check counts reflect the removal.
- [ ] A scripted case citing an id that did not come back this turn, and one with a misquote, each have the sentence removed with its reason.
- [ ] A scripted case that asks for a fourth tool round gets no more tool results and ends with an answer built on the first three rounds' evidence.
- [ ] After the sync command runs, a second run reports no difference between the repo's instructions and the Foundry agent's.
- [ ] On the workspace, the same question through the live Foundry agent returns a cited answer that passes checks 1 to 3; the run is logged in strata.ops with an Application Insights trace id that opens in Application Insights.
- [ ] Five real passages containing rule-like sentences go through the live agent as tool results without a Prompt Shields refusal.
- [ ] The recording command re-records every scripted case, and the result shows as a reviewable diff.

## Comments

- October 23, 2026, orchestrator: ticket 09 landed in build/strata (merge commit f9cc969) with choices that shape the agent; its done comment lists all nine. Three matter here. First, check_plan's `version_not_public` abstention names the later disclosure date, which is a date after the as-of date; keep it for page routes, but the agent must never see or state a date after its as-of, so strip it from what the agent gets. Second, the registry accepts an as-of date after today and then states events that have not happened; the user has not picked between answering as of today and refusing, so leave `registry.call` as it is and make the agent pass an as-of date no later than today. Third, a data note code that `reasons` in `config/tools.toml` lacks gives HTTP 500 at run time, not a gate failure; when you add a tool, a reason or an abstention, add its code and its copy sentence in the same change, and add the gate check if it is cheap.
