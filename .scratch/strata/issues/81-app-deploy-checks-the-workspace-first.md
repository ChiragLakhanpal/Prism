# 81: The App deploy checks the workspace's state first and confirms its deployment registered, so a stopped workspace fails at the start with a plain message

**What to build:** On October 26, 2026 at about 14:55 UTC the user ran `uv run --script ops/app/deploy_app.py --env-file .env` while the Free Edition workspace was stopped by its daily limit (job compute since 12:43 UTC, the SQL warehouse since 12:53, the App since 12:57). The script printed steps 1 to 5 as if they had passed ("5. Deploying the app. This takes a few minutes."), then failed in step 6 with `TABLE_DOES_NOT_EXIST: Table 'strata.ops.exposures' does not exist`, which was false: the table existed (Unity Catalog, created 06:33 UTC), the stopped warehouse answered every statement with an error, and `apps list-deployments` showed no deployment after 10:29 UTC, so step 5 had registered nothing. Twenty minutes went into a wrong diagnosis. Make the script fail early and say why: before step 1, read the App's compute status and the SQL warehouse's state through the SDK (no SQL), and when the App's compute is STOPPED "due to workspace or account status" or the warehouse is STOPPED and will not start, print one sentence that names the state and that the Free Edition's daily limit is the usual cause, then exit 2 without uploading. After step 5, read `apps list-deployments` (or the App's active deployment) and fail unless a deployment newer than the run's start exists with status SUCCEEDED, naming the deployment id and its time. In step 6, when the warehouse refuses a statement, say the warehouse's state before the statement's message, so an error from a stopped warehouse is never read as a missing table. Add tests with the fake workspace for the three cases (stopped App compute, stopped warehouse, no new deployment after step 5) and for the step 6 message. Do the same pre-check in `ops/bundle/deploy.py` (the warehouse) and `ops/demo/ready.py` (both), which print the workspace's state first already; keep their output otherwise unchanged.

Read first: `ops/app/deploy_app.py` (`main`, `deploy`, steps 5 and 6), `ops/app/app_live.py` (`run_sql`, the App lookups), `src/strata/lakehouse/engine.py` line 386 (`refused`), `ops/app/tests/test_deploy_app.py` (the fake workspace), `ops/bundle/deploy.py`, `ops/demo/ready.py` step 1, the catch-up file's 06-1 block and the second session's record of the stopped workspace on October 26.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] With the fake workspace, a stopped App compute or a stopped warehouse makes `deploy_app.py` exit 2 before step 1 with one sentence that names the state; a run where step 5 registers no new deployment fails there and names what it found; the existing tests pass unchanged.
- [ ] A warehouse refusal in step 6 names the warehouse's state before the statement's message (a test on the message), and `ops/bundle/deploy.py` and `ops/demo/ready.py` make the same pre-check with their output otherwise unchanged.
- [ ] README's deploy section says what the script checks first and after step 5; the live proof is the second session's next App deploy on a running workspace (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 08:03 PDT from the user's deploy of 14:55 UTC and the second session's check at 15:00 UTC. On the demo path: a deploy on demo day must say at once when the workspace is down.
