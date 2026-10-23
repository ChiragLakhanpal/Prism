# Area brief: ops

Tickets with `Area: ops` build the repo's machinery and the operations around it: the scaffold and the gate, credentials and the day-one tests, the Databricks bundle, deploys, the nightly job, the demo-ready command, budgets and caps.

Read: `docs/PLAN.md` sections 2, 10, 11, 12, 13, 14, 16 and 18, and "The shared workspace" in `docs/agents/build.md`.

- The gate (`.githooks/pre-commit`) runs the ground-truth SQL and the offline tests in under two minutes with no network, includes `python3 .claude/hooks/test_guard.py`, and skips the tests when only Markdown files are staged.
- The gate runs its steps in lanes, side by side. To add a step to a lane, give it `lane = "<name>"` in `gates/steps.toml` and put it among the steps that have lanes, below the steps it needs in that lane. A step with no lane runs alone, after every step above it. A new pytest step names the folders it tests, so each test folder runs in exactly one step. A test folder whose tests read the fixture database runs in the python lane, below the build, and is named in `FIXTURE_READERS` in `tests/test_gate.py`. When one lane gets slow, give its pytest step more pytest-xdist workers (`--numprocesses`) or move some of its folders to a new lane.
- Everything deploys from code: the bundle, the app, the jobs, the Genie space, the AI Search index and the Foundry agent. One command takes a fresh workspace to the demo state.
- Work on the shared workspace runs one at a time and leaves fairshare's catalog, app and job untouched.
- Human-only steps (tokens, the Azure sign-in, model deployments, the pay-as-you-go switch, budgets, inviting an outside reviewer) go into a wizard the user runs in their own terminal: call the Skill tool with `mattpocock-skills:wizard`.
- Caps are configuration: tokens per minute on each deployment, the daily page cap in ingestion, at most two replicas for anything hosted.
