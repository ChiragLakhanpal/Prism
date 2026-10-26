-- Every version of every lesson, in order, with the procurement categories and selection methods it names (ticket
-- 39's strata.ops.lesson_version_tags; empty lists for a version that names none).
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
  v.days_from_publication,
  coalesce(t.categories, '[]') AS categories,
  coalesce(t.methods, '[]') AS methods
FROM strata.ops.lesson_versions AS v
LEFT JOIN strata.ops.lesson_version_tags AS t ON t.lesson_id = v.lesson_id AND t.version = v.version
ORDER BY v.lesson_id, v.version
