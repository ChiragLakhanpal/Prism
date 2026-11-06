# 152: The demo setting: deep research writes from stored items only, and the seed reads the Bank's records from the engine it writes to

**What to build:** The user's instruction of November 5, 2026 at 19:55 PST: the demo uses pre-seeded briefs for a handful of projects and no live lookups. Two small changes:

1. **The setting.** `[research] live_sources = false` in `config/thresholds.toml` (the one place; `true` is the product's default, `false` the demo's). When false, `POST /api/projects/{pid}/research` behaves as `reuse: true` whatever the body says: it reads no source, writes the brief from the items the store holds for the project, and the stream's source steps say "from the stored run of <read_on>" instead of reading. When the store holds no run for the project, the run ends with the abstention `not_fetched` and the tab's empty state says a brief has not been prepared for this project (copy in `web/src/copy.ts` under `research`). The tab's button reads "Write the brief again" when the setting is false (copy), never "Research again".
2. **The seed.** `ops/research/seed.py` reads the Bank's own items (the ISR narrative passages and the procurement notices) through the engine the store writes to, so on the workspace they come from `strata.gold.passage` and `strata.gold.notice` on the warehouse and locally from the fixture database, and a project outside the fixture's documents still gets its ISR and notice items when seeded on the workspace. The sample file per project, `ops/research/sample_<pid>.toml`, stays the list of the outside items; the seed takes `--project` more than once or `--all` for every sample file present.

Tests: with the setting false, a POST with `reuse: false` reads no source (a fake reader that would raise is never called) and writes from the stored run; with no stored run the stream ends `not_fetched` and GET stays `{status: "none"}`; the seed with the engine flag reads ISR passages and notices for a fixture project from the fixture database (the same counts as before) and `--all` seeds every sample file. Keep the gate under 180 seconds.

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD. Essentials only, no polish. Commit with plain-English messages and no trailers. Do not change ticket files, docs/STATUS.md or anything under .scratch. Report: branch and worktree, the setting's name, each criterion's evidence, the gate's time, and the workspace steps (the App needs a redeploy for the setting; the seed command for several projects).

**Blocked by:** None (can start immediately)

**Status:** done
**Area:** agent
**Phase:** P5
**Design review:** no

- [ ] With `research.live_sources = false`, a POST never reads a source and writes the brief from the stored run; with no run it ends `not_fetched` and the tab says no brief has been prepared (tests).
- [ ] The seed reads ISR passages and notices through the store's engine, and `--all` seeds every `sample_<pid>.toml` (tests on the fixture).
- [ ] The gate passes under 180 seconds on the worktree.

## Comments

- November 5, 2026, orchestrator: opened at 20:05 PST from the user's instruction of 19:55 (pre-seeded briefs, no live lookups).
- November 5, 2026, merger: merged on the integrated branch `worktree-agent-adfa26ba0a813e559` (head c492ce9d, where an integrator joined tickets 152, 155, 150, 154 and the four research branches of ticket 153, each gated on commit) into build/strata as merge commit 01f76c67, with history, because the history scan found no keys in the branch's commits. The gate on the merge commit passed in 168.3 seconds, under tonight's 180-second limit; the integrator's final gate on the branch passed in 154.5 seconds. The secret scan on build/strata after the merge found no keys. The worktree that built it, `.claude/worktrees/agent-adfa26ba0a813e559`, is removed after this commit. The branch stays.
  - Evidence: tonight's rule from the user (November 5, 18:05 PST) is essentials only, with no review or verify round, so the integrator's report is the evidence. One store and one seed. The demo setting `research.live_sources = false` replays the stored steps under the live labels; the writer has a fallback; the seed writes `sites`, keys notices without the window, and `--all` seeds every sample file. The seed on a fresh state file gives P130164 31 items, P145559 25, P156634 60, P161305 38 and P167814 28. The recorded P156634 writer answer replays with 70 kept and 0 removed. `web/tests/research.spec.ts` and `web/tests/field-photos.spec.ts` ran 15 tests and passed; the brief, photo, tools and benchmark tests ran 106 and passed.
  - Workspace results: none run tonight. Ticket 151's agent runs the six steps under "Tickets 150, 152, 153, 154 and 155, the second deploy of the Prism night" in `docs/workspace-catchup.md`, steps 2, 4 and 6 for the setting, the seed and the check that each brief reports `live_sources` false.
