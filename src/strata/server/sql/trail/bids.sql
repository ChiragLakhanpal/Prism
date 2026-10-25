-- The contract trail's bids (ticket 22): every bid the award notices of a STEP reference list, read from each
-- notice's newest page (strata.silver.notice_bids), in the notice's own order. :notices holds the notice ids
-- joined by commas, which no notice id contains.
WITH newest AS (
  SELECT notice_id, page_hash
  FROM strata.silver.notice_bids
  WHERE array_contains(split(:notices, ','), notice_id)
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC) = 1
)
SELECT
  b.notice_id,
  b.bid,
  b.member,
  b.section,
  b.name,
  b.country,
  b.individual_consultant,
  b.currency,
  b.price_at_opening,
  b.evaluated_price,
  b.signed_price,
  b.reason,
  b.price_at_opening_label,
  b.evaluated_price_label,
  b.notice_lists_scores
FROM strata.silver.notice_bids AS b
JOIN newest AS n ON n.notice_id = b.notice_id AND n.page_hash = b.page_hash
ORDER BY b.notice_id, b.bid, b.member
