# 15: Plan a package from a sentence

**What to build:** At concept stage, before any STEP rows exist, a specialist types "rural roads, Kenya, about US$15 million" into the box, chooses "Plan a package from this sentence", and lands in a new package workspace showing what Strata understood as chips they can change, with the past range beneath. The plan-a-package workflow (Microsoft Agent Framework, in code) turns the sentence into criteria with one structured model call, recorded for the offline gate. Chips follow the package form schema, the single place where each criterion's group (What, Where, How), STEP field name and source (typed, computed or guessed) is defined. Review type and market approach are computed from the thresholds file and labeled as computed, with a note that states the rule from the file's values; guesses are marked as guesses ("1 guess to check"); "Your plan: N months" is typed by the person. Changing a chip reruns find_comparables and updates section 1. Packages save to strata.ops with a "saved" stamp. The Packages tab lists plans in progress (the person's packages and checked plans) with "Check a plan" and "Plan a package" as its actions, and the box gains its "Plan a package from this sentence" intent. A dot on the range chart now opens its comparable package in the evidence drawer, with its notice and contract records and their source lines. The sticky action that suggests PPSD risk rows arrives with the PPSD ticket.

Read first: docs/PLAN.md sections 1 and 8; DESIGN.md sections 5, 7 and 10; the blueprint's Package workspace wireframe ("What I understood") and its "why" panels, and "Where Strata enters the work".

**Blocked by:** 12 (Comparables and the past range, on the package workspace); 14 (Ask from the one box: the answer panel and the evidence drawer)

**Status:** in-progress
**Area:** app
**Phase:** P1
**Design review:** yes

- [ ] With the recorded model output, the sentence yields the chips Works, Rural roads, About US$15 million and a guessed "2 lots?" under What; Kenya under Where; and RFB, Open international (computed), Single stage, one envelope, Post-qualification and Prior review (computed) under How, as the Package workspace wireframe shows.
- [ ] The computed note reads from the thresholds file's values; changing the prior-review threshold in that file changes the review type chip with no code change.
- [ ] Adding a temporary field to the package form schema adds a chip in its group with no other code change, and removing it removes the chip.
- [ ] Typing "ICB" into the method chip stores Request for Bids with an open international market approach.
- [ ] Changing a chip reruns find_comparables and redraws section 1; the box never creates a package unless the person chooses "Plan a package from this sentence".
- [ ] A saved package reopens with the same chips, and the Packages tab lists it with the person's checked plans.
- [ ] Opening a dot on the range chart, by click or by Enter on the focused mark, opens the evidence drawer at that comparable's records, and closing it returns focus to the mark.
- [ ] Chips are at least 32px tall and editable by keyboard; computed and guessed chips say so in text, not only by style (DESIGN.md section 10); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/15-plan-a-package-from-a-sentence, as soon as ticket 12 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
