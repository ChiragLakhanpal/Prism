# 140: The review queue names the viewer as "you" and everyone else by role, never a person two ways

**What to build:** On October 29, 2026 the demo walkthrough's second capture of the lessons review queue (/lessons/review, as the owner) showed, under "With other reviewers", items printing "Chirag Lakhanpal recommended adding it" beside "You recommended it": the same person named two ways, and a person's name on a page whose rule is "naming roles and never people" (the Lessons tab, ticket 29; `src/strata/knowledge/lessons/review.py`; the spec's user story for lessons). Make the actor's line one rule in one place: when the actor is the viewer, "You recommended adding it on October 29, 2026"; otherwise the actor's role and region ("A lead procurement specialist for South Asia recommended adding it"), never a name or an email, on the queue, on an item's page and in the library. The roles file (`config/roles.toml`) gives the role; a recorded act whose actor is not in the roles file reads "A reviewer recommended adding it". Tests on the fixture's recorded reviewer pages and on the gallery's lesson states, and the live proof is the orchestrator's: the queue as the owner shows "You" and roles only after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `src/strata/knowledge/lessons/review.py` (the acts and who made them), the lessons routes in `src/strata/server/app.py`, `web/src/pages/Lessons*` and the review components, `config/roles.toml`, GLOSSARY.md (lesson, reviewer), DESIGN.md's Lessons page row.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] One rule names an act's actor: "You" for the viewer, the role and region for anyone in the roles file, "A reviewer" otherwise; no page under /lessons prints a person's name or email (a test over the fixture's recorded pages and the gallery states).
- [ ] The queue, an item's page and the library all use it (specs).
- [ ] On the paid workspace, the queue as the owner shows "You" and roles only after the redeploy (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 21:03 PDT from the walkthrough's second capture.
