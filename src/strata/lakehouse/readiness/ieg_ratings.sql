-- IEG ratings' data readiness measures, for every country (subject all):
--   coverage_years   evaluation fiscal years with ratings, of the fiscal years from the first to the last
--   linked_project   ratings whose project record is held, of all ratings
-- Its coverage_rows and freshness are written for every source at once (strata.lakehouse.readiness).
WITH held AS (
  SELECT
    count(*) AS ratings,
    count(p.project_id) AS with_project,
    count(DISTINCT r.evaluation_fy) AS years_held,
    max(r.evaluation_fy) - min(r.evaluation_fy) + 1 AS years_spanned
  FROM strata.gold.ieg_rating AS r
  LEFT JOIN strata.gold.project AS p ON p.project_id = r.project_id
)
SELECT 'ieg_ratings' AS source, 'all' AS subject, 'coverage_years' AS measure, 'coverage' AS kind,
  CAST(years_held AS BIGINT) AS count, CAST(years_spanned AS BIGINT) AS denominator, CAST(NULL AS DATE) AS as_of,
  'This counts the fiscal years that have evaluations, out of the fiscal years from the first to the last.' AS detail
FROM held
WHERE ratings > 0
UNION ALL
SELECT 'ieg_ratings', 'all', 'linked_project', 'linked', CAST(with_project AS BIGINT), CAST(ratings AS BIGINT),
  CAST(NULL AS DATE), 'This counts the ratings whose project record is held, out of all ratings.'
FROM held
WHERE ratings > 0
