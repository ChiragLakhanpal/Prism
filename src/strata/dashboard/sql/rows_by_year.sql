-- Tile 5: every source's rows per fiscal year, with exact counts, as public on the measure date:
-- the table beside tile 4's chart, and the coverage of the sources that are not awards. The sources'
-- names are parameters whose values are copy.dataReadiness.server.dashboard.labels.
WITH counted AS (
  SELECT
    CASE source
      WHEN 'awards' THEN :awards_label
      WHEN 'awards_fy2001_2016' THEN :fy2001_label
      ELSE :notices_awards_label
    END AS source,
    fiscal_year
  FROM strata.gold.contract
  WHERE public_from <= :measure_date
  UNION ALL
  SELECT :notices_label, fiscal_year FROM strata.silver.notices WHERE public_from <= :measure_date
  UNION ALL
  SELECT :projects_label, approval_fiscal_year FROM strata.gold.project WHERE public_from <= :measure_date
  UNION ALL
  SELECT :ieg_label, evaluation_fy FROM strata.gold.ieg_rating WHERE public_from <= :measure_date
)
SELECT
  source,
  fiscal_year,
  concat('FY', right(CAST(fiscal_year AS STRING), 2)) AS fiscal_year_label,
  count(*) AS source_rows
FROM counted
WHERE fiscal_year IS NOT NULL
GROUP BY source, fiscal_year
ORDER BY source, fiscal_year
