# 12: Comparables and the past range, on the package workspace

**What to build:** From any STEP row, a specialist opens the package workspace and sees how comparable packages went: section 1, "How long it took", with lane 1 of the range chart and the plan as a line. The find_comparables tool (one registry entry) selects comparables by the stated criteria (method, category, market approach, review type, size band, region and period), defaulting from the package; measures procurement cycle time from the specific procurement notice to the signed contract, from notices joined to awards on the STEP reference; keeps packages still open as censored; and returns the Kaplan-Meier past range (the middle half, the middle, and the point 8 in 10 were signed within), one dot per comparable with its id, months and whether it is still open, and a coverage line. Below 20 comparables, subgroups included, it abstains and returns every comparable. The workspace opens at the packages route from a link on each Check a plan row, with one narrative column and a sticky header. Section 1's title is the finding; lane 1 draws each comparable as a dot (hollow and counted if still open), the middle half as a band and the middle as a tick; the plan is a full-height line with a count readout, draggable by mouse, keyboard and number input, defaulting to the plan row's own months; a "Show the table" twin, alt text that states the statistics, one tab stop with arrow keys between marks, and a coverage line linking to Data readiness filtered to the sources behind it. Above about 60 comparables the lane switches to 20 quantile dots. A dot shows its package reference, months and status on focus or hover; opening it in the evidence drawer comes with ticket 15. Lane 2, the time estimate, comes later.

Read first: docs/PLAN.md section 7; DESIGN.md sections 5 (Range chart, Coverage line), 6 and 7; the blueprint's Package workspace wireframe, its "why" panels and "Showing uncertainty honestly"; docs/agents/areas/ml.md.

**Blocked by:** 07 (Kenya's procurement records, bronze to gold); 10 (Check a plan, on screen, for the NWWDA plan)

**Status:** ready-for-agent
**Area:** ml
**Phase:** P1
**Design review:** yes

- [ ] On the fixture, find_comparables with the default criteria returns the comparables listed in the ground-truth file, with Kaplan-Meier quantiles equal to the literal values stored there (computed once by an independent library), counting open packages as censored.
- [ ] The fixture's narrower criteria variant returns fewer than 20 comparables, no range and no percentage, every comparable, and the copy-file sentence "I'm not giving a range: only N comparable packages. Here are all N." with N filled from the rows.
- [ ] The coverage line's numbers equal a direct count over the fixture.
- [ ] With an as-of date, a package signed after that date comes back as still open.
- [ ] The chart follows DESIGN.md section 5's Range chart and section 6's "Strata's range chart": dots on a month axis, hollow open packages, a grey200 middle-half band with line-strong edges, a 2.5px grey500 middle tick, and the finding as the title.
- [ ] Dragging the plan line, pressing arrow keys on it, or typing a number updates the readout ("N of M signed within P months") from the returned rows; "Show the table" shows the same values; the chart has one tab stop with arrow keys between marks, and Escape closes any tooltip.
- [ ] A fixture variant with more than 60 comparables renders 20 quantile dots.
- [ ] The workspace matches the blueprint's Package workspace wireframe for the sticky header and the section 1 card, with the "Planning" eyebrow; loading, empty, error and abstention states are captured at 1440, 1024 and 390 px; below 768 px the chart leads with its sentence; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: from ticket 05's review. Read a comparable's signing date from the awards dataset or, when it has no row, from its Contract Award notice (KE-GAWASCO-54771-CW-RFB and KE-GAWASCO-111742-CW-RFB are signed only in notices OP00175878 and OP00191645). Read notices and awards from every project, because four still-open comparables come from P176758 and P170941. Decide whether the 3 canceled packages count as still open (4 or 7 hollow points) and keep the choice in one config line.
