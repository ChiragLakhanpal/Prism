# 82: The bundle commands use only the host and token from the env file, never the CLI's default profile, so a deploy lands on the workspace the env file names

**What to build:** On October 26, 2026 at 20:24 UTC `ops/bundle/deploy.py`, run from a snapshot with an env file that named the new paid workspace, deployed to the Free Edition workspace instead: the Databricks CLI (1.22.1) ran the `bundle` commands with the default profile in `~/.databrickscfg` (`[__settings__] default_profile`, a still valid OAuth profile for the old host) and ignored DATABRICKS_HOST and DATABRICKS_TOKEN in the environment. Three checks by the second session settled it: `databricks auth describe` with the same environment resolved the new host, `bundle summary` in a fresh snapshot resolved the old workspace's user and pulled its state (lineage c0ce886e, serial 25), and the same command with DATABRICKS_CONFIG_FILE=/dev/null resolved the new workspace and its state (lineage dfafaf94, serial 2). The old workspace's bundle state was rewritten (serial 24 to 25, nothing created), and step 2 of the deploy then failed on the new warehouse with SCHEMA_NOT_FOUND strata.bronze. `ops/bundle/bundle_live.py`'s `cli_env` strips every DATABRICKS_* key from the shell, so a caller cannot pass the config file through. Make `cli_env` set DATABRICKS_CONFIG_FILE to `/dev/null` itself (or DATABRICKS_CONFIG_PROFILE to a profile it owns), so every CLI call made by the repo's scripts reads only the host and token the env file gives it; add a test on the fake CLI environment that the variable is set and that no profile from the config file can win; say in the catch-up file's header and in `bundle/README.md` that the CLI's default profile never applies to the repo's commands. `ops/bundle/check.py job-run` goes through the SDK, not the CLI, and is not affected.

Read first: `ops/bundle/bundle_live.py` (`cli_env`, the CLI calls), `ops/bundle/tests/` (the fake CLI environment), `ops/bundle/deploy.py` (where the CLI runs), `bundle/README.md`, the catch-up file's header and the second session's record of the 20:24 UTC run.

**Blocked by:** None (can start immediately)

**Status:** done
**Area:** ops
**Phase:** P4
**Design review:** no

- [x] `cli_env` sets DATABRICKS_CONFIG_FILE to `/dev/null` (or a profile the repo owns), and a test proves the CLI environment the scripts build holds it and no DATABRICKS_* value from the shell; the existing bundle tests pass unchanged.
- [x] `bundle/README.md` and the catch-up file's header say that the repo's CLI calls never use the config file's default profile, and name the October 26 run that showed why.
- [ ] The second session's next bundle deploy from a snapshot with the new workspace's env file lands on the new workspace (`bundle summary` names the new host's user and lineage dfafaf94), recorded in the catch-up file under this ticket.

## Comments

- October 26, 2026, orchestrator: opened at 13:40 PDT from the second session's finding during the paid-workspace chain, as the one exception to the rule of no new tickets after 49 without the user's yes: without it every bundle deploy from this Mac lands on Free Edition. Built by the orchestrator in the worktree `.claude/worktrees/orch-82`.
- October 26, 2026, orchestrator (merger): built in `.claude/worktrees/orch-82` (ca6b5be1, gate green in 136.8 seconds) and merged into build/strata as efce9da6 with the gate green at the merge, with no reviewer or verifier, like tickets 69, 71 and 73 (the status writer's decision 87 asks for a review and a verify pass; the change is one line in `cli_env`, one test, and two documents). The same commit fixed the catch-up file's line 3152 (ticket 49's parked block quoted the environment file's path, which the command test cuts at the quote; the P4 gate tripped on it) and gave `docs/paid-workspace.md` three second-run fixes from the sessions that ran it: the CLI profile rename before the sign-in, the token to type at stage 1, and the secret scope and two secrets to save by hand after stages 6 and 9. The live proof (criterion 3) is the second session's next bundle deploy from a snapshot of efce9da6 or later.
