-- The examples the seed command set up for one viewer (ticket 41), oldest first.
SELECT example_key, item_kind, item_id, seeded_at
FROM strata.ops.seeded_examples
WHERE viewer_id = :viewer_id
ORDER BY seeded_at, example_key
