-- Each Contract Award notice page in strata.silver.notices whose awarded bidders have not been read
-- yet. A notice page is read once; a later page of the same notice is read again, and gold reads the
-- newest.
SELECT
  n.notice_id,
  n.project_id,
  n.step_reference,
  n.notice_text,
  n.page_hash,
  n.fetched_at,
  n.public_from
FROM strata.silver.notices AS n
WHERE n.notice_type = 'Contract Award'
  AND n.notice_text IS NOT NULL
  AND NOT EXISTS (
    SELECT 1
    FROM strata.silver.notice_bidders AS b
    WHERE b.notice_id = n.notice_id AND b.page_hash = n.page_hash
  )
