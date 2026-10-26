# 70: Redeploy the App without rewriting its secrets, so a session that may not write secrets can deploy new code

**What to build:** `ops/app/deploy_app.py` always runs step 3, which writes the Foundry agent's four keys and the judge's two Azure OpenAI keys into the secret scope with `put_secret` before it uploads and deploys the code. Only the user may write secrets in this workspace (the second session's writes are denied), so every redeploy of new code, including the retry after ticket 69's numpy fix, waits for the user by hand. Add a `--keep-secrets` option: with it, step 3 writes no secret, says which secret names it expects to exist already (it may list the scope's keys, never their values), warns by name about any that are missing and goes on without them, and still gives the app its resources, the user authorization scopes and the secret references in `app.yaml`; everything else (the web build, the upload, the deploy, the app's address) runs as today. Without the option, the script behaves exactly as it does now. Add a test with the fake workspace that `--keep-secrets` makes no `put_secret` call and still configures the app with the same resources, and a test that a missing expected secret is reported by name before the upload starts. Update the script's docstring, README's deploy section and `docs/workspace-catchup.md`'s header (the mergers' note) so the second session knows it can redeploy code with `--keep-secrets` once the user has written the secrets. Change nothing about what the app receives.

Read first: `ops/app/deploy_app.py` (steps 3 to 5, `resources()`, `main()`), `ops/app/app_live.py` (`put_secret`, `configure_app`), `ops/app/tests/test_deploy_app.py` (the fake workspace), README's deploy section, `docs/workspace-catchup.md`'s header, ticket 69's done comment (the Python 3.11 pin and the deploy log).

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P2
**Design review:** no

- [ ] `uv run --script ops/app/deploy_app.py --env-file <file> --keep-secrets` on the fake workspace makes no `put_secret` call, configures the app with the same resources and scopes as a run without the option, and prints the secret names it expects; a run without the option is unchanged (the existing tests still pass).
- [ ] A missing expected secret is reported by name when `--keep-secrets` is given and the scope lacks it (the fake workspace lists its keys), and the deploy goes on without that key the way a deploy without the key in the environment file does today (the app comes up and says it has no agent or no judge); the script's exit code stays 0 and the report line says what to write into the scope. (Changed on October 25, 2026 at 23:20 from "exits with an error": the scope lacks FOUNDRY_TENANT_ID tonight, and the point of the option is to prove the package step and the app's start without the user's hands.)
- [ ] The docstring, README's deploy section and the catch-up file's header say when to use `--keep-secrets`; the live proof is the second session's redeploy with it, recorded under this ticket in the catch-up file with the app's address.

## Comments

- October 25, 2026, orchestrator: opened at 23:05 PDT while the user sleeps, so the second session can redeploy the App overnight after ticket 69's fix and report whether the app starts on Python 3.11, instead of waiting for the user's hands. Dispatched to an implementer in a side run; a merge-only run lands it.
