-- The review list for suppliers: each candidate pair of name matching that waits for a person, with both
-- sides' names, countries and contracts (strata.ops.supplier_review_list), most likely first. A pair a person
-- decided that the run sent back, such as a merge that would join two STEP supplier IDs by name, comes with the
-- latest decision on it, so a reviewer sees it was decided (ticket 19's verification round 3, O1). Who decided is
-- left out: the list names no reviewer.
WITH decisions AS (
  SELECT
    pair_id,
    decision,
    reason,
    decided_at,
    row_number() OVER (PARTITION BY pair_id ORDER BY decided_at DESC) AS newest
  FROM strata.ops.supplier_review_decisions
)
SELECT
  l.pair_id,
  l.left_key,
  l.left_name,
  l.left_country,
  l.left_contracts,
  l.right_key,
  l.right_name,
  l.right_country,
  l.right_contracts,
  l.match_probability,
  l.review_reason,
  l.model_decision,
  l.model_confidence,
  l.model_reason,
  d.decision AS latest_decision,
  d.reason AS latest_reason,
  d.decided_at AS latest_decided_at
FROM strata.ops.supplier_review_list AS l
LEFT JOIN decisions AS d ON d.pair_id = l.pair_id AND d.newest = 1
ORDER BY l.match_probability DESC, l.pair_id
