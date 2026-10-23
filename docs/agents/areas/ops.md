# Area brief: ops

Tickets with `Area: ops` build the repo's machinery and the operations around it: the scaffold and the gate, credentials and the day-one tests, the Databricks bundle, deploys, the nightly job, the demo-ready command, budgets and caps.

Read: `docs/PLAN.md` sections 2, 10, 11, 12, 13, 14, 16 and 18, and "The shared workspace" in `docs/agents/build.md`.

- The gate (`.githooks/pre-commit`) runs the ground-truth SQL and the offline tests in under two minutes with no network, includes `python3 .claude/hooks/test_guard.py`, and skips the tests when only Markdown files are staged.
- The gate runs its steps in lanes, side by side. To add a step to a lane, give it `lane = "<name>"` in `gates/steps.toml` and put it among the steps that have lanes, below the steps it needs in that lane. A step with no lane runs alone, after every step above it. A new pytest step names the folders it tests, so each test folder runs in exactly one step. A test folder whose tests read the fixture database runs in the python lane, below the build, and is named in `FIXTURE_READERS` in `tests/test_gate.py`.
- The python lane's tests run on four pytest-xdist workers, and the ops lane's on six. So every Python test must be safe beside the others: it writes only under its own `tmp_path` or a throwaway repo, opens the fixture database read-only, never changes the working folder or sets an environment variable, and listens on port 0 (or, when it must name a port, on one below the system's range, as `free_port` in `tests/test_server_start.py` does). A test that cannot run beside the others gets `@pytest.mark.xdist_group("<name>")` with a comment that says why, and its step gets `--dist loadgroup`.
- When a lane gets slow again, run `uv run --frozen pytest --durations=15 <its folders>` to find the slowest tests; one slow test sets a floor that no number of workers can lower. Then try more workers (`--numprocesses`) and keep the number that gives the lower total gate time over three runs by hand, since the lanes share the processors. Or move a folder that does not read the fixture database to a new lane.
- Everything deploys from code: the bundle, the app, the jobs, the Genie space, the AI Search index and the Foundry agent. One command takes a fresh workspace to the demo state.
- Work on the shared workspace runs one at a time and leaves fairshare's catalog, app and job untouched.
- Human-only steps (tokens, the Azure sign-in, model deployments, the pay-as-you-go switch, budgets, inviting an outside reviewer) go into a wizard the user runs in their own terminal: call the Skill tool with `mattpocock-skills:wizard`.
- Caps are configuration: tokens per minute on each deployment, the daily page cap in ingestion, at most two replicas for anything hosted.
