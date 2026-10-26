# 49: The change drills and the full rehearsal

**What to build:** The ten likely change requests from PLAN.md section 15 each land in under ten minutes with the gate green, and the specialist's path runs end to end on the deployed app. For each drill (add a data source; add a tool; change a signal threshold; add a country to the slice; swap the model; reorder the evidence ladder; add a field to the package form; reword copy; add a benchmark or must-refuse question; add a dashboard tile), write a runbook entry naming the single place it lives, the steps, and the test that proves it, then rehearse it on a throwaway branch with a timer and record the time. Then run the demo-ready command and walk the blueprint's "A specialist's path" on the deployed app: Home, Check a plan, the package workspace, the evidence drawer, the project timeline, Drafts, Following and Lessons. Record timings and anything that fails; each failure becomes a ticket or a "designed, not built" line.

Read first: docs/PLAN.md sections 13 (P4) and 15; the blueprint's "A specialist's path" and "From an empty repo to a rehearsed demo"; the spec's "Ten single places"; docs/agents/areas/ops.md.

**Blocked by:** 45 (All three dashboard pages and the KPIs); 47 (The deck at /present, and How Strata works); 48 (The demo-ready command)

**Status:** in-progress
**Area:** ops
**Phase:** P4
**Design review:** no

- [ ] Each of the ten drills has a runbook entry that names its single place and its proving test.
- [ ] Each drill was rehearsed, timed under ten minutes, and finished with the gate green; the times are recorded. This is P4's exit criterion.
- [ ] No drill leaves a change on the integration branch.
- [ ] The demo-ready command ran and passed before the rehearsal.
- [ ] All eight steps of the specialist's path ran on the deployed app with timings recorded, and every step either worked or has a recorded follow-up ticket or "designed, not built" line.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/49-change-drills-and-rehearsal, as soon as ticket 47 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
- October 26, 2026, merger, for the change drill notes (from ticket 47's builder and its round 2 review): the deck at `/present` reads its numbers and addresses from a built file. A change to any of the inputs below means rebuilding both deck files in the same change, with `uv run python -m strata.proposal deck` and `uv run --frozen python tests/record_deck_api.py`. The proof is that `tests/test_deck_data.py` passes; its committed-file test catches each input.
  - `config/urls.toml`, `config/deck.toml`, `config/rubric.toml` and `config/designed_not_built.toml`
  - `config/slice.toml`'s `[demo_plan]` and `[showcase]`
  - `config/sources.toml`'s `awards` known gap `fy2017_2019`
  - any setting the deck reads through `docs/proposal/settings.toml`, such as `hindsight.checklist_size` in `config/thresholds.toml`
- October 26, 2026, orchestrator: the P3 phase gate (run after ticket 47 merged, 10:10 PDT) failed on one finding that this ticket settles: `docs/proposal/source.md` lines 272 and 274 say a change lands "in under ten minutes" (the Module 4 heading and paragraph 56), but nothing has measured it, the drill table under it says "Not rehearsed yet" for all ten changes, and the number check in `src/strata/proposal/numbers.py` line 65 counts only the words two to nine, so it never saw the claim. When the drills run, cite their measured times there, take the number out of the heading unless the measurement supports it, and add ten and up to the number check's word list with a test. Everything else in the P3 gate passed (offline 129.1 s; 46 and 47 done; probes held). The gate runs again in the next wave.
