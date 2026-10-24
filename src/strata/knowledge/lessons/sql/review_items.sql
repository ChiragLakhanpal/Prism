-- Every item of the lesson review queue, oldest first.
SELECT
  i.item_id,
  i.kind,
  i.proposal_id,
  i.lesson_id,
  i.version,
  i.decided_item_id,
  i.project_id,
  i.region,
  i.decided_region,
  i.origin,
  i.origin_by,
  i.origin_by_name,
  i.origin_reason,
  i.origin_item_id,
  i.entered_on,
  i.due_on,
  i.created_at
FROM strata.ops.lesson_review_items AS i
ORDER BY i.entered_on, i.created_at, i.item_id
