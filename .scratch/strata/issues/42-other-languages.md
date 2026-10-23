# 42: French, Spanish and Portuguese sources and answers

**What to build:** Reports written in French, Spanish or Portuguese count as evidence, and an implementing agency officer can ask for answers and drafts in their working language while the interface stays in English. Every passage's language is set and checked across the slice. Retrieval works across languages: an English query finds French passages and the reverse, measured on a small bilingual query set through the retrieval evaluation. The lang parameter (fr, es or pt) sets the language the agent writes answers and drafts in; quotes stay word for word in their original language, carry their language attribute, and still pass the verifier. The old method names used in the French Procurement Plan template and in French, Spanish and Portuguese plans are accepted on input and written back in the current Regulations' names. The French Procurement Plan template is registered as a source.

Read first: docs/PLAN.md sections 3 and 5; the blueprint's "Who reaches for Strata, and when" (implementing agencies working in French, Spanish or Portuguese) and Evidence drawer wireframe; DESIGN.md section 10; docs/agents/areas/knowledge.md.

**Blocked by:** 32 (The retrieval loop: a labeled set, tuned hybrid search and feedback)

**Status:** ready-for-agent
**Area:** knowledge
**Phase:** P2
**Design review:** yes

- [ ] Every non-English passage in the slice has a language set, and a check of 50 sampled passages agrees with an independent language detector.
- [ ] A bilingual query set of at least 20 queries reports recall at 20 for English queries over French passages, stored in strata.ops.
- [ ] With lang set to fr, a scripted answer and a draft are written in French, their quotes stay word for word with the fr language attribute, and all six checks pass.
- [ ] Passages render with their language attribute in the evidence drawer and the source view (DESIGN.md section 10), checked by Playwright.
- [ ] A French method name in a fixture plan maps to the current Regulations' name.
- [ ] Interface strings stay English: the copy file is unchanged by this ticket, and the drawer follows the Evidence drawer wireframe in every language; axe finds no WCAG 2.2 AA violations.
