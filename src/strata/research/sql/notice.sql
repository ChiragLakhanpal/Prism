-- One notice of the project by its id, whatever its date, public by the as-of date (ADR 0002), with its text as silver
-- keeps it (contact details stripped at ingestion, CLAUDE.md rule 8): the notices the demo seed names by key
-- (ops/research/seed.py, ticket 152), which may be older than the procurement_notices reader's window.
SELECT n.notice_id, n.notice_type, n.notice_date, n.step_reference, n.bid_reference_no, n.bid_description,
       n.procurement_method, n.public_from, s.notice_text
FROM strata.gold.notice AS n
LEFT JOIN (
  SELECT notice_id, max(notice_text) AS notice_text
  FROM strata.silver.notices
  WHERE project_id = :project_id
    AND notice_id = :notice_id
  GROUP BY notice_id
) AS s ON s.notice_id = n.notice_id
WHERE n.project_id = :project_id
  AND n.notice_id = :notice_id
  AND n.public_from <= :as_of
