# 01: Repo scaffold with fairshare's rules, hooks, shell and the offline gate

**What to build:** A fresh clone of the strata repo installs, builds and passes its offline gate with the network off, and every later ticket has a place to land. The planning commit already carries CLAUDE.md's rules and the destructive-command guard with its own tests; this ticket keeps them as they are and adds the rest of what PLAN.md section 12 brings over from fairshare, copied and never imported: the pre-commit gate hook, the server shell (viewer identity, the harness helpers, the identity and stream routes) and the web shell (the api, sse, store and export libraries), unstyled and laid out in the modules the spec names. The gate runner starts small and grows seam by seam: today it runs the guard's tests, builds a placeholder fixture, runs one ground-truth SQL check on DuckDB, one server test and one Playwright smoke test of the shell, prints its total time and fails above two minutes. When only Markdown files are staged it skips the tests. The server and the web app take their ports from environment variables with free-port defaults, so several worktrees can run side by side. Everything on PLAN.md section 12's "Leave" list stays behind.

Read first: CLAUDE.md; docs/PLAN.md sections 8, 10 and 12; docs/agents/areas/ops.md; the spec's Seams and Testing Decisions; GLOSSARY.md.

**Blocked by:** None (can start immediately)

**Status:** done
**Area:** ops
**Phase:** P0
**Design review:** no

- [x] A fresh clone installs with one documented command, and the single gate command passes with the network disabled, printing a total time under two minutes.
- [x] With the repo's hooks path set to the gate hook, a commit with a failing test is blocked and the same commit with the test fixed goes through.
- [x] The gate runs the guard's own tests and fails when one of them fails.
- [x] The gate scans staged changes and the full git history for secrets, fails on a planted fake key, and passes once it is removed.
- [x] A commit that stages only Markdown files skips the tests and finishes in a few seconds.
- [x] The gate fails when a run exceeds two minutes, shown once with an artificial delay in a throwaway test that is then removed.
- [x] Two copies of the app start side by side from two worktrees without a port clash.
- [x] A search of the repo for fairshare's airline terms, synthetic data, deck content and Power BI parity returns nothing, and CLAUDE.md and the guard are unchanged.
- [x] The server answers its health route, and the web shell renders in the Playwright smoke test.

## Comments

- October 22, 2026, orchestrator: dispatched to an implementer in its own worktree. Credentials are not in place yet, so workspace steps are parked in docs/workspace-catchup.md.
- October 22, 2026, orchestrator: reset to ready-for-agent. The first session had started one folder up, so the guard hook and the named agents never loaded; the worktree was removed before any commit. The next session, started inside strata/, dispatches this ticket again.
- October 23, 2026, orchestrator: dispatched again to an implementer in its own worktree, from a session started inside strata/. Credentials are still missing, so every workspace step is parked in docs/workspace-catchup.md and the offline parts are built against local fixtures.
- October 23, 2026, merger: merged `strata/01-repo-scaffold-and-offline-gate` at b5b59df into `build/strata` as merge commit 45a8298. Round 3's review approved the branch with no blocking findings, and round 3's verification passed all 9 criteria with none parked.
  - **How I merged.** I followed the README's "Merge a ticket" steps: `git merge --no-ff --no-commit`, then `scripts/install`, then `git commit`. The merge had no conflicts, because `build/strata` had not moved since ab3212e. The install ran offline from the local uv and npm caches in 1.4 seconds. Before the merge, I ran `gates/secret_scan.py` in the ticket worktree, so it read the branch's own history. It found no keys. This covers the gap that verification finding V1 describes for this merge only.
  - **The gate.** It passed on the merged tree in 21.4 seconds: the secret scan, the guard's tests, the fixture build, the Python tests, the web build and the Playwright tests.
  - **Evidence from verification.** The gate passed offline in a fresh clone in 21.3 seconds. A commit with a failing test was blocked, and the fixed commit went through. The guard's tests failed the gate in a temp folder. The secret scan named a planted key in the staged changes and in the history, and passed once each key was gone. A Markdown-only commit took 0.57 seconds. A test that slept 150 seconds failed the gate at 120.1 seconds. Two copies of the app ran side by side on separate ports. The searches for Leave-list terms found only two allowed hits. CLAUDE.md and the guard kept their blob hashes. The health route answered, and 9 Playwright tests passed. The notes are `.notes/01-review-r3.md` and `.notes/01-verify-r3.md`.
  - **Workspace steps.** The implementer named none, so nothing was added to docs/workspace-catchup.md. Verification notes that `GET /api/me` inside the deployed Databricks App must name the viewer and return `"has_token": true`, never the token. The ticket that deploys the app should run that check.
  - **Left for a later ticket.** Verification finding V1: during a merge, the secret scan reads only HEAD's history, so it does not read the incoming branch's commits. Review polish P1 (the IPv6 test fails on a computer without IPv6), P2 (the gate tells a person who lacks uv or npm to run `scripts/install`, which needs them) and P3 (the word "Clear" in `tests/test_server_start.py` line 21) are still open.
