# 24: All six checks in the verifier, and the must-refuse set

**What to build:** Every answer passes all six checks before anyone sees it, and every request on the refusal list gets a first-person refusal. This ticket adds checks 4 to 6 to the verifier. Check 4: each sentence follows from its passages, judged in one batched call to the drafting model (named in the model file) and skipped for sentences that checks 1 to 3 already prove; its outputs are recorded for the offline gate. Check 5: a claim of kind advice must cite at least one lesson or comparable. Check 6: a claim that rests on an assertion in a disagreement shows both sides; when the agent left the other side out, the verifier attaches the disagreement from get_disagreements, so both sides always reach the screen. Each failing sentence is removed with a reason from the copy file. The check line reports what each check covered and what was not checked ("Not checked: whether these are the right comparables."). The refusal list from PLAN.md section 6 goes into the agent's instructions, each refusal is answered in the first person from the copy file, and each has a scripted case in the offline gate and a must-refuse entry in the benchmark file.

Read first: docs/PLAN.md section 6 (The verifier, Refusals); the blueprint's "How an answer gets checked before anyone sees it" and "What Strata will not do"; DESIGN.md sections 5 (Check line, Removed box) and 7; docs/agents/areas/agent.md.

**Blocked by:** 13 (One cited answer through the Foundry agent and the verifier); 20 (Assertions, disagreements and the evidence ladder)

**Status:** in-progress
**Area:** agent
**Phase:** P2
**Design review:** yes

- [ ] A scripted sentence that its passage does not support is removed with the copy-file reason for check 4; the judge is called once per answer, and not at all when checks 1 to 3 prove every sentence (call counts asserted).
- [ ] A scripted advice sentence that cites neither a lesson nor a comparable is removed with the reason for check 5.
- [ ] A scripted claim resting on ISR 7's rating streams with the ICR ¶78 disagreement attached, both sides present, even though the agent omitted it.
- [ ] Each refusal category in PLAN.md section 6 has a scripted case whose response is a first-person refusal from the copy file and whose tool calls return no restricted data; a scan of every response finds no notice contact details or individual consultant names.
- [ ] Every refusal category appears in the benchmark file as a must-refuse question.
- [ ] The check line reads from verifier counts in the form "Checked: N of N numbers match records; M of M quotes are on their pages. Not checked: whether these are the right comparables." and uses the neutral state (DESIGN.md section 5).
- [ ] The removed box lists every removed sentence with its reason, the first one open by default, as in the blueprint's Package workspace wireframe; refusal and removal states are captured at 1440, 1024 and 390 px and pass axe.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/24-six-checks-and-refusals, as soon as ticket 20 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
