-- Every version of every lesson, in order.
SELECT
  v.lesson_id,
  v.version,
  v.statement,
  v.risk_factors,
  v.stage,
  v.kind,
  v.edition_key,
  v.project_id,
  v.state,
  v.change_kind,
  v.was,
  v.now,
  v.reason,
  v.item_id,
  v.decided_on,
  v.decided_by,
  v.decided_by_name,
  v.recommended_by,
  v.recommended_by_name,
  v.recommended_reason,
  v.published_on,
  v.days_from_publication
FROM strata.ops.lesson_versions AS v
ORDER BY v.lesson_id, v.version
