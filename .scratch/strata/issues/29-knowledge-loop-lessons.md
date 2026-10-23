# 29: The knowledge loop: proposed lessons with verified quotes, the review queue and versions

**What to build:** Completion reports turn into lessons that people decide on. One batch pass (gpt-5.4-nano on Global Batch) over each ICR, ICR Review and PPAR in the slice proposes lessons, each with a statement, risk factors from the closed list, a lifecycle stage, a polarity and verbatim evidence with its page. A proposed lesson is rejected unless its quote is found word for word on the cited page; the check rejects and never repairs. An ICR Review's restatement attaches as a second, IEG-endorsed piece of evidence, and a lesson resting on an ICR alone is marked "Awaiting IEG review". The review-proposed-lessons workflow (Microsoft Agent Framework, with the lesson review writer summarizing the evidence and pointing out likely merges) feeds the Lessons tab's "Waiting for review" queue, which only reviewers see. An accredited procurement specialist recommends and a lead procurement specialist decides, each with a reason; two different people per decision; nobody decides on their own projects (from the roles file); the 10-business-day clock shows on each item. States: current at a version, rejected (the reason kept for the extractor), merged as evidence, being re-checked, retired; each new version records was, now and the reason. A quarterly job draws a 10% sample of decisions for another region to cross-check. The get_lessons tool (one registry entry) returns current lessons at their versions with evidence ids, ranked by fit and evidence and never by use, tagged by the Regulations edition their projects followed.

Read first: docs/PLAN.md sections 5 (Lessons) and 11 (Lesson governance); the blueprint's Lessons wireframe and "Three loops, one dated store" (panels "Who decides a lesson" and "Lesson states"); DESIGN.md sections 5 and 7; docs/agents/areas/knowledge.md.

**Blocked by:** 14 (Ask from the one box: the answer panel and the evidence drawer); 18 (The document slice, the page router's Route B and the stress shelf)

**Status:** ready-for-agent
**Area:** knowledge
**Phase:** P2
**Design review:** yes

- [ ] On the fixture, extraction proposes "Base works estimates on market rates to avoid rebidding" from ICR P130164 ¶54 on page 23 with its quote, and the ICR Review's restatement attaches as IEG-endorsed evidence.
- [ ] A fixture proposal whose quote is not on its cited page is rejected and counted, and its text is not altered to fit.
- [ ] The queue and its tab appear only for reviewer roles; anyone else gets a permission error from the route and sees no entry.
- [ ] The same person cannot both recommend and decide, and nobody can decide on a lesson from their own project; both attempts are refused with a reason.
- [ ] A decision moves the lesson to current at version 1 with both names, reasons and dates; a rejection keeps its reason; days from publication to decision are recorded as the knowledge loop's leading indicator.
- [ ] get_lessons ordering is unchanged when usage counts change, proving it ranks by fit and evidence only, and each lesson carries its Regulations edition.
- [ ] The quarterly job writes a 10% sample of decisions assigned to another region.
- [ ] The queue follows the Lessons wireframe's "Waiting for review (3) · reviewers only" tab and DESIGN.md section 5; reviewer actions use plain verbs ("Recommend", "Reject, with a reason", "Add to the library"), never a DESIGN.md section 7 rule 19 word; states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
