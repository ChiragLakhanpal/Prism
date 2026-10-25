# 26: The time estimate on screen: lane 2, approach options, what-ifs and the track record

**What to build:** The package workspace shows Strata's time estimate in lane 2 of the range chart, the procurement approach options, fair what-ifs that answer at once, and the time estimate's track record. Batch scoring precomputes the time estimate for every package and every what-if combination (market approach, prequalification, lotting) into a scores table, so the chart answers within 100 ms. The estimate_time tool (one registry entry) returns the ranges, the track record, the reasons the two lanes differ as counts (for example, the package is larger than 30 of its 37 comparables) and the what-if grid. Lane 2 draws a navy bar for the middle half, a thin line to the 8-in-10 point and a white notch at the middle, with a sentence saying why the lanes differ; the plan line and its readout now cross both lanes. "Compare with" toggles (such as Open national, 3 lots, Prequalification) light the matching dots with their count and leave a ghost of the previous estimate, worded "went with", never "caused". Under the chart, the track-record line, and a choice of plan dates ("9 months: half ran longer" or "12 months: 2 in 10 ran longer") with the cautious date as the default. Section 4, "Procurement approach options" (PPSD section 6), lists up to three options with how many comparables went with each and their time estimates, collapsed by default. No option is ever framed as a way to stay under a review threshold.

Read first: docs/PLAN.md section 7; DESIGN.md sections 5 (Range chart), 6 and 7; the blueprint's Package workspace wireframe (section 1 and section 4) and "What-ifs on fair levers only"; docs/agents/areas/ml.md.

**Blocked by:** 15 (Plan a package from a sentence); 25 (The replay harness and the survival model's backtests)

**Status:** in-progress
**Area:** ml
**Phase:** P2
**Design review:** yes

- [ ] On the fixture, estimate_time returns ranges equal to the stored batch scores, and a timed test of every what-if lookup stays within 100 ms.
- [ ] Lane 2 follows DESIGN.md section 5's Range chart and section 6 (navy middle-half bar, thin line to the 8-in-10 point, white notch), as the Package workspace wireframe draws it, and the sentence on why the lanes differ uses the tool's counts.
- [ ] Each "Compare with" toggle lights the matching dots with their count and shows a ghost of the previous estimate; the copy lint finds "went with" and never "caused", "split" or "splitting" on this screen.
- [ ] The what-if set contains no option whose only effect is to move a package below a review threshold.
- [ ] The track-record line shows numbers from the backtest results in strata.ops, and the plan-date choice defaults to the cautious date.
- [ ] Section 4 lists up to three approach options with "N of M" counts from find_comparables and opens on demand.
- [ ] With fewer than 20 comparables, lane 2 shows the first-person abstention and no bar.
- [ ] Toggles are a segmented control at least 32px tall and keyboard operable, the chart's alt text updates with its statistics, motion stops under reduced-motion, states are captured at 1440, 1024 and 390 px, and axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/26-time-estimate-on-screen, as soon as ticket 25 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
