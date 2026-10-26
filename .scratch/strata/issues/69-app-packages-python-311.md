# 69: The App's packages resolve on the platform's Python 3.11

**What to build:** The user's first App deploy on October 25, 2026 failed at "Error installing packages": the Databricks Apps runtime is Python 3.11 (its pip log names `./.venv/lib/python3.11`), and `ops/app/requirements.txt` pinned `numpy==2.5.4`, whose every 2.5 release says "Requires-Python >=3.12", so pip found no matching distribution. The lean requirements take their pins from `uv.lock`, which the repo resolves for Python 3.12. Pin numpy at its newest release for 3.11 (2.4.6) under an "# app-python:" comment that says why, let `ops/app/tests/test_app_package.py` allow that one marked exception while every other pin still matches `uv.lock`, and prove by hand that the whole file resolves for Python 3.11 on the App's platform (`uv pip compile ops/app/requirements.txt --python-version 3.11 --python-platform x86_64-manylinux_2_28`). Change nothing else.

Read first: the pip log the user pasted (summarized in the comment below), `ops/app/requirements.txt`, `ops/app/tests/test_app_package.py`, `ops/app/deploy_app.py`'s docstring.

**Blocked by:** None (can start immediately)

**Status:** done
**Area:** ops
**Phase:** P2
**Design review:** no

- [x] `uv pip compile ops/app/requirements.txt --python-version 3.11 --python-platform x86_64-manylinux_2_28` resolves every pin (the report gives the count), and the App's deploy reaches "Deploying the app" and ends with the app's address (the user or the second session runs it and records it in the catch-up file under this ticket's heading).
- [x] `ops/app/tests/test_app_package.py` passes: numpy is the one pin allowed below its `uv.lock` version, with its marker, and the server still starts with only the lean packages.

## Comments

- October 25, 2026, orchestrator: opened at 22:40 PDT from the user's deploy log and built by the orchestrator itself in the worktree `.claude/worktrees/orch-69`, since the user is waiting to see the app and the change is one pin plus its test. The log: "Collecting pillow==13.0.0 ... Downloading pillow-13.0.0-cp311-cp311-manylinux_2_27_x86_64 ...", then "Ignored the following versions that require a different python version: ... 2.5.4 Requires-Python >=3.12", then "No matching distribution found for numpy==2.5.4", then "Error installing packages". Resolution for Python 3.11 on x86_64 manylinux_2_28 after the change: 63 pinned packages, numpy 2.4.6, pillow 13.0.0, pydantic-core 2.50.1, psycopg 3.3.6. The second finding from the same log, that the environment file has no FOUNDRY_CLIENT_ID and FOUNDRY_CLIENT_SECRET so the app gets no agent, is the user's to fix before the next deploy.
- October 25, 2026, orchestrator (merger): merged into build/strata as 4a40152 after two gate timeouts under the wave's load and one pass at 119.5 seconds with the wave stopped. The branch's tests pass (4 of 4) and the resolution for Python 3.11 holds 63 pins. The user's redeploy at 22:48 still used numpy 2.5.4 because it ran before the merge; the next redeploy from build/strata is the live proof, to be recorded in the catch-up file under this ticket. The second session's live test showed the app principal needs Azure AI User where it exists, otherwise Cognitive Services User, which the docstring and the example file now say.
- October 25, 2026, orchestrator: live proof. The user's third deploy at 06:11 UTC on October 26 (from the main checkout after 4a40152) ended "App started successfully"; the App strata is RUNNING at https://strata-7474658003099155.aws.databricksapps.com with its nine resources bound (the warehouse, Application Insights, the app state database, the four Foundry keys, the two Azure OpenAI keys), as the second session read from the workspace. Asking through the agent still waits on the Cognitive Services User role assignment, which is the user's.
