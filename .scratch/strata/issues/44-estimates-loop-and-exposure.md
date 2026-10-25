# 44: Exposure logging, the estimates loop and the hazard model in shadow

**What to build:** Strata measures its own influence on the plans it informs, watches its models for drift, and changes them only when a challenger has earned it. Whenever a past range or time estimate is shown for a package with a STEP reference, an exposure is logged (the STEP reference, the range shown, the option chosen, viewer and date). Later plan rows within 14 days of Strata's value are marked as anchored, and plan accuracy and duration are reported separately for anchored and other plans, and for onboarded countries against those not yet onboarded. Projects exposed to Strata are left out of the recall KPI. A monthly watch tracks rolling coverage of the 8-in-10 range, error against the past range and the input mix, and raises a retrain when coverage leaves 75–85% for two months, error trails the past range by more than 10%, the input mix drifts, or a new Regulations edition takes effect (which first marks affected lessons and models as being re-checked). A quarterly retrain produces a challenger that must win the backtest and a quarter in shadow, hold coverage for each Regulations edition, and carry a sign-off from the model owner and the lead before it becomes champion. The discrete-time hazard model for project delay early warning scores in shadow beside the fixed signals and is never shown until it beats them on the replay harness's hindsight comparison.

Read first: docs/PLAN.md sections 7 and 11 ("Loops through the world", Retraining); the blueprint's "Three loops, one dated store"; docs/agents/areas/ml.md.

**Blocked by:** 26 (The time estimate on screen); 34 (The hindsight test); 37 (Following, project signals and the mission brief)

**Status:** in-progress
**Area:** ml
**Phase:** P2
**Design review:** no

- [ ] Through the answer contract, showing a range for a package with a STEP reference writes one exposure row with the range shown and the option chosen.
- [ ] Of two fixture plan rows, the one within 14 days of the shown value is marked anchored and the other is not.
- [ ] strata.ops reports plan accuracy and duration separately for anchored and other plans, and for onboarded and not-yet-onboarded countries.
- [ ] The recall KPI query leaves out every exposed project.
- [ ] Each retrain trigger fires on a seeded series: coverage outside 75–85% for two months, error trailing the past range by more than 10%, input-mix drift, and a new Regulations edition marking lessons and models as being re-checked.
- [ ] Promotion is refused without a backtest win, a shadow-quarter win, per-edition coverage and a sign-off from both roles; with all four it succeeds and moves the champion alias.
- [ ] The hazard model's shadow scores are stored nightly with its comparison against the fixed signals, and no screen shows them.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/44-estimates-loop-and-exposure, as soon as ticket 26 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
