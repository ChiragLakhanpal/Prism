-- The upload a person already kept with this idempotency key, so a second click keeps nothing new.
SELECT upload_id
FROM strata.ops.uploads
WHERE uploader_id = :uploader_id
  AND idempotency_key = :idempotency_key
