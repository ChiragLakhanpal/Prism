# 115: The package's steps as a horizontal tracker, each step marked done, next, planned, late or unknown

**What to build:** On the package page, section 2 ("Planned date for each step") lists the six steps from the bid invitation to the contract's completion, each with its planned date from the plan row and, where STEP's records give it, the date it happened; today the list sits behind "Show the steps". Draw it as a horizontal tracker at the top of the package workspace, the pattern of a delivery tracker the user asked for on October 27, 2026: six nodes joined by one line, each with the step's name and its date, and each marked in words and in form as done (a tick and the actual date), next (the current step, filled), planned (an outline with the planned date), late (the planned date passed with no actual date; the status color and "late by N days") or unknown (no date; a dotted node). Every date and the late count come from the server's steps payload (add `state` and `late_days` as columns of the steps API, computed in src/strata/server from the records and the as-of date; the browser computes nothing, rule 1). For screen readers the tracker is a list, one item per step with its state in words; keyboard focus moves along the nodes; under reduced motion nothing moves, otherwise the next node's fill enters in 160 ms (the plan's section 5.7). Tokens only; every string in web/src/copy.ts; section 2's list stays available under "Show the steps". Prove it on the fixture: the showcase package KE-NWWDA-541055-CW-RFB (its planned completion of July 31, 2026 passed with no signed contract, so that step is late) and a package with no dates, in a screen test for the five states, a gallery state, and axe.

Read first: `docs/design/redesign-2026-10/plan.md` section 5.7 and 8.0 (the package workspace), `web/src/components/StepsSection.tsx` and `Steps.tsx` (section 2 today), the steps route in `src/strata/server` and its test, `web/src/copy.ts` (the step names), `DESIGN.md` (tokens, the status colors, the motion rules), `.notes/skills/emil/find-animation-opportunities.SKILL.md`.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The tracker shows the six steps with their names and dates from the steps API, and marks each state (done, next, planned, late, unknown) in words and in form, on the fixture's showcase package and on a package with no dates.
- [ ] `state` and `late_days` come from the server's steps payload, with a Python test; the browser does no date arithmetic.
- [ ] The tracker is a list for screen readers, its nodes take keyboard focus, and nothing moves under reduced motion; the gallery holds the five states and axe passes.
- [ ] Section 2's list stays under "Show the steps", and the gate adds at most one second.

## Comments

- October 27, 2026, orchestrator: opened at 13:42 PDT from the user's question of the same minute ("wouldn't a simple tracker, like a food delivery app's, with each step marked, be helpful?"), as a visual aid on the demo's package page; it builds in the polish wave after 110.
