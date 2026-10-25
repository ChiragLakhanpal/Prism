# 23: Disagreements on screen: the project timeline and the disagreement card

**What to build:** A project's Timeline tab shows What, How and Why in three lanes on one time axis, and wherever a claim appears, a disagreement card shows both sides when its sources disagree. The timeline draws evaluations in the Why lane (PAD, ICR, ICR Review and its re-issue), operations in the How lane (the mid-term review, ISRs with their rating bands, the restructuring) and records in the What lane (contracts signed). Each mark opens its source in the evidence drawer, and a disagreement is a dashed warning line labeled "2 reports disagree". The chart has one tab stop with arrow keys between marks and a "Show the table" twin, and becomes a list in date order below 768 px. The disagreement card puts both claims side by side (stacked below 768 px), in the order they were written and with equal weight, each with its source line and date; tags one "Strata leans on this"; states the rule in one sentence; says what changes if you keep the other; and lets the person keep the other source with a reason that is stored for the evidence pack. It uses the warning state and the badge "Two reports disagree" only when the disagreement changes a number or claim in the answer or draft, and otherwise an info note, "Sources differ"; never the error state. It appears only beside the claim it concerns, in the answer panel and the drawer.

Read first: DESIGN.md sections 5 (Disagreement card), 6 and 10; the blueprint's Project timeline wireframe and its "why" panels, and "When reports disagree, both stay on screen"; docs/agents/areas/app.md.

**Blocked by:** 14 (Ask from the one box: the answer panel and the evidence drawer); 20 (Assertions, disagreements and the evidence ladder); 21 (The project page as the hub)

**Status:** in-progress
**Area:** app
**Phase:** P2
**Design review:** yes

- [ ] P130164's timeline places the PAD (October 1, 2013), the mid-term review (May 16, 2016), ISR 7 (August 26, 2016, Satisfactory), the contract IN-RRSMP-7431-CW-RFB (June 15, 2017), the restructuring (July 27, 2017), ISR 12 (April 10, 2018, Moderately Unsatisfactory), the ICR (October 10, 2019), the ICR Review (March 27, 2020) and its re-issue (May 4, 2023) at their dates, and the rating bands name their ratings in text.
- [ ] A dashed line labeled "2 reports disagree" joins ISR 7 and the ICR, and activating it opens the disagreement card in the drawer.
- [ ] The card shows ISR 7 first and ICR ¶78 second, with equal weight, "Strata leans on this" on the ICR, the rule sentence and the "keep the other" line, as in the blueprint's P130164 example.
- [ ] A scripted answer whose number depends on the disagreement shows the warning state and "Two reports disagree"; one whose claims do not depend on it shows the info note "Sources differ"; neither ever uses the error state.
- [ ] Keeping the ISR asks for a reason and stores it with the viewer and the answer or draft in strata.ops.
- [ ] The ISR series shows as rating bands, never as a disagreement.
- [ ] The chart has role img with a name, one tab stop, arrow keys between marks, "Show the table", a time axis with no title and about five ticks (DESIGN.md sections 6 and 10); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/23-timeline-and-disagreement-card, as soon as ticket 21 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
