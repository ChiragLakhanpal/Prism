-- The packages one person made, newest change first, each with the criteria of its latest save.
SELECT p.package_id, p.author_id, p.author_name, p.sentence, p.run_id, p.created_at,
       s.save_id, s.criteria, s.plan_months, s.plan_before_range, s.saved_at
FROM strata.ops.planned_packages AS p
JOIN strata.ops.planned_package_saves AS s ON s.package_id = p.package_id
WHERE p.author_id = :author_id
QUALIFY row_number() OVER (PARTITION BY s.package_id ORDER BY s.saved_at DESC, s.save_id DESC) = 1
ORDER BY s.saved_at DESC, p.package_id
