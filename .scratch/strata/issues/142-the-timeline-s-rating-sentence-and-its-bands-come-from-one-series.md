# 142: The timeline's rating sentence and its bands come from one series, so the last band and the "fell to" rating agree

**What to build:** On October 30, 2026 the demo walkthrough's midnight capture of P161305's Timeline tab (Kenya roads, active) read "Reports disagree on one point, and ISR ratings of progress fell from Satisfactory to Moderately Satisfactory", while the band row under the lane ends with "MU, ISRs 10 to 11" and the lane's last marked report is ISR 12, and the Summary tab rates progress Moderately Satisfactory from ISR 13. The sentence and the bands read different series: the sentence takes `first_rating` and `last_rating` from one set of rating points, the bands are drawn from another (the bands stop at ISR 11, the sentence reaches ISR 13), so the page contradicts itself. The timeline (`src/strata/server/timeline.py`, the `ratings` block built from `get_disagreements`' trajectories, and the bands) must build the sentence and the bands from one series in one place: the same points, the same last rating, and a band row that reaches the last rated ISR the sentence names; where the ISR ratings table (`strata.silver.isr_ratings`) and the assertions hold different last ISRs, the page uses the fuller one and says which ISR the last rating comes from ("last rated in ISR 13"). Tests on the fixture (P161305 or a planted series where the assertions stop before the ratings table) that the sentence's last rating equals the last band's rating and that the band row ends at the ISR the sentence names. The live proof is the orchestrator's: P161305's Timeline tab reads consistently after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds; no design review.

Read first: `src/strata/server/timeline.py` (the ratings sentence, the bands, `isr_marks`), `src/strata/tools/get_disagreements.py` (`trajectories`), `src/strata/server/sql/timeline/reports.sql`, the recorded timeline fixtures under `tests/fixtures/api/`.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The rating sentence and the band row are built from one series in one place; the sentence's last rating equals the last band's rating, and the band row ends at the ISR the sentence names (tests on the fixture and a planted series).
- [ ] Where two sources hold different last ISRs, the page uses the fuller one and names the ISR the last rating comes from (a test).
- [ ] On the paid workspace, P161305's Timeline tab reads consistently after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 30, 2026, orchestrator: opened at 03:08 PDT from the walkthrough's midnight capture.
