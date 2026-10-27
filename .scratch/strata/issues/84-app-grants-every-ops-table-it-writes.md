# 84: The App's grant list names every ops table the App writes after an answer, so a fresh deploy never loses run records

**What to build:** After each answer, `src/strata/agent/runs.py` writes the run row to `strata.ops.agent_runs` and then the run's tool calls, reads and removed sentences to `strata.ops.tool_calls`, `strata.ops.tool_call_reads` and `strata.ops.answer_removals` (its `CALLS`, `READS` and `REMOVALS`), in a thread beside the answer, so a refused insert loses the record without breaking the answer. `ops/app/deploy_app.py`'s `grants()` names eighteen ops tables in its `tables` tuple and not those three. On the paid Azure workspace, where the App's service principal owns no table, the App's first answer on October 26, 2026 at 22:28 UTC got `PERMISSION_DENIED: Principal 'app-1vvvna strata' does not have MODIFY on Table 'strata.ops.tool_calls'` (the warehouse's query history), and every run record was lost until the user granted the three tables by hand at 23:58 UTC. Add the three tables to the grant list with SELECT and MODIFY, and add a test that compares the grant list with the tables the App writes as itself, read from the code (`runs.py`'s constants, `src/strata/estimates/exposures.py`, the usage events, the drafts and the other writers the comment above `tables` names), so a new writer cannot be left out again. The live proof is the second session's next App redeploy from the merge commit: the deploy's step 6 prints the grants, and `databricks grants get table strata.ops.tool_calls -p strata` shows the App's principal with SELECT and MODIFY (the user's hand grants make the statement a no-op there; a fresh workspace is the real test).

Read first: `ops/app/deploy_app.py` (`grants`, `tables`, `ACCESS`, `LESSON_REVIEW_TABLES`, `RETRIEVAL_TABLES`), `src/strata/agent/runs.py` (`TABLE`, `CALLS`, `READS`, `REMOVALS`, `record`), `src/strata/server/app.py` around line 1302 (the writers started after an answer), `ops/app/tests/test_deploy_app.py` (the grants test near line 245), the catch-up file's App block of October 26 (the user's three grants and the query history line).

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] `grants()` gives the App's principal SELECT and MODIFY on `strata.ops.tool_calls`, `strata.ops.tool_call_reads` and `strata.ops.answer_removals`, and the existing grants test names them.
- [ ] A test reads the tables the App writes as itself from the code and fails when one of them is missing from the grant list.
- [ ] After the second session's next App redeploy from the merge commit, `databricks grants get table` shows the App's principal with SELECT and MODIFY on the three tables (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 17:10 PDT with the user's yes, from the second session's reading of the paid workspace's query history. The user ran the three grants by hand the same evening, so the App records its answers there now; this ticket keeps the next workspace from losing them.
