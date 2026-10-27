# 49: The change drills and the full rehearsal

**What to build:** The ten likely change requests from PLAN.md section 15 each land in under ten minutes with the gate green, and the specialist's path runs end to end on the deployed app. For each drill (add a data source; add a tool; change a signal threshold; add a country to the slice; swap the model; reorder the evidence ladder; add a field to the package form; reword copy; add a benchmark or must-refuse question; add a dashboard tile), write a runbook entry naming the single place it lives, the steps, and the test that proves it, then rehearse it on a throwaway branch with a timer and record the time. Then run the demo-ready command and walk the blueprint's "A specialist's path" on the deployed app: Home, Check a plan, the package workspace, the evidence drawer, the project timeline, Drafts, Following and Lessons. Record timings and anything that fails; each failure becomes a ticket or a "designed, not built" line.

Read first: docs/PLAN.md sections 13 (P4) and 15; the blueprint's "A specialist's path" and "From an empty repo to a rehearsed demo"; the spec's "Ten single places"; docs/agents/areas/ops.md.

**Blocked by:** 45 (All three dashboard pages and the KPIs); 47 (The deck at /present, and How Strata works); 48 (The demo-ready command)

**Status:** done
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
- October 26, 2026, merger: merged strata/49-change-drills-and-rehearsal (head 6454cec6) into build/strata as merge commit 5d923cbc, with history, since the history scan found no key-shaped line in the branch's commits. Its parents are 8362d875 and 6454cec6. The worktree that built it was `.claude/worktrees/wf_b78fa5cb-ded-61`. I removed it and kept the branch. No dependency file changed, and `scripts/install` ran before the merge commit. The merge commit's gate passed in 125.0 seconds. The gate run by hand on build/strata, with its history scan over the merged history, passed in 124.8 seconds at 12:14 PDT.
  - Evidence. Review round 2 (`.notes/49-review-r2.md`) approved with 0 blocking findings. Verify round 2 (`.notes/49-verify-r2.md`) passed, and the worktree's gate passed in 132.6 seconds. Criterion 1 passed: `docs/change-drill.md` has ten entries in `config/change_drills.toml`'s order. Each one names its one place, its proving test and its workspace line, and every named test passed when run by name. Criterion 2 passed: each drill was rehearsed on its own `drill-49/` branch and took 3 to 4 minutes with the gate green. The edits took 6 to 55 seconds and the gates 121.0 to 131.8 seconds. The verifier checked every time against git's commit dates and reflog, not against the record. Criterion 3 passed: none of the ten drill commits is on build/strata, HEAD or `main` (`git merge-base --is-ancestor` and `git cherry`), and no drill's content is on either branch. The rendered proposal shows the measured times in Module 4 and Annex 1. Paragraph 56 says each change had been worked through once before its timed run, and it no longer says "under ten minutes" or "Not rehearsed yet". The number check now reads ten and up, with a test. This settles the P3 phase gate's finding in the comment above.
  - Criteria 4 and 5 are parked. They need the workspace and a person signed in to the App.
  - Workspace results: none ran. Every key is set, but the second session runs every workspace step from a snapshot of the commit, so the merger ran none. Three blocks are parked in `docs/workspace-catchup.md` for a snapshot of 5d923cbc or later:
    1. "Ticket 49, step 1 of 3" runs the demo-ready command twice (criterion 4). The second session runs it. It cannot pass while `strata.gold.passage` holds 0 rows, so it waits on ticket 72's documents run.
    2. "Ticket 49, step 2 of 3" walks the specialist's eight steps with timings into `docs/rehearsal.md` section 2 (criterion 5). It needs the user signed in as the test account. Ask answers 401 until the user assigns the App's role.
    3. "Ticket 49, step 3 of 3" is each drill's live part. It is optional, no criterion needs it, and it waits for the user's go-ahead, because it would put a drill's change on the workspace the demo runs on.
  - Follow-ups (none blocks this ticket):
    1. A plan with a `method_unknown` data note makes check_plan answer HTTP 500 (review round 1's F3, carried). It needs a check_plan ticket of its own. The fix is in `.notes/49-review-r2.md`, follow-up 1.
    2. Add the as-of June 30, 2017 behaviour test to `tests/test_project_signals.py`, plus one runbook line under "A new signal" (review follow-up 2). The verifier's probe shows it passes today.
    3. The two git-backed rehearsal tests skip any commit this clone does not hold, and the drill branches exist only in this local repo (verify follow-up 3). Keep the ten `drill-49/*` branches, and never delete them as cleanup.
  - Decisions parked for the user:
    1. Time the drills again from a cold start? The reviewer and verifier kept the current times. The proposal says plainly that they measure a known change made again, plus the gate.
    2. Push the ten `drill-49/*` branches, or one tag per drill commit, so a reader can open the commits Annex 1 cites? They stay local and are not deleted. Pushing waits for your go-ahead (CLAUDE.md rule 10).
    3. Run each drill's live part on the shared workspace (catch-up step 3 of 3)? I parked it as optional and ran nothing, because the demo runs on that workspace.
  - Deferred to the design pass: nothing. This ticket changes no screen.
- October 27, 2026, orchestrator (03:26 PDT): step 1 ran twice after ticket 86's live step; both runs exit 1 (the app, the smoke question and Home fail; Genie, the recheck and the listing pass; the second run prints No changes). The catch-up block "Ticket 49, step 1 of 3 ran twice" names the three causes: day-one test 6's chosen path (the user re-runs the probe), the smoke question's quote_not_on_page removal (to diagnose in the App), and the seed command's two user items.
