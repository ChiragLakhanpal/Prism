# 155: The verifier keeps the brief's questions and bottom line when their facts hold, quotes dates that live in an item's words, and judges "could not see" against the run's coverage

**What to build:** The first live brief on the workspace (P156634, November 6, 2026, 04:03 UTC; the stream is saved in the orchestrator's scratchpad `ops-151/research-P156634-20261106T040308Z.sse`) wrote 74 sentences; the checks kept 56 and removed 18, and the bottom line and the questions came back empty. The reasons, from the stream:

1. Ten sentences of the `bottom_line` and `questions` sections were removed by check 4 with `not_supported`: the judge read them as advice the sources do not state ("asking for justification, approval chain, and explanation is advice not contained in the sources"). A question to take to the agencies and a bottom-line item are Prism's own by design (the sample brief's pages 1 and 8); what must hold is every fact inside them. Fix: for sentences in those two sections (kind `advice`), the judge is asked only whether every fact the sentence states, its dates, counts, names and events, follows from its cited items, and told in plain words that the question or the recommendation itself is Prism's and is not to be judged; check 5 (a lesson or comparable behind advice) does not apply to them, since `research_evidence` backs advice. A question whose facts do not hold is still removed with the judge's reason.
2. Seven `developments` sentences were removed by check 1 (`date_not_in_records`, `number_not_in_records`) for dates and a number that live inside a notice's or an article's text (submission and award dates such as "June 22, 2026", a count written in a sentence) rather than in a field. Fix, both halves: the notices reader (`src/strata/research/sources/procurement_notices.py` or wherever ticket 147 put it) exposes the notice record's own dates as fields (`notice_date`, `submission_date`, and the award's signing date when the record carries it), and the writer's instruction says that a date or number found only in an item's words must be quoted word for word in the sentence, which the verifier accepts, or left out.
3. One `could_not_see` sentence was judged against an article and removed. Fix: the run's coverage notes (each source's `reached`, `status` and `note`, and each item's "page could not be read, headline only" note) become citable records of the turn, `strata.research.coverage:<run id>/<source key>`, so `could_not_see` sentences cite them, and the writer's instruction says so.

Then re-run the offline seeded P156634 brief through the recorded writer answer (`tests/fixtures/agent/research/P156634.json`; extend the recorded judge answers if the judge is now asked differently) and show that the sections keep their sentences; add a test with a planted question whose fact is wrong (removed) and one whose facts hold (kept), a planted development with a submission date now matched as a field, and a `could_not_see` sentence citing a coverage record (kept). Keep the gate under 180 seconds.

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD. Ticket 152 is changing the stream in `src/strata/server/research.py` in parallel; keep your changes to the verifier's instructions (`src/strata/agent/judge.py` or the research-specific judge call), `answer_check.py` where the brief's sections are handled, the notices reader, the coverage records in the run, and the writer's instruction; merge build/strata into your branch before your final gate if 152 has landed. Essentials only. Commit with plain-English messages and no trailers. Do not change ticket files, docs/STATUS.md or anything under .scratch. Report within 75 minutes: branch and worktree, each fix with its test, the offline brief's kept and removed counts before and after, the gate's time, and the workspace steps (the App needs a redeploy; the P156634 brief must be written again on the workspace after it).

**Blocked by:** None (can start immediately; merges after 152)

**Status:** in-progress
**Area:** agent
**Phase:** P5
**Design review:** no

- [ ] A question or bottom-line item whose facts hold is kept, and one whose fact is wrong is removed with the judge's reason (tests).
- [ ] A development citing a notice's submission date is kept because the date is a field, and a date that lives only in an item's words is quoted by the writer (tests and the instruction).
- [ ] A `could_not_see` sentence citing the run's coverage record is kept (tests).
- [ ] The gate passes under 180 seconds on the worktree.

## Comments

- November 5, 2026, orchestrator: opened at 21:12 PST from the first live brief on the workspace.
