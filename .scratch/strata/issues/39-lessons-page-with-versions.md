# 39: The Lessons page, with versions and was and now in drafts

**What to build:** The Lessons page opens on what affects the reader's work, and a changed lesson shows was and now wherever it was used, so nothing in a draft changes without its author. The page leads with a sentence counting what came in since the reader's last visit (completion reports, ICR Reviews, new and changed lessons, proposed lessons with reviewers), then "Changed where you used it" (the lesson, was and now with its version and date, where it is used and which version the draft cites, and "See both versions", "Update the row" and "Keep version 1, with a reason"), then "New" lessons (statement, quote, citations, the IEG-endorsed badge or "Awaiting IEG review", chips for stage, category and sector, and who recommended and decided it, by role, with the date), then the reader's feedback line, then the library with filters for stage, method, sector and status and a count line. In an open draft, a row citing a changed lesson shows was and now with the same two choices. Notices are tiered: a strengthened lesson goes to the digest only, a narrowed one appears on the draft, and one retired as wrong must be resolved before export. Proposed lessons never appear outside the reviewers' queue.

Read first: docs/PLAN.md section 11 (Lesson governance); the blueprint's Lessons wireframe and its "why" panels, the Draft wireframe, and "Three loops, one dated store" ("Drafts cite a version", "Showing that it learned"); DESIGN.md sections 5 and 7; docs/agents/areas/app.md.

**Blocked by:** 29 (The knowledge loop: proposed lessons with verified quotes, the review queue and versions); 32 (The retrieval loop: a labeled set, tuned hybrid search and feedback); 36 (Suggested PPSD risk rows and the Project Paper summary, exported to Word)

**Status:** ready-for-agent
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] A fixture version change to a lesson cited at version 1 in a reader's draft appears under "Changed where you used it" with was, now, the version date, "Used in: <draft> (cites version 1)" and the three actions.
- [ ] "Update the row" rewrites the draft row to the new version and records it; "Keep version 1, with a reason" stores the reason with the draft.
- [ ] A version retired as wrong holds the draft's export with the reason shown; a narrowed version shows on the draft; a strengthened one appears only in the digest.
- [ ] The headline counts equal the stored counts since the reader's last visit.
- [ ] A lesson restated by an ICR Review shows the IEG-endorsed badge; one resting on an ICR alone shows "Awaiting IEG review".
- [ ] The library filters by stage, method, sector and status with a count line ("showing N of M"), and no proposed lesson appears for a non-reviewer.
- [ ] The feedback line reads from the retrieval loop's per-viewer counts in the form "You marked 2 passages as wrong; 1 is fixed, and 14 answers now cite the right paragraph."
- [ ] The page follows the Lessons wireframe and DESIGN.md sections 5 (cards, info badge) and 7; states (first visit, nothing new) are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
