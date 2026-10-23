-- strata.gold.country: each country code that projects or awards name, with the earliest date any
-- project, award or notice for it became public. Notices name the country only in words.
-- key: country_code
WITH named AS (
  SELECT country_code, country_name, region, public_from
  FROM strata.silver.projects
  UNION ALL
  SELECT borrower_country_code AS country_code, borrower_country AS country_name, region, public_from
  FROM strata.silver.awards
),
codes AS (
  SELECT country_code, min(country_name) AS country_name, min(region) AS region, min(public_from) AS public_from
  FROM named
  WHERE country_code IS NOT NULL
  GROUP BY country_code
),
noticed AS (
  SELECT project_country, min(public_from) AS public_from
  FROM strata.silver.notices
  GROUP BY project_country
)
SELECT
  c.country_code,
  c.country_name,
  c.region,
  least(c.public_from, n.public_from) AS public_from
FROM codes AS c
LEFT JOIN noticed AS n ON n.project_country = c.country_name
