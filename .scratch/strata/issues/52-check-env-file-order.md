# 52: The bundle checks take --env-file after the subcommand, as every catch-up command writes it

**What to build:** `ops/bundle/check.py` defines `--env-file` only on its top parser, so `uv run --script ops/bundle/check.py same-rows --env-file .env` exits 2 with "unrecognized arguments: --env-file". That order is written 22 times: ten command lines and one mention in `docs/workspace-catchup.md` (tickets 04, 07, 08, 11 and 17), four places in `check.py` itself, and seven ground-truth SQL comments. The P0 phase gate found it on October 23, 2026 (`.notes/phase-P0-verify.md`). Make the script accept `--env-file`, and `--write` for `schedules`, in either position, by giving each subparser the same options through a shared parent parser, so the commands work as written and the top-level form keeps working. Add a test for each subcommand in both orders. Do not change what the commands do, and do not rewrite the command lines in the docs or the SQL comments.

Read first: `ops/bundle/check.py`; the tests under `ops/bundle/tests/`; `docs/workspace-catchup.md`; `.notes/phase-P0-verify.md`; `docs/agents/areas/ops.md`.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P1
**Design review:** no

- [ ] `uv run --script ops/bundle/check.py job-run --env-file .env`, `... same-rows --env-file .env` and `... schedules --env-file .env --write` parse without error, and so do the forms with `--env-file` before the subcommand; a test under `ops/bundle/tests/` proves that each of the six forms parses to the same arguments, without reading any real environment file.
- [ ] With a missing environment file, each form stops with the same one-sentence message as before, and a wrong option still exits with code 2.
- [ ] Every command line in `docs/workspace-catchup.md`, `check.py` and the ground-truth SQL comments works as written; the ticket changes none of them unless one is wrong for another reason, and then the report says which.
- [ ] The gate passes by hand on the branch with build/strata merged in, and the python and ops lanes' test counts are reported.

## Comments

- October 23, 2026, orchestrator: opened after the P0 phase gate's re-check found that every catch-up command for the bundle checks fails as written. The user will run those commands after the wizard, so the fix lands before then. It is a fix the catch-up file depends on, not new scope. Dispatched to an implementer in its own worktree on branch strata/52-check-env-file-order; a side run builds, reviews and verifies it, and the next wave merges it first.
