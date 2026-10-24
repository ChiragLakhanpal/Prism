# 54: One gate at a time on this computer, so parallel gates stop timing each other out

**What to build:** The offline gate (`gates/offline.py`, run by `.githooks/pre-commit` and by hand) fails when it takes longer than two minutes. On October 24, 2026, up to four gates ran at once on this computer: the build wave's implementers, reviewers and mergers in their worktrees, and a second session committing in the main checkout. At load averages of 25 to 50 the gates took 100 to 120 seconds, timed out, and failed Playwright tests that pass alone, so the sessions had to take turns by hand. Make the gate take one lock for the whole computer before it starts its clock: a lock file under the user's temporary folder (not under the repo, since each worktree is its own repo copy), held with `fcntl.flock` for the whole run, so a second gate waits for the first and then runs alone. Print one line while waiting, with the waiting time, and give up with a clear message after a limit named in `gates/steps.toml` or at the top of `gates/offline.py` (20 minutes to start with). The two-minute cap counts from the moment the lock is held, not from the start of the wait. The lanes inside one gate keep running side by side as they do today. Markdown-only commits, which run only the secret scan, also take the lock, so they do not read a tree another gate is building in; they are quick, so that costs nothing.

Read first: `gates/offline.py` (the whole file; the clock and the lanes), `.githooks/pre-commit` and `.githooks/pre-merge-commit`, `tests/test_gate.py` and `tests/test_offline.py` (they build throwaway repos and run the gate in them), README's "The gate" section and `docs/agents/areas/ops.md`.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P1
**Design review:** no

- [ ] Two gates started within a second of each other in two throwaway repos run one after the other: the second one's log shows the waiting line, its two-minute clock starts when it holds the lock, and both pass. A test under `tests/` proves it with two subprocesses and a lock path under `tmp_path` (an environment variable names the lock path, so tests never share the real one).
- [ ] A gate that cannot get the lock within the limit stops with one sentence that names the limit and the lock path, and exits with a code other than 0; a test proves it with a held lock and a short limit.
- [ ] The gate's own tests in `tests/test_gate.py` and `tests/test_offline.py` still pass, and so does the whole gate by hand on this branch with build/strata merged in; report its time.
- [ ] README's gate section and `docs/agents/areas/ops.md` say in two or three sentences that one gate runs at a time on a computer, where the lock lives, how long a gate waits, and that the two-minute cap counts from the moment it holds the lock.

## Comments

- October 24, 2026, orchestrator: opened after the build wave and a second session timed each other's gates out all afternoon and took turns by hand. This is enabling work the spec allows for the gate, not new scope. Dispatched to an implementer in its own worktree on branch strata/54-one-gate-at-a-time at the next restart of the wave.
