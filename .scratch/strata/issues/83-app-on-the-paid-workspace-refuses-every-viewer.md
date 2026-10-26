# 83: The App on the paid workspace refuses every viewer: read the forwarded token's refusal and fix its cause

**What to build:** On October 26, 2026 at 21:02 UTC the App deployed on the paid Azure workspace (https://strata-7405609289499029.9.azure.databricksapps.com) showed "Your account can't read the data I hold yet" on every page for the user who owns the catalog and the warehouse: the server answered 403 with the code permission on /api/freshness, /api/home and /api/following for the browser's forwarded token, while the same user's own OAuth tokens (all APIs, and one with only the sql scope) ran statements on the same warehouse and got 200 on every route. The second session's checks cleared the grants (account users read every schema; the App's service principal has its grants), the App's resources (the sql-warehouse resource is the new warehouse, user_api_scopes sql and dashboards.genie, effective scopes include sql), the warehouse permissions (the viewer owns it) and the query history (no statement as the viewer reached the warehouse): the Statement Execution API refuses the forwarded token before any statement runs, with a 401 or 403 whose body the server dropped, because `as_viewer` and `read_for` in `src/strata/server/app.py` logged only the viewer's name. Step 1 (done, d7423568, merged 912306fe): both paths log the PermissionDenied message, which carries the workspace's status and the first 400 characters of its body and never the token. Step 2 (live): redeploy the App from 912306fe or later with --keep-secrets, open it in the browser, and read the logged line. Step 3: fix the cause the line names (the candidates: the forwarded token's audience is the App's OAuth integration rather than the workspace; the consent the user gave does not cover the sql scope; an Azure-side difference in user authorization for Apps), with a test where the fix is code, and record the fix in `docs/paid-workspace.md` section 8 and in the catch-up file under this ticket.

Read first: `src/strata/server/app.py` (`as_viewer`, `read_for`, the viewer and its token), `src/strata/lakehouse/engine.py` (`http_transport`, `PermissionDenied`, line 310), `ops/app/deploy_app.py` (`resources`, the user authorization scopes), `docs/workspace-catchup.md` (the second session's record of the 21:02 UTC open and its five checks), `docs/paid-workspace.md` section 8.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** app
**Phase:** P4
**Design review:** no

- [x] The server logs the workspace's answer when it refuses a viewer, in both refusal paths, without the token (d7423568; the existing server tests pass).
- [ ] The App's log on the paid workspace holds the refusal's status and body for one browser open after a redeploy from 912306fe or later (recorded in the catch-up file under this ticket).
- [ ] The cause is fixed and the App's pages load for the user on the paid workspace; `docs/paid-workspace.md` section 8 names the problem and the fix.

## Comments

- October 26, 2026, orchestrator: opened at 15:05 PDT, as the second exception to the rule of no new tickets without the user's yes, because the App must answer on the paid workspace for the demo. Step 1 was built by the orchestrator in `.claude/worktrees/orch-83` and merged with the gate green (120.6 seconds in the worktree, green again at the merge); the second session runs step 2.
