# 28: Rebidding risk, labeled experimental

**What to build:** For a package being planned, Strata shows how many comparable packages were advertised again and why, labeled experimental. Labels come from three places: notices with no award, notices re-advertised under the same STEP reference, and canceled plan rows. Calibrated gradient boosting is compared with logistic regression through the replay harness (calibration and Brier score per test year) and the better-calibrated model becomes champion; both stay labeled experimental. The rebidding_risk tool (one registry entry) returns the count of comparables advertised again with the reasons quoted from award notices (for example all bids rejected) and their notice ids, and adds a natural frequency from the model ("about 2 in 10") only when there are at least 20 comparables and the model beat the baseline in its backtest. On the workspace it appears under section 1 as a line such as "Advertised again: 6 of 37 comparable packages", with the reasons expandable and cited, and an "Experimental" label that explains itself in text.

Read first: docs/PLAN.md section 7; the blueprint's "What Strata estimates, and what it refuses to" (rebidding row: "Shown as") and Package workspace wireframe; DESIGN.md section 7 (rules 6 and 15); docs/agents/areas/ml.md.

**Blocked by:** 15 (Plan a package from a sentence); 25 (The replay harness and the survival model's backtests)

**Status:** in-progress
**Area:** ml
**Phase:** P2
**Design review:** yes

- [ ] strata.ops records the label counts from each of the three sources.
- [ ] Backtests for both models record calibration and Brier score per test year, and the champion is the better-calibrated model on those results.
- [ ] On the fixture, rebidding_risk returns "N of M were advertised again" with each reason quoted from an award notice and its notice id, matching a direct count.
- [ ] The natural frequency appears only with at least 20 comparables and a model that beat the baseline; otherwise only counts appear.
- [ ] The workspace line and its reasons follow the blueprint's "Shown as" wording, cite their notices through the evidence drawer, and carry an "Experimental" label with a one-sentence explanation from the copy file.
- [ ] States (populated, under 20 comparables, no rebidding found) are captured at 1440, 1024 and 390 px, follow DESIGN.md sections 5 and 7, and pass axe.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/28-rebidding-risk-experimental, as soon as ticket 25 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
