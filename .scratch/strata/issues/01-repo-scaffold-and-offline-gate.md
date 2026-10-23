# 01: Repo scaffold with fairshare's rules, hooks, shell and the offline gate

**What to build:** A fresh clone of the strata repo installs, builds and passes its offline gate with the network off, and every later ticket has a place to land. The planning commit already carries CLAUDE.md's rules and the destructive-command guard with its own tests; this ticket keeps them as they are and adds the rest of what PLAN.md section 12 brings over from fairshare, copied and never imported: the pre-commit gate hook, the server shell (viewer identity, the harness helpers, the identity and stream routes) and the web shell (the api, sse, store and export libraries), unstyled and laid out in the modules the spec names. The gate runner starts small and grows seam by seam: today it runs the guard's tests, builds a placeholder fixture, runs one ground-truth SQL check on DuckDB, one server test and one Playwright smoke test of the shell, prints its total time and fails above two minutes. When only Markdown files are staged it skips the tests. The server and the web app take their ports from environment variables with free-port defaults, so several worktrees can run side by side. Everything on PLAN.md section 12's "Leave" list stays behind.

Read first: CLAUDE.md; docs/PLAN.md sections 8, 10 and 12; docs/agents/areas/ops.md; the spec's Seams and Testing Decisions; GLOSSARY.md.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P0
**Design review:** no

- [ ] A fresh clone installs with one documented command, and the single gate command passes with the network disabled, printing a total time under two minutes.
- [ ] With the repo's hooks path set to the gate hook, a commit with a failing test is blocked and the same commit with the test fixed goes through.
- [ ] The gate runs the guard's own tests and fails when one of them fails.
- [ ] The gate scans staged changes and the full git history for secrets, fails on a planted fake key, and passes once it is removed.
- [ ] A commit that stages only Markdown files skips the tests and finishes in a few seconds.
- [ ] The gate fails when a run exceeds two minutes, shown once with an artificial delay in a throwaway test that is then removed.
- [ ] Two copies of the app start side by side from two worktrees without a port clash.
- [ ] A search of the repo for fairshare's airline terms, synthetic data, deck content and Power BI parity returns nothing, and CLAUDE.md and the guard are unchanged.
- [ ] The server answers its health route, and the web shell renders in the Playwright smoke test.

## Comments

- October 22, 2026, orchestrator: dispatched to an implementer in its own worktree. Credentials are not in place yet, so workspace steps are parked in docs/workspace-catchup.md.
