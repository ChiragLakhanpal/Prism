# 88: The App's requirements hold every package the server imports, so the Packages page loads on the deployed App

**What to build:** On the deployed App, the Packages page has shown "I couldn't load your packages and checked plans just now. Try again in a moment." since its first deploy, on Free Edition (October 25, 2026) and on the paid workspace (October 26). The page's loader calls `GET /api/planned-packages`, which answers 500 with the code `internal`; Application Insights holds the exception (references e12e0e3f32c043b75483cc9fcac419e0 and be101875624e4a5e7e18a9586b8d0cc8, October 27, 03:46 and 03:53 UTC): `ModuleNotFoundError: No module named 'sqlglot'`, raised from `src/strata/packages/store.py` line 196 through `src/strata/server/packages.py` and the engine's transpile step in `src/strata/lakehouse/engine.py` line 122, which the app-state store needs when the state lives in Lakebase. `ops/app/requirements.txt`, the App's lean package list, lacks sqlglot (and the same list lacked py3langid before ticket 66). Add `sqlglot` at `pyproject.toml`'s pin, and add a test under `ops/app/tests/` that reads the imports of every module the server can reach from `src/strata/server/app.py` (the code under `src/strata/`, followed through the repo's own imports) and checks that each third-party top-level module has its package in `ops/app/requirements.txt` (with the few name differences spelled out, such as `PIL` for pillow and `yaml` for pyyaml, and the standard library left out), so a missing package fails the gate instead of a page on the deployed App. Keep the list lean: a package only the nightly job or the scripts need stays out. The live proof is the second session's or the orchestrator's App redeploy with `--keep-secrets` from the merge commit, after which `GET /api/planned-packages` answers 200 for a signed-in viewer and the Packages page lists the examples Strata set up.

Read first: `ops/app/requirements.txt` and its tests (`ops/app/tests/test_app_package.py`, `test_deploy_app.py` line 104), `src/strata/packages/store.py` (`_open`, `_rows`), `src/strata/lakehouse/engine.py` (`transpile`, the Lakebase path), `src/strata/server/app.py` (`/api/planned-packages`), `pyproject.toml` (the pins), ticket 66's done comment (py3langid, the same gap), the catch-up file's App block.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** no

- [ ] `ops/app/requirements.txt` holds sqlglot at `pyproject.toml`'s pin, and the App's package test still passes.
- [ ] A test follows the server's imports through `src/strata/` and fails when a third-party module it reaches has no package in `ops/app/requirements.txt`; it fails on build/strata's list today (sqlglot) and passes on the branch.
- [ ] After the App redeploy from the merge commit, `GET /api/planned-packages` answers 200 for a signed-in viewer and the Packages page shows its examples (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 21:05 PDT with the user's go-ahead for the overnight build, from the exception in Application Insights. On the demo path: the Packages page is one of the five tabs.
