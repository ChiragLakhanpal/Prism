# 27: A planned date for each STEP step, from the delay model

**What to build:** Delay against the Procurement Plan gets its own model, and the package workspace shows a planned date for every STEP step. A survival model per step, with the plan as the baseline and delay measured from the first published planned date, is trained on the slice's plan rows and backtested through the replay harness. estimate_time also returns a planned date for each step, the cautious one by default, with the comparables behind it and an abstention below 20. Section 2 of the workspace, "Planned date for each step", is collapsed by default with a summary line ("6 steps, from bid invitation to contract signed. Bid evaluation ran longest in N of M.") and opens to the steps, labeled as STEP labels them for the package's method family: goods, works and non-consulting services; consulting firms; or individual consultants. Full STEP names show on hover and focus (for example "Bid Evaluation Report and Recommendation for Award"). Strata fills planned dates only, never actual dates.

Read first: docs/PLAN.md sections 3 (Quirks) and 7; the blueprint's Package workspace wireframe (section 2) and "Words" ("Step labels taken from STEP"); DESIGN.md sections 5 and 7; docs/agents/areas/ml.md.

**Blocked by:** 18 (The document slice, the page router's Route B and the stress shelf); 25 (The replay harness and the survival model's backtests)

**Status:** ready-for-agent
**Area:** ml
**Phase:** P2
**Design review:** yes

- [ ] strata.ops holds per-step backtest results (coverage and error against the plan) for 2021 to 2025, each with its MLflow run id.
- [ ] Delay is measured from the first published planned date: a fixture activity re-dated in a later plan version shows its delay against the earlier date.
- [ ] Section 2's summary line fills its step count and "ran longest" count from the tool, and the section opens and closes by keyboard.
- [ ] Step labels match the blueprint's "Step labels taken from STEP" for each of the three method families, with the full STEP name on hover and focus.
- [ ] Each step's planned date defaults to the cautious choice, names its comparables count, and abstains below 20.
- [ ] No actual date is ever written by Strata into a step.
- [ ] The section follows the Package workspace wireframe and DESIGN.md sections 5 and 7 (rule 17, STEP's words); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
