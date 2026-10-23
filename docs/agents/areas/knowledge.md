# Area brief: knowledge

Tickets with `Area: knowledge` turn documents and records into evidence: the page router, passages, embeddings and the AI Search index, proposed lessons, entity resolution, links, assertions and disagreements.

Read: `docs/PLAN.md` section 5, `docs/adr/0002` and `0004`, and the blueprint's "Documents to evidence" and "Knowledge model" sections (`docs/blueprint/strata-blueprint.html`).

- A passage is a numbered paragraph or a table row, with its PDF page and printed page. A citation points at exactly one passage.
- A proposed lesson enters the store only when its quote is found verbatim on the cited page. The check rejects; it never repairs.
- Suppliers resolve on STEP supplier IDs first, by name only where no ID exists, and uncertain pairs go to a person.
- A disagreement needs the same subject and predicate for an overlapping period. A rating that moves over time is a trajectory.
- Every retrieval and tool takes an optional as-of date and never returns a passage made public after it.
- Known-answer tests come from the showcase project, P130164: ICR ¶54 (the rebidding lesson, PDF page 23), ¶55 (clearances before award) and ¶78 against ISR 7 (the disagreement).
