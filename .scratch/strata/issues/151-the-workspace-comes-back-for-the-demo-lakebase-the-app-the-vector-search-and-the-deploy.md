# 151: The workspace comes back for the demo: Lakebase, the App, the vector search endpoint and its indexes, then the deploy

**What to build:** Nothing in the repo; the shared Azure Databricks workspace (docs/paid-workspace.md), which was shut down on November 3, 2026 (the user's "shut everything down"), comes back for the demo of the morning of November 6 at 8 am PST, on the user's decision of November 5 ("on the databricks app and github, rebuild the vector-search"). The steps, each recorded in `docs/workspace-catchup.md` with its command, its answer and the time, as every workspace step is:

1. Lakebase `strata-state`: `update-database-instance` with `stopped = false`; wait until it answers.
2. The vector search endpoint `strata-search` and its two delta-sync indexes (`strata.gold.passage_index`, `workspace.strata_dayone.passages_index`): recreate them from the archived definitions in `.notes/archive/strata-search/` in the main checkout (the endpoint first, then each index once the endpoint is online; a sync of each index; the source tables are untouched). Check with `ops/bundle/check.py` or the probes that `search_passages` answers before the deploy.
3. The App `strata`: `databricks apps start strata`; then, once the night's tickets have merged on `build/strata`, the deploy with `ops/app/deploy_app.py` from a snapshot (`git archive HEAD | tar -x -C <scratchpad>/snap-<sha>`, with `web/node_modules` linked from the main checkout), with `--force` if the bundle asks (docs/STATUS.md decisions 140 and 149); if the deploy ends in DeadlineExceeded while the compute starts cold, check `databricks apps list-deployments` and retry rather than debug. The App's `user_api_scopes` must still hold `sql`, `dashboards.genie` and `vector-search`.
4. The research item store's tables (ticket 147: `strata.ops.research_runs`, `research_items`, `research_briefs`) created on the workspace through the app state's path, and the demo seed `ops/research/seed.py --project P156634` run as the App, so the Deep research tab answers at once; then the demo-ready command's steps that still apply, and the three Deep research tabs (P156634 first) opened on the App in a private window and recorded in the catch-up file.
5. The jobs stay paused; the cost pull stays paused; nothing else starts.

The CLI: the `strata` profile's OAuth is expired; use the PAT from the project's env file with auth type pat and `DATABRICKS_CONFIG_FILE=/dev/null`, as docs/workspace-catchup.md records, without writing the env file's name in a command (the guard blocks it): the repo's helpers (`strata.dbx`, `ops/bundle/check.py`, `ops/app/deploy_app.py`) load it themselves. Any step the permission classifier denies (secret writes, grants, scope changes) goes to the user as one `!` line, self-contained, in `docs/STATUS.md`'s "For the user" list, never retried in another way. Cost: the App about US$9 a day, Lakebase about US$4, the endpoint about US$7, the warehouse per use; the user accepted this on November 5.

Run steps 1 to 3 (start) now, in parallel with the build, since each takes wall-clock time; step 3's deploy and step 4 wait for the orchestrator's word that `build/strata` holds the night's tickets. Report each step's time and answer, and the App's address.

Read first: docs/workspace-catchup.md (the last blocks, the CLI notes), docs/paid-workspace.md, `.notes/archive/strata-search/` (the archived definitions and `delete.sh`, which names what was deleted), `ops/app/deploy_app.py`, `ops/dayone/dayone.toml`, docs/STATUS.md decisions 140 and 149.

**Blocked by:** None for steps 1 to 3's start; the deploy waits for 146 to 149

**Status:** in-progress
**Area:** ops
**Phase:** P5
**Design review:** no

- [ ] Lakebase `strata-state` is running and the App `strata` is started, with the times in the catch-up file.
- [ ] The endpoint `strata-search` is online with both indexes synced, and `search_passages` answers on the workspace (a probe's answer in the catch-up file).
- [ ] The App runs the night's tip of `build/strata` (the deployment id and the commit in the catch-up file), with its three scopes.
- [ ] The research tables exist on the workspace and the P156634 seed run is stored; the Deep research tab opens on the App with the brief (recorded in the catch-up file).
- [ ] The jobs stay paused.

## Comments

- November 5, 2026, orchestrator: opened at 18:04 PST; steps 1 to 3's start run now, the rest after the merges.
