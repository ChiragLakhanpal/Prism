# 142: The timeline's rating sentence and its bands come from one series, so the last band and the "fell to" rating agree

**What to build:** On October 30, 2026 the demo walkthrough's midnight capture of P161305's Timeline tab (Kenya roads, active) read "Reports disagree on one point, and ISR ratings of progress fell from Satisfactory to Moderately Satisfactory", while the band row under the lane ends with "MU, ISRs 10 to 11" and the lane's last marked report is ISR 12, and the Summary tab rates progress Moderately Satisfactory from ISR 13. The sentence and the bands read different series: the sentence takes `first_rating` and `last_rating` from one set of rating points, the bands are drawn from another (the bands stop at ISR 11, the sentence reaches ISR 13), so the page contradicts itself. The timeline (`src/strata/server/timeline.py`, the `ratings` block built from `get_disagreements`' trajectories, and the bands) must build the sentence and the bands from one series in one place: the same points, the same last rating, and a band row that reaches the last rated ISR the sentence names; where the ISR ratings table (`strata.silver.isr_ratings`) and the assertions hold different last ISRs, the page uses the fuller one and says which ISR the last rating comes from ("last rated in ISR 13"). Tests on the fixture (P161305 or a planted series where the assertions stop before the ratings table) that the sentence's last rating equals the last band's rating and that the band row ends at the ISR the sentence names. The live proof is the orchestrator's: P161305's Timeline tab reads consistently after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds; no design review.

Read first: `src/strata/server/timeline.py` (the ratings sentence, the bands, `isr_marks`), `src/strata/tools/get_disagreements.py` (`trajectories`), `src/strata/server/sql/timeline/reports.sql`, the recorded timeline fixtures under `tests/fixtures/api/`.

**Blocked by:** None (can start immediately)

**Status:** done
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The rating sentence and the band row are built from one series in one place; the sentence's last rating equals the last band's rating, and the band row ends at the ISR the sentence names (tests on the fixture and a planted series).
- [ ] Where two sources hold different last ISRs, the page uses the fuller one and names the ISR the last rating comes from (a test).
- [ ] On the paid workspace, P161305's Timeline tab reads consistently after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 30, 2026, orchestrator: opened at 03:08 PDT from the walkthrough's midnight capture.
- October 30, 2026, merger: merged into build/strata as ad9f5af6 (merge with history; branch `strata/142-the-timeline-s-rating-sentence-and-its-bands-come-from-one-series` at 90935835, kept). The history scan found no keys. The merge gate passed in 146.3 seconds on the orchestrator's quiet-window script's first try: the script waited from 03:47 to 03:55 PDT for another gate to finish, and the commit landed at 03:58 PDT. The by-hand gate on build/strata afterwards passed in 134.4 seconds, from 03:58:26 to 04:00:41 PDT, at ad9f5af6, with no other gate, test run or headless browser running when it started; the secret and history scan took 3.7 s, so the history scan has read the merged history (limit 150 s). Built in the worktree `.claude/worktrees/wf_5e8cdd03-161-1`, now removed. Review round 1 approved with 0 blocking and 4 follow-ups (`.notes/142-review.md`); verify round 1 passed (`.notes/142-verify.md`).

  Evidence from the verify notes:
  - Criterion 1 passes. `timeline.series()` builds one series, and `_bands()` reads the title's first rating, last rating and `last_sequence` off the band row it just built; the band's drawer (`read_ratings`) calls the same `series()`. On the fixture, P130164 as of 2026-10-23 gives the bands (1, 9) S, (10, 11) MS, (12, 13) MU and the title "...fell from Satisfactory to Moderately Unsatisfactory, last rated in ISR 13.", with source `strata.gold.assertion`. With ISR 13's assertion deleted, the bands still end at (12, 13) and the source is `strata.silver.isr_ratings`. `tests/test_timeline_series.py`'s 3 tests all fail on build/strata's code. A sweep of 78 timeline requests over 7 databases, 15 as-of dates and both views found 0 cases where the title and the bands disagree. The planted case where the last ISR changes the rating (P161305's shape) ends (12, 12) MU, (13, 13) MS and reads "fell from Satisfactory to Moderately Satisfactory, last rated in ISR 13".
  - Criterion 2 passes. When the assertions stop early, the page reads the table; when the table stops early, it reads the assertions; on a tie the assertions win; a "--" rating is no point. The 7 recorded timeline answers changed only by the title's new clause and the three new `ratings` fields.
  - Probes: no answer cites a document before its public date (0 hits over 78 answers); the refusal and benchmark tests pass; ISR 13's and ISR 12's dates and ratings, and the band counts, match the recorded ISR text and the benchmark's `trajectory_runs`. The ticket changes no table. The ticket's own tests (62) take about 4 seconds; the builder's gate was 135.8 s and the verifier's 138.5 s.

  Workspace results: none run. Every key is set, but mergers run no workspace step. One step is parked in `docs/workspace-catchup.md` under "Ticket 142, step 1 of 1", for the second session (strata-58) or the orchestrator to run from a snapshot at or after ad9f5af6: a read-only SQL check that no ISR is listed twice for P161305 in `strata.silver.isr_ratings`, the App redeploy with `--keep-secrets`, then P161305's Timeline tab at 1440 px, its `ratings` block and its Summary tab (criterion 3).

  Decisions parked for the user (from the review and the verifier):
  1. The task named `docs/agents/areas/server.md` as the area brief, but no such file exists. The review and the verifier used `docs/agents/areas/app.md`, which covers the FastAPI service. Either add a server brief or point server tickets at app.md.
  2. Follow-up F1 stays a follow-up, not a block, because neither the fixture nor any known record lists an ISR twice. If the live check of P161305 finds one, F1 lands before criterion 3 is recorded as passed.

  Follow-ups for the PM (none blocking):
  1. F1, the most important: an ISR listed twice in `strata.silver.isr_ratings` wins the "fuller" test and is counted twice. On a planted copy the alt text says "over 14 ISRs" for P130164, which has 13 (a wrong count, CLAUDE.md rule 1). Fix: keep one point per sequence in `_table_points`, count distinct ISRs in `_fullness`, and add a third planted case to `tests/test_timeline_series.py`.
  2. F2: a rating read only from the table cites `doc:<document_id>`, whose document view lists only asserted ratings, so a reader who opens it cannot find the rating. Fix: carry `pdf_page` from `isr_ratings.sql` onto each point and link the drawer row to that page.
  3. F3: the agent's `get_disagreements` trajectories still stop at the last assertion, so on P161305 the agent ends at ISR 12 while the page says ISR 13 (CLAUDE.md rule 4). Fix: move the series choice into `strata/tools` and have the timeline call it, with get_disagreements' benchmark question updated in the same change.
  4. F4: naming in `timeline()`: `held` names the rating series and then the contracts, and `_bands`' parameter `found` holds a series. Rename both to `rating_series`.

  Deferred to the design pass:
  - The last band's minimum width, so its rating code shows when it holds one ISR (`bandEdges`, `web/src/lib/timeline.ts`).
  - The title placeholder's four lines below a 440 px card (`TimelineTab.tsx`, `titleLines`).
  - The wording of the "same" clause, "were Satisfactory at the first ISR and at the last, ISR 7".
  - Whether ISR 13 gets a lane mark of its own: on the capture, the Operations lane's last ISR mark is ISR 12 while the title names ISR 13 (the band row reaches ISR 13, so the criterion holds).
