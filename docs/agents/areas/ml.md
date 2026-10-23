# Area brief: ml

Tickets with `Area: ml` build the past range, the time estimate, rebidding risk, the signals' track record and the hindsight test.

Read: `docs/PLAN.md` sections 7, 10 and 11, and the blueprint's "Estimates" and "Design rationale" sections (`docs/blueprint/strata-blueprint.html`).

- The past range is Kaplan-Meier over comparables, with packages still open kept as censored.
- The time estimate is XGBoost AFT with conformal ranges, backtested on rolling origins for 2021 to 2025, and shown as a track record.
- Features are taken as of the moment a package was planned or advertised. PLAN.md section 7 lists the leakage traps.
- Fewer than 20 comparables, subgroups included, means no range: Strata shows the cases instead.
- What-if combinations are precomputed so the chart answers within 100 ms.
- Models live in Unity Catalog with champion and challenger aliases; a challenger must win the backtest and a quarter in shadow.
