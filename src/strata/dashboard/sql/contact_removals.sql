-- Tile 18: the contact names, email addresses and phone numbers ingestion took out of the pages it kept in the dates
-- chosen, and from how many notices, as bronze wrote them beside each page (strata.ops.contact_removals; ticket 45).
-- Only counts: no contact detail is kept anywhere. Addresses and web addresses come out of their contact fields too,
-- and are counted under their own kinds there.
SELECT
  CASE kind WHEN 'names' THEN 1 WHEN 'emails' THEN 2 ELSE 3 END AS position,
  :kind_label__kind AS kind,
  sum(removed) AS removed,
  sum(records) AS notices,
  CAST(max(fetched_at) AS DATE) AS last_removed
FROM strata.ops.contact_removals
WHERE kind IN ('names', 'emails', 'phones') AND public_from BETWEEN :date_from AND :date_to
GROUP BY kind
ORDER BY position
