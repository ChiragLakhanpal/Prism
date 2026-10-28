# 118: The judge and the agent retry a rate-limited model call before a sentence is removed or an answer fails

**What to build:** On October 28, 2026 at 05:54 UTC the demo-ready command's third smoke run in a row lost its one sentence with the reason `judge_unavailable`: the verifier's check-4 judge asked Azure OpenAI and got `429 Your requests to gpt-5.4 for gpt-5.4 in eastus have exceeded token rate limit` (code rate_limit_exceeded), while the two runs before it had passed every check. Since the agent role moved to gpt-5.4 the same evening (e8cd0021), the agent and the judge share one deployment with a 30,000 tokens-per-minute cap (the day-one caps the owner chose), so a long answer and its judging can cross the cap inside one minute. Today the judge gives up on the first 429 and the verifier removes every sentence it had to judge (rule 1 keeps unchecked sentences off the screen, which stays), and the agent's Foundry calls turn a 429 into `agent_unavailable` the same way. Make both retry a 429 (and a 503) before giving up: `src/strata/agent/judge.py` and the judge's client wait the seconds the `Retry-After` header names (or `azure.retry_seconds` from `config/thresholds.toml`, 5 to start, never more than `azure.max_retry_seconds`, 60), up to `azure.retries` (3) tries, then fall back to today's `judge_unavailable`; `src/strata/agent/foundry.py` does the same for the agent's run and tool-output calls before `agent_unavailable`; every wait is logged with the try count; a fake clock in the tests, no sleep. The waits must stay inside the answer route's own timeout (`[answer]` in config/thresholds.toml), so the sum of the retries is bounded by it. Prove it on the fixture: a judge whose client answers 429 twice then 200 keeps the sentence with two logged waits; four 429s give `judge_unavailable` as today; a 403 gives up at once; the same for the agent's call through Foundry's fake. The live proof is the orchestrator's: the demo-ready command's smoke question passing three times in a row on the paid workspace after the merge and the App redeploy, with any retry visible in the log. Parked for the owner beside this ticket: raising the gpt-5.4 deployment's capacity in Azure (the day-one caps in `ops/dayone/dayone.toml` would move with it), which removes the cause rather than the symptom.

Read first: `src/strata/agent/judge.py`, `src/strata/agent/answer_check.py`, `src/strata/agent/foundry.py` (where a 429 becomes agent_unavailable), `src/strata/lakehouse/costs.py` (ticket 107's retry on a 429 with Retry-After, the pattern to copy), `config/thresholds.toml` [agent] and [answer], `tests/test_answer_stream.py`, `tests/test_judging.py`, the catch-up file's block "Ticket 117, steps 1 and 2 ran" of October 28.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** agent
**Phase:** P4
**Design review:** no

- [ ] The judge retries a 429 or 503 up to `azure.retries` times with the wait the header names or the config default, bounded by `azure.max_retry_seconds` and the answer route's timeout, with a fake clock in the tests; four refusals give `judge_unavailable` as today, and a 403 gives up at once.
- [ ] The agent's Foundry calls retry the same way before `agent_unavailable`, with the same tests through Foundry's fake.
- [ ] The tries and the waits live in `config/thresholds.toml` under `[azure]` and nowhere else; each wait is logged with its try count; the recorded ask streams and the benchmark still pass; the gate adds at most one second.
- [ ] On the paid workspace, after the merge and the App redeploy, the demo-ready command's smoke question passes three times in a row (recorded in the catch-up file under this ticket).

## Comments

- October 27, 2026, orchestrator: opened at 23:00 PDT on the orchestrator's judgment after the three measured smoke runs of the night (two passes, then the judge's 429); it builds in wave 4u. The capacity question is the owner's, on the morning list.
