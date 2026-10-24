-- Tile 5: every source's rows per fiscal year, with exact counts, as public on the measure date:
-- the table beside tile 4's chart, and the coverage of the sources that are not awards.
WITH counted AS (
  SELECT
    CASE source
      WHEN 'awards' THEN 'Awards since FY2020'
      WHEN 'awards_fy2001_2016' THEN 'Awards, FY2001–16'
      ELSE 'Award notices, FY2017–19'
    END AS source,
    fiscal_year
  FROM strata.gold.contract
  WHERE public_from <= :measure_date
  UNION ALL
  SELECT 'Procurement notices', fiscal_year FROM strata.silver.notices WHERE public_from <= :measure_date
  UNION ALL
  SELECT 'Projects', approval_fiscal_year FROM strata.gold.project WHERE public_from <= :measure_date
  UNION ALL
  SELECT 'IEG ratings', evaluation_fy FROM strata.gold.ieg_rating WHERE public_from <= :measure_date
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
