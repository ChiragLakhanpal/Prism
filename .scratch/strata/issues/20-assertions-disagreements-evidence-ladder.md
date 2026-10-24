# 20: Assertions, disagreements and the evidence ladder

**What to build:** Ratings, dates and amounts from records and documents become dated assertions; Strata detects disagreements between them, tells trajectories apart, and applies the evidence ladder to choose the assertion it leans on while keeping both. Assertions come from ISR ratings (each for its own date and period), ICR ratings and narrative accounts (such as ¶78's account of the mid-term review), ICR Review and PPAR ratings, PAD appraisal ratings, the IEG ratings dataset, and contract and plan dates and amounts. Assertions read from text come from the batch model and are rejected unless their quote is found word for word on the cited page. A disagreement is two assertions with the same subject and attribute for the same or an overlapping period whose values cannot both be true; assertions about different periods form a trajectory. The evidence ladder is one config: outcome judgments lean on the ICR Review or PPAR, then the ICR, then the last ISR, then the PAD; assertions about a moment lean on the record made at that moment; ties go to the more specific source, then the more recent; a report re-issued under the same number replaces its earlier version. The get_disagreements tool (one registry entry) returns, for a subject, each disagreement with both sides in the order written, the source Strata leans on, the rule in one sentence, and what changes if the other is kept, plus any trajectories.

Read first: docs/PLAN.md section 5 (Assertions and disagreements); ADR 0002; the blueprint's "When reports disagree, both stay on screen"; docs/agents/areas/knowledge.md.

**Blocked by:** 18 (The document slice, the page router's Route B and the stress shelf)

**Status:** in-progress
**Area:** knowledge
**Phase:** P2
**Design review:** no

- [ ] For P130164, ISR 7 (August 26, 2016, progress towards the objective rated Satisfactory) and ICR ¶78 (October 10, 2019, the mid-term review found part of the objective compromised) come back from get_disagreements as one disagreement, with Strata leaning on the ICR under the outcome-judgment rule.
- [ ] ISRs 1 to 9 (Satisfactory), 10 and 11 (Moderately Satisfactory) and 12 and 13 (Moderately Unsatisfactory) come back as a trajectory, not a disagreement.
- [ ] As of October 1, 2019, no disagreement is returned for that subject, because the ICR was not yet public.
- [ ] Reordering the ladder in its config, with no code change, flips the source Strata leans on in the fixture case.
- [ ] A fixture tie is decided by the more specific source, and a second by the more recent one.
- [ ] The May 4, 2023 re-issue of the ICR Review replaces the March 27, 2020 version for current answers.
- [ ] An extracted assertion whose quote is not on its cited page is rejected and counted.
- [ ] Every assertion has subject, attribute, value, period, made-at date, public_from, source document and passage, and evidence tier, checked by a schema test.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/20-assertions-disagreements-evidence-ladder, as soon as ticket 18 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
