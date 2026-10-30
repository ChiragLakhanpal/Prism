# 136: The timeline tells one disagreement per fact: rows that share the rule, the attribute and the earlier report are one line with a count

**What to build:** On October 29, 2026 at about 20:10 PDT, after the assertions pass ran for the demo projects, the Timeline tab of P130164 (India, Rajasthan roads, closed) read "60 pairs of reports disagree" and drew 60 "2 reports disagree" pills with dashed lines from the PAD to every ISR, on top of one another, so the chart cannot be read. The 60 rows of `strata.gold.disagreement` for the project are 44 `moment`/`overall_risk` pairs (the PAD's overall risk, read twice from one page as two table cells, `strata.gold.passage:18381488/v1/table65.1` and `.../table65b.1`, against each ISR's overall risk), 11 `outcome`/`pdo_progress` pairs and 5 `tieSpecific`/`overall_risk` pairs: three facts told 60 times. Make the timeline and the tool tell each fact once: (1) in `src/strata/tools/get_disagreements.py`, rows that share the rule, the attribute and the earlier side's document are one disagreement group with its count and the later sides listed (the tool's rows keep every pair for the table, and the summary counts groups: "3 disagreements over 60 report pairs"); the benchmark question for the tool is updated in the same change (rule 4); (2) in `src/strata/server/timeline.py` and `web/src/components/Timeline*`, one dashed line and one pill per group, the pill naming the fact and the count ("Overall risk: the PAD and 13 ISRs disagree"), and the finding sentence counting groups; the table lists every pair; (3) in the assertions pass (`src/strata/knowledge/assertions.py`), two assertions read from one page that name the same subject, attribute, period and value are one assertion (the PAD's two table cells), with a test on the fixture. Prove it on the fixture (P130164 has these rows in the fixture too, fewer) with tests that count groups and lines, and the live proof is the orchestrator's: the P130164 Timeline tab reads with one line per fact after the redeploy, recorded in the catch-up file. Reviews block only on wrong facts, failed criteria, crashes or unreachable content; keep the gate under 150 seconds.

Read first: `src/strata/tools/get_disagreements.py` (the rows, `trajectories`, the summary), `src/strata/server/timeline.py` (the disagreement lines and the finding), the timeline components and their specs under `web/`, `src/strata/knowledge/assertions.py` (where a page's table cells become assertions), `evals/benchmark.yaml` (the tool's question), DESIGN.md's Timeline row.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The tool groups pairs that share the rule, the attribute and the earlier side's document, with the count and the later sides, and its summary counts groups; its benchmark question is updated in the same change (tests on the fixture).
- [ ] The timeline draws one line and one pill per group, naming the fact and the count, with every pair in the table and the finding counting groups (specs at 1440 and 390 px; no pills overlap on the fixture's P130164).
- [ ] Two assertions read from one page with the same subject, attribute, period and value are one assertion (a test), and on the paid workspace the P130164 Timeline tab reads with one line per fact (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 20:24 PDT from the recaptured India roads timeline.
