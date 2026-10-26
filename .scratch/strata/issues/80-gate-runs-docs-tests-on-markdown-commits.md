# 80: The gate runs the tests that read the Markdown files on a Markdown-only commit, so a note cannot break the next merge's gate

**What to build:** When every staged file is Markdown, `gates/offline.py` runs only the steps marked `always` (today the secret scan), so a Markdown-only commit skips every test, including the tests that read Markdown: `ops/bundle/tests/test_check.py::test_every_check_command_the_repo_writes_parses_as_written` reads every `uv run --script ops/bundle/check.py ...` line in the docs and parses it, and `ops/dayone/tests/test_results_document.py` checks `docs/day-one-results.md` against its marked blocks. Twice on October 26, 2026 a Markdown-only commit broke the next code commit's gate: 929a14c5 put a paragraph outside the marked blocks of the results document (ticket 70's first merge aborted on it; fixed in 4d96275), and 3e684c58's parked block for ticket 78 wrote `check.py same-rows --env-file "<main checkout>/.env"`, which the test's pattern cuts at the double quote (ticket 76's merge hit it; the line now reads `--env-file .env`). Add one step to `gates/steps.toml` with `always = true` that runs those tests (`uv run --frozen pytest --basetemp .gate-tmp/docs ops/bundle/tests/test_check.py::test_every_check_command_the_repo_writes_parses_as_written ops/dayone/tests/test_results_document.py`, a few seconds), placed so it runs alone after the secret scan and before the lanes, and keep `tests/test_gate.py`'s rule that each test folder runs in exactly one step (the step names two files, not a folder; extend `paths_tested` or the rule's wording if it counts them). A test in `tests/test_gate.py` proves a Markdown-only commit now runs that step: a throwaway repo whose always step fails blocks a Markdown-only commit. README's gate section says which tests a Markdown-only commit still runs. Also make the written-commands test's pattern read a double-quoted argument as one argument, so a quoted path parses as the shell would read it.

Read first: `gates/offline.py` (`only_markdown`, `main`), `gates/steps.toml`, `tests/test_gate.py` (`test_a_commit_of_only_markdown_skips_the_tests`, `paths_tested`, `gate_steps_per_test_folder`), `ops/bundle/tests/test_check.py` (`COMMAND`, line 405), `ops/dayone/tests/test_results_document.py`, README's gate section.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] A Markdown-only commit runs the secret scan and the new docs step, and a throwaway repo whose always step fails blocks such a commit (a test in `tests/test_gate.py`); the gate's time for a Markdown-only commit stays under 30 seconds.
- [ ] The written-commands test reads a double-quoted argument as one argument, with a test case for `--env-file "<main checkout>/.env"`.
- [ ] README's gate section says which tests a Markdown-only commit still runs, and `tests/test_gate.py`'s folder rule still passes with the new step.

## Comments

- October 26, 2026, orchestrator: opened at 06:10 PDT from the second session's finding on ticket 76's merge gate (line 2827 of the catch-up file). On the build's path: every merge runs the gate on a tip that Markdown-only commits touch many times a day.
