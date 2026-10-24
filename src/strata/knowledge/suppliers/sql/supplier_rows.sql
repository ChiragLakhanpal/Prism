-- Every supplier row that supplier resolution reads (strata.knowledge.suppliers.resolve), one per
-- supplier of each contract or award notice:
--   awards              the awards since FY2020, as the newest fetch of each contract holds them. Every
--                       row has its STEP supplier ID; they are read so that a row with no ID can be
--                       matched to the supplier an ID names.
--   awards_fy2001_2016  the FY2001 to FY2016 awards, from the newest fetch of each row. The dataset has
--                       no supplier_id column.
--   notices             each Contract Award notice's awarded bidders, from its newest page.
-- contract is how a person tells the row's contract apart: its STEP reference when it has one, or
-- else its contract number or notice ID.
WITH fy2001_2016 AS (
  SELECT *
  FROM strata.silver.awards_fy2001_2016
  QUALIFY row_number() OVER (PARTITION BY contract_number, supplier, supplier_contract_amount_usd
                             ORDER BY fetched_at DESC, page_hash) = 1
),
award_notices AS (
  SELECT notice_id, page_hash, step_reference
  FROM strata.silver.notices
  WHERE notice_type = 'Contract Award'
  QUALIFY row_number() OVER (PARTITION BY notice_id ORDER BY fetched_at DESC, page_hash) = 1
)
SELECT
  'awards' AS source,
  a.wb_contract_number AS source_key,
  CAST(row_number() OVER (PARTITION BY a.wb_contract_number ORDER BY a.supplier_id) AS INT) AS position,
  a.wb_contract_number AS contract_id,
  a.project_id,
  a.supplier AS name,
  a.supplier_country AS country,
  a.supplier_id AS step_supplier_id,
  a.individual_consultant,
  coalesce(a.step_reference, a.wb_contract_number) AS contract,
  a.public_from
FROM strata.silver.awards_current AS a
UNION ALL
SELECT
  'awards_fy2001_2016',
  f.contract_number,
  CAST(row_number() OVER (PARTITION BY f.contract_number ORDER BY f.supplier, f.supplier_contract_amount_usd) AS INT),
  f.contract_number,
  f.project_id,
  f.supplier,
  f.supplier_country,
  CAST(NULL AS STRING),
  f.individual_consultant,
  coalesce(f.step_reference, f.contract_number),
  f.public_from
FROM fy2001_2016 AS f
UNION ALL
SELECT
  'notices',
  b.notice_id,
  b.position,
  b.notice_id,
  b.project_id,
  b.name,
  b.country,
  b.step_supplier_id,
  b.individual_consultant,
  coalesce(n.step_reference, b.notice_id),
  b.public_from
FROM strata.silver.notice_bidders AS b
JOIN award_notices AS n ON n.notice_id = b.notice_id AND n.page_hash = b.page_hash
