-- get_lessons: the risk factors the completion reports a call counts raised (ticket 30). A report raised a
-- risk factor when the knowledge loop proposed a lesson from it tagged with that factor and found its quote
-- word for word on the page it cites (strata.silver.lesson_proposals, quote_check :passed). Only proposals
-- made on or before :decided_by count (ADR 0002): the as-of date, except in the hindsight test's replays
-- (ticket 34), where it is the replay's own date and a report public by the as-of date counts with what it
-- raised. Each comes with the passage it cites, for the list of reports behind a count. :documents holds the
-- reports' document ids, joined by commas.
SELECT
  p.proposal_id,
  p.document_id,
  p.version,
  p.project_id,
  p.document_type,
  p.passage_id,
  p.paragraph,
  p.cited_page,
  p.risk_factors,
  p.public_from
FROM strata.silver.lesson_proposals AS p
WHERE array_contains(split(:documents, ','), p.document_id)
  AND p.quote_check = :passed
  AND p.public_from <= :decided_by
ORDER BY p.document_id, p.passage_id, p.proposal_id
