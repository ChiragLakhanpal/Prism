# Prism is the name, and the workspace keeps the strata identifiers

On November 5, 2026, the user renamed the product from Strata to Prism, and Surya Yadav joined as a builder. The user chose a brand-only rename. Every word a person reads now says Prism: the app's copy, the deck, the figures' text, the README, the docs, the agents' instructions, and the comments and messages in the code. Each `Strata` became `Prism` and each `STRATA` became `PRISM`. The lowercase `strata` did not change anywhere, and neither did any name a program or the workspace looks up.

## What stays, and why

- The Python package and its module paths: `src/strata`, `import strata`, `python -m strata.*`, `strata.tools.*`. A package rename touches every import, every command in the docs, the bundle's tasks and the App's start command at once.
- The Databricks catalog and its tables, such as `strata.gold.*` and `strata.ops.*`, the bundle's name, the jobs (`strata nightly`, `strata cost pull`), the App's name `strata` and its address, the secret scope `strata`, and the Lakebase instance `strata-state`. These are live workspace objects. Renaming one is a migration: copy or move the data, grant again, redeploy the App and update every reference in one window.
- The Azure names: the Foundry resource `wb-strata`, the Foundry project `Strata` (`ops/dayone/dayone.toml`, and the endpoint `.../api/projects/Strata`), the agents such as `strata-orchestrator`, and the guardrail `strata-guardrail`. They are the addresses the code calls.
- Names the code uses to find its own objects on the workspace. The App's description (`DESCRIPTION` in `ops/app/deploy_app.py`, and the probe app's in `ops/dayone/live.py`) is how a deploy knows the App is this repo's, so a new description would make the next deploy leave the live App alone. The Genie space's title in `config/genie.toml` is how its deploy finds the live space, so a new title would make a second space. Both keep the old name until the workspace migration.
- Environment variables (`STRATA_*`), the gate's lock file (`STRATA_GATE_LOCK`), the upload header `X-Strata-File-Name`, browser storage keys such as `strata.sidebar`, and every file and folder name, such as `.scratch/strata`, `docs/blueprint/strata-blueprint.html`, `docs/readme/strata-*.webp` and `docs/presentation/strata-presentation.pdf`. Changing them would break saved settings, links and scripts for no change a person reads.
- Records of what happened. Pictures, PDFs and the film were captured before the rename and still show Strata; `.github/README.md` says so under the film. A command's printed output quoted in the docs follows the code, except where a line records a workspace object's old name.
- `STRATA` as an identifier or as the plural of stratum: the constant `STRATA` in `src/strata/config.py` (What, How and Why) and in `ops/bundle/tests/test_check.py`, and "The three strata" in `web/public/deck/notes/three_strata.svg`.

## Follow-ups

- A workspace migration that renames the catalog, the App, its description, the secret scope, the Lakebase instance, the jobs and the Genie space's title, in one window, with the grants again.
- A package rename from `strata` to `prism`, with the imports, the bundle's tasks, the App's start command and the docs' commands in one change.
- New screenshots, a new film and a new presentation PDF, once the screens are final.
- The GitHub repo's rename to `ChiragLakhanpal/Prism`, which `config/urls.toml` already names.
