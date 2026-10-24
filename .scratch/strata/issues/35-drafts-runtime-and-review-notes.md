# 35: Drafts: the runtime, the draft bar and review notes on a plan

**What to build:** A World Bank procurement specialist turns a plan check into review notes in one action, checks them, and exports them, and nothing leaves without that person. On Check a plan, the sticky header gains the primary action "Draft review notes (N rows)", with N the marked rows. The check-a-plan workflow's writer drafts one note per marked row from the check's evidence, and the draft passes the six checks. The draft runtime, adapted from fairshare's, stores drafts in strata.ops with their author's team and moves them from Draft to Checked by you to Exported only when the person acts; Discard is set apart and undoable. The draft bar sits at the bottom of the document column: on the left, what exporting does and is not, and "You opened N of M sources" from the citations recorded in the evidence drawer; on the right, Mark as checked (primary) and Export to Word (secondary). Export writes a Word file with sources as footnotes and an evidence pack (PDF and CSV) listing every source, whether the person opened it, and any reason given for keeping a source Strata did not lean on. The page ends on a success state naming what was saved. The Drafts tab lists the team's drafts under To check, Checked and Exported. Strata sends nothing itself.

Read first: docs/PLAN.md sections 6 and 8 (Exports); the blueprint's Draft wireframe and Check a plan wireframe, with their "why" panels, and "Trust, not over-trust"; DESIGN.md sections 5 (Draft bar) and 10; docs/agents/areas/app.md.

**Blocked by:** 10 (Check a plan, on screen, for the NWWDA plan); 14 (Ask from the one box: the answer panel and the evidence drawer)

**Status:** in-progress
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] On the NWWDA plan, "Draft review notes (3 rows)" creates a draft with notes for KE-NWWDA-541055-CW-RFB, KE-NWWDA-229129-CW-RFB and KE-NWWDA-541062-CW-RFQ, each citing its plan rows, and every sentence passed the six checks.
- [ ] Through the HTTP routes, a draft moves Draft to Checked by you to Exported only on the person's actions; exporting from Draft is refused; Discard can be undone.
- [ ] The bar's left text is the DESIGN.md section 5 sentence adapted to review notes, ending "Exporting sends nothing and is not a World Bank review, clearance or no-objection.", and "You opened N of M sources" equals the distinct cited sources this viewer opened.
- [ ] Export produces a Word file with one footnote per citation and an evidence pack in PDF and CSV listing every source and whether it was opened; the success state names the file and its footnote count.
- [ ] A test proves export makes no outbound call: the files are only offered to the person.
- [ ] The Drafts tab lists only the author's team's drafts, under To check, Checked and Exported.
- [ ] The page follows the blueprint's Draft wireframe (states in the sticky header, the bar held to the document column, Discard set apart) and DESIGN.md section 5's Draft bar; scroll padding keeps focused elements clear of the sticky bar (DESIGN.md section 10); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/35-drafts-runtime-and-review-notes, as soon as ticket 14 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
