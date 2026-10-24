# 25: The replay harness and the survival model's backtests

**What to build:** The replay harness (seam 5) and the time estimate's model, backtested the way PLAN.md section 7 requires. The harness takes a cutoff date and a scorer, builds every input as of the cutoff (ADR 0002), runs, scores against outcomes that became public later, and writes results to strata.ops evaluation results and MLflow; later tickets plug in retrieval evaluation and the hindsight test as further scorers. The model is XGBoost survival (accelerated failure time) on procurement cycle time, with features taken as of the moment a package was planned or advertised (method, category, market approach, review type, size, region and country, governance indicators lagged as published, the implementing agency's history, the plan's own planned duration) and conformal ranges for the middle half and 8 in 10. Leakage is kept out by the as-of filter: no signed amounts, no ICR from the same project, no revised dates, no later ratings. Rolling backtests train before each date and test on the next 12 months, for 2021 to 2025, and record coverage of the 8-in-10 range, interval width, and error against the past range and against the borrower's own plan. The model card lives in MLflow; the model is registered in Unity Catalog with a champion alias; below 20 comparables, subgroups included, it abstains. The track-record sentence is generated from the stored results.

Read first: docs/PLAN.md sections 7 and 10; ADR 0002; the blueprint's "What Strata estimates, and what it refuses to" and "A track record, not a confidence score"; docs/agents/areas/ml.md.

**Blocked by:** 12 (Comparables and the past range, on the package workspace); 17 (Every structured source, for every country, kept as published)

**Status:** in-progress
**Area:** ml
**Phase:** P2
**Design review:** no

- [ ] On fixture data with known answers, the harness returns the expected scores, and a feature injected with a public date after the cutoff is never used.
- [ ] Backtests for 2021 to 2025 run on the workspace, and strata.ops holds, per test year, the 8-in-10 coverage, interval width, and error against the past range and against the borrower's plan, each with its MLflow run id.
- [ ] Coverage of the 8-in-10 range falls within 75–85% in each test year, or the shortfall and its likely cause are written into the model card.
- [ ] The model is registered in Unity Catalog with a champion alias, and its model card lists the data, the features, the leakage exclusions, the backtest results and the abstention rule.
- [ ] The track-record sentence for the latest test year ("Of N packages from YEAR that Strata had not seen, M finished inside its 8-in-10 range") is filled from stored results, never typed.
- [ ] A package with fewer than 20 comparables, or in a subgroup with fewer than 20, gets an abstention instead of a range.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/25-replay-harness-and-survival-backtests, as soon as ticket 12 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
