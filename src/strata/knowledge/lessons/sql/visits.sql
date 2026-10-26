-- A reader's earlier loads of a Lessons page, each with the start of the visit it belonged to
-- (strata.knowledge.lessons.visits).
SELECT visit_started_at, seen_at
FROM strata.ops.lesson_visits
WHERE viewer_id = :viewer_id
ORDER BY seen_at
