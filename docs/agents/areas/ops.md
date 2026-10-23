# Area brief: ops

Tickets with `Area: ops` build the repo's machinery and the operations around it: the scaffold and the gate, credentials and the day-one tests, the Databricks bundle, deploys, the nightly job, the demo-ready command, budgets and caps.

Read: `docs/PLAN.md` sections 2, 10, 11, 12, 13, 14, 16 and 18, and "The shared workspace" in `docs/agents/build.md`.

- The gate (`.githooks/pre-commit`) runs the ground-truth SQL and the offline tests in under two minutes with no network, includes `python3 .claude/hooks/test_guard.py`, and skips the tests when only Markdown files are staged.
- Everything deploys from code: the bundle, the app, the jobs, the Genie space, the AI Search index and the Foundry agent. One command takes a fresh workspace to the demo state.
- Work on the shared workspace runs one at a time and leaves fairshare's catalog, app and job untouched.
- Human-only steps (tokens, the Azure sign-in, model deployments, the pay-as-you-go switch, budgets, inviting an outside reviewer) go into a wizard the user runs in their own terminal: call the Skill tool with `mattpocock-skills:wizard`.
- Caps are configuration: tokens per minute on each deployment, the daily page cap in ingestion, at most two replicas for anything hosted.
