-- The seed command's example lesson change for one viewer (ticket 41), added only when the viewer has no example
-- version of that lesson with that number yet.
INSERT INTO strata.ops.example_lesson_versions (viewer_id, lesson_id, version, version_row, seeded_at, public_from)
SELECT :viewer_id, :lesson_id, :version, :version_row, CAST(:seeded_at AS TIMESTAMP), CAST(:seeded_at AS DATE)
WHERE NOT EXISTS (
  SELECT 1 FROM strata.ops.example_lesson_versions AS e
  WHERE e.viewer_id = :viewer_id AND e.lesson_id = :lesson_id AND e.version = :version
)
