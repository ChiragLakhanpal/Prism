# 19: Suppliers resolved on STEP IDs first, names second

**What to build:** Each supplier is one record across contract awards and award notices. STEP supplier IDs decide first. Only rows with no ID go to name matching (Splink, with names normalized for legal forms, transliteration and punctuation, blocked by country); a model adjudicates the uncertain middle; and whatever stays uncertain goes to a person through a review list in strata.ops, where each decision records the reviewer and the reason. The match thresholds live in the thresholds file. A joint venture stays its own supplier, linked to its members. "INDIVIDUAL CONSULTANT" is never shown by name. A labeling tool lets a person label candidate pairs, and auto-merge precision is measured on them, aiming at 1,000 labeled pairs and a precision of at least 0.98. No supplier score, rank or profile is computed anywhere.

Read first: docs/PLAN.md section 5 (Suppliers); the blueprint's "Suppliers resolve on keys first"; docs/agents/areas/knowledge.md.

**Blocked by:** 17 (Every structured source, for every country, kept as published)

**Status:** ready-for-agent
**Area:** knowledge
**Phase:** P2
**Design review:** no

- [ ] On the fixture, the STEP supplier ID in award notices matches the awards table's supplier_id in every recorded check, reproducing the blueprint's 7 of 7.
- [ ] A row that has a STEP supplier ID never enters name matching.
- [ ] Pairs are routed to auto-merge, model adjudication or a person by the thresholds in the thresholds file; changing a threshold changes the routing of a fixture pair.
- [ ] The review list shows each uncertain pair with both names, countries and contracts, and a decision writes merge or no merge with the reviewer and the reason.
- [ ] strata.ops reports how many pairs are labeled and the auto-merge precision on them with its interval; the auto-merge threshold is set so that precision on the labeled pairs is at least 0.98.
- [ ] The fixture's joint venture is one supplier linked to its members.
- [ ] The supplier tables expose no score, rank or rating column, and no tool returns a supplier profile.
