# 129: The scripts that act as the App fall back to the owner's token when the App principal's secret is gone

**What to build:** On October 28 and 29, 2026 the seed command (`strata.seed_examples`), the demo-ready command's Home step (`ops/demo/ready.py`) and every by-hand probe that signs in as the App's own service principal failed with `EngineError: The workspace gave the app no token: HTTP Error 401: Unauthorized`, twice after the owner had pasted a fresh OAuth secret into the environment file. The cause is the platform: when Databricks Apps stops the App (compute STOPPING at 14:44 UTC on October 29, deployment dropped at 16:33 UTC) and the watchdog or a person starts it again, the platform makes a new OAuth secret for the App's service principal (app-1vvvna strata, id 145252624286955) and the earlier secrets are gone (the principal holds exactly one active secret, created at 14:46:16 UTC, one minute into the 14:46 restart), so DATABRICKS_CLIENT_SECRET in the environment file dies with every restart. The App itself is unaffected, because the platform injects its token. Make the scripts that write as the App survive that: `src/strata/server/settings.py`'s `_the_app_s_engine` (or the place the seed and ready.py build their engine) tries the client credentials once, and when the token endpoint answers 401 invalid_client it falls back to the owner's token (DATABRICKS_TOKEN, the one every other ops script already uses), says so in one line ("The App's secret is gone since the platform restarted the App; writing as the owner instead."), and the rows it writes carry the owner as the writer where a writer column exists. The seed's grants: the owner is the catalog's owner, so no new grant is needed; say so in the docstring. Prove it on the fixture with a fake token endpoint that refuses the client, and the live proof is the orchestrator's: the demo-ready command's Home step passes after a platform restart with no new secret pasted, recorded in the catch-up file. Also stop asking the owner for the secret: the setup wizard's step that writes DATABRICKS_CLIENT_ID and DATABRICKS_CLIENT_SECRET says the secret lives only until the next platform restart and that the fallback covers it.

Read first: `src/strata/server/settings.py` (`_the_app_s_engine`, `as_the_app`, `token`), `src/strata/seed_examples.py` (`as_the_app`), `ops/demo/ready.py` (the Home step), `ops/demo/fresh_workspace.py`, `ops/wizard/strata-setup.sh` (the step that asks for the client secret), the catch-up blocks "The morning check of October 29" and the orchestrator's notes of October 29 on the secret.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] When the token endpoint refuses the App's client credentials with 401, the engine falls back to the owner's token with one printed line (a fixture test with a fake token endpoint); when the credentials work, nothing changes (a test).
- [ ] The seed and the demo-ready command's Home step pass on the fixture both ways, and the wizard's text about the client secret says it lives until the next platform restart.
- [ ] On the paid workspace, after a platform restart of the App with no new secret pasted, the demo-ready command's Home step passes and names the fallback (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 12:55 PDT after the second dead secret; the platform's restart at 14:46 UTC made the new one.
