-- The draft an author already saved with this idempotency key, so a second request with the same key
-- (a double click, or React's StrictMode) saves nothing new and opens the same draft.
SELECT draft_id
FROM strata.ops.drafts
WHERE author_id = :author_id
  AND idempotency_key = :idempotency_key
ORDER BY created_at
LIMIT 1
