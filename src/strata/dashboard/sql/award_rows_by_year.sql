-- Tile 4: contract-award rows per fiscal year, by the dataset they came from, as public on the
-- measure date (ADR 0002). Fiscal 2017 to 2019 come from award notices, which neither awards
-- dataset covers. A year with no rows has no bar.
SELECT
  fiscal_year,
  concat('FY', right(CAST(fiscal_year AS STRING), 2)) AS fiscal_year_label,
  CASE source
    WHEN 'awards' THEN 'Awards since FY2020'
    WHEN 'awards_fy2001_2016' THEN 'Awards, FY2001–16'
    ELSE 'Award notices, FY2017–19'
  END AS dataset,
  count(*) AS award_rows
FROM strata.gold.contract
WHERE public_from <= :measure_date AND fiscal_year IS NOT NULL
GROUP BY fiscal_year, source
ORDER BY fiscal_year, dataset
