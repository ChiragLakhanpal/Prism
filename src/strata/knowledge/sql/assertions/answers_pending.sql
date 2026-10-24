-- The rows with no answer for the requests a run would ask (:hashes, their request hashes joined by commas),
-- from the same reader, newest first: an error, which is asked again, or "pending:" and the id of a batch
-- an earlier run sent the request in, which is still running and is waited for.
SELECT
  b.request_hash,
  b.error
FROM strata.bronze.batch_answers AS b
WHERE b.read_by = :read_by
  AND array_contains(split(:hashes, ','), b.request_hash)
  AND b.content IS NULL
ORDER BY b.answered_at DESC
