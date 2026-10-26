-- The seed command set up one example for a viewer (ticket 41). The row is added only when the viewer has no row for
-- that example yet, so running the command twice writes nothing new.
INSERT INTO strata.ops.seeded_examples (viewer_id, example_key, item_kind, item_id, seeded_by, seeded_at, public_from)
SELECT :viewer_id, :example_key, :item_kind, :item_id, 'strata', CAST(:seeded_at AS TIMESTAMP),
       CAST(:seeded_at AS DATE)
WHERE NOT EXISTS (
  SELECT 1 FROM strata.ops.seeded_examples AS s
  WHERE s.viewer_id = :viewer_id AND s.example_key = :example_key
)
