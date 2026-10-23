# 37: Following, project signals and the mission brief

**What to build:** World Bank staff follow projects and see, for each, a status, the signals behind it and one next action; a task team leader turns that into a mission brief. Following lives under the Projects tab for World Bank staff, with follow and unfollow on the project page saved per viewer. The project_signals tool (one registry entry) runs fixed checks from the thresholds file on public records: activities past their planned completion with no signed contract, actual amounts far above estimates, a direct-selection activity first appearing late in a plan, closing-date moves from the loan history, restructurings, ISR rating downgrades and disbursement lag. "Needs a look" means three signals or one strong one, as the column header says. Each signal is one past-tense line with its counts. Each signal rule's track record comes from the replay harness (how many projects with that many signals later extended their closing date, against those with none). Projects with no signals fold away with a count, and the page states what Strata cannot see. "Add to mission brief" starts the mission brief writer, which drafts the latest plan per implementing agency, awards since the last ISR, the rating history, disbursement and a closing check, with citations, the usual draft states and bar, and Word export.

Read first: docs/PLAN.md sections 7 (Project delay early warning) and 11; the blueprint's Following wireframe and its "why" panels, and "Signals, not scores"; DESIGN.md sections 5 (Following row, Status badge) and 7; docs/agents/areas/app.md.

**Blocked by:** 17 (Every structured source, for every country, kept as published); 21 (The project page as the hub); 35 (Drafts: the runtime, the draft bar and review notes on a plan)

**Status:** ready-for-agent
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] P156634's row shows Needs a look with the four real signals from the Following wireframe: KE-NWWDA-541055-CW-RFB passed its planned completion (July 31, 2026) with no signed contract; KE-NWWDA-229129-CW-RFB was signed at about 4 times its estimate; KE-CWSB-567630-CW-DIR, a US$2.6 million direct-selection works activity, first appears in the August 17, 2026 plan; the closing date has moved three times since 2022.
- [ ] The Status column header reads "Status: needs a look means three signals or one strong one; a signal is a reason to look, not a finding".
- [ ] Changing a signal threshold in the thresholds file changes a fixture project's status with no code change.
- [ ] The track-record note is filled from the replay harness's stored results, never typed.
- [ ] Follows persist per viewer, and the Following route refuses viewers without the World Bank staff role.
- [ ] "Add to mission brief" creates a mission brief draft with its five parts, numbers from tools and citations, that moves through the draft states and exports to Word.
- [ ] The page follows the Following wireframe and DESIGN.md section 5 (status first, project as a link, P-code in mono, closing date, one action per row) and section 7 (Needs a look, Watch, No signals; never "at risk", "flag" or "watchlist"); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
