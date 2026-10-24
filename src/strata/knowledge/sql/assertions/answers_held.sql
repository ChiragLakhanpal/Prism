-- The batch model's answers already held for the requests a run would ask (:hashes, their request hashes
-- joined by commas), from the same reader, newest first, leaving out errors and requests still in a running
-- batch, which have no content and are asked again or waited for.
SELECT
  b.custom_id,
  b.request_hash,
  b.content,
  b.error
FROM strata.bronze.batch_answers AS b
WHERE b.read_by = :read_by
  AND array_contains(split(:hashes, ','), b.request_hash)
  AND b.content IS NOT NULL
ORDER BY b.answered_at DESC
