# 32: The retrieval loop: a labeled set, tuned hybrid search and feedback

**What to build:** Retrieval is measured on a labeled set, tuned only when tuning wins, and improved by feedback that never touches production until a person reviews it. The labeled set: ICR Reviews' "ICR para N" citations and PADs' "lessons reflected in the design" sections as silver labels, plus 150 queries written from award notices and judged by two people through a judging tool that records their agreement. Retrieval evaluation plugs into the replay harness and reports recall at 20, precision at 10 and nDCG at 10, using only documents public before each query's date. Tuning (hybrid weights, the reranker, the passage header) ships only when it loses nothing on the held-out set or the hindsight set. In the evidence drawer, "Wrong passage" and "Not useful" sit together at the bottom under "Was this the right passage?", take an optional reason, and write candidate labels to strata.ops. In the pilot a person reviews every report through a label review list; the rules for scale are built and tested too (three agreeing users with no dissent make a silver label, weighted as in Dawid and Skene, with a 10% audit; no user supplies more than 10% of a batch; reports about one's own project always go to a person). A reviewed label can demote a passage but never hide it. Evaluation sets never take live feedback. The loop's leading indicator, "Wrong passage" per 100 sources opened, and the per-viewer counts for "You marked 2 passages as wrong; 1 is fixed, and 14 answers now cite the right paragraph" are computed for the dashboard and the Lessons page.

Read first: docs/PLAN.md sections 10 and 11 (Feedback); the blueprint's Evidence drawer wireframe and "Three loops, one dated store" ("Feedback that teaches, safely"); DESIGN.md sections 5 and 10; docs/agents/areas/knowledge.md.

**Blocked by:** 14 (Ask from the one box: the answer panel and the evidence drawer); 18 (The document slice, the page router's Route B and the stress shelf); 25 (The replay harness and the survival model's backtests)

**Status:** ready-for-agent
**Area:** knowledge
**Phase:** P2
**Design review:** yes

- [ ] The silver label set's size is recorded, and the judging tool records two judges per notice query with their agreement statistic.
- [ ] strata.ops holds recall at 20, precision at 10 and nDCG at 10 per query set, and a test proves no document public after a query's date is retrieved for it.
- [ ] A deliberately worse search configuration is blocked by the tuning gate, and the current one passes.
- [ ] "Wrong passage" and "Not useful" sit grouped at the bottom of the drawer as ghost buttons, each writes one candidate label with viewer, passage, query and reason, and production ranking does not change until a person accepts the label.
- [ ] An accepted label demotes its passage for that kind of query, and a demoted passage still appears when it is the only evidence.
- [ ] Through seams 1 and 3: three agreeing users with no dissent make a silver label; a user's share of a batch is capped at 10%; a report about one's own project goes to a person.
- [ ] Building an evaluation set from a label that came from live feedback fails.
- [ ] "Wrong passage" per 100 sources opened and the per-viewer fixed and re-cited counts are computed and stored.
- [ ] The feedback row follows the Evidence drawer wireframe and DESIGN.md section 5 (ghost buttons) and section 10 (24px targets, focus); states are captured at 1440, 1024 and 390 px; axe finds no WCAG 2.2 AA violations.
