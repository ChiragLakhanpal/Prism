-- strata.gold.contract: one row per contract, from three sources. A new source is also named in
-- src/strata/server/tracker.py's CONTRACT_SOURCES, or the step tracker ignores its signing dates.
--
-- awards              contract awards since FY2020, in US dollars, from the rows of its suppliers
--                     that the newest fetch holds (strata.silver.awards_current). A joint venture's
--                     members each have a row with their share, so the contract's amount adds the
--                     shares and is counted once, and its supplier is the joint venture, JV- and its
--                     members' IDs.
-- awards_fy2001_2016  prior-review contract awards from FY2001 to FY2016, in US dollars, with no
--                     STEP supplier ID, from the newest fetch of each row. Its supplier is the one
--                     name matching resolved (strata.silver.supplier_resolution).
-- notices             FY2017 to FY2019, which neither awards dataset covers: each Contract Award
--                     notice whose contract was signed in those years (or, with no signature date,
--                     whose notice was published in them) is a contract, with the signed price in
--                     the currency the notice names, labeled as US dollars or local currency from
--                     award notices. A notice with no signature date whose STEP reference is
--                     already a contract's from an awards dataset is that contract, published after
--                     its signing, so it is left out rather than counted twice. Its supplier is
--                     the awarded bidder the notice lists, by the STEP supplier ID the notice writes
--                     or as name matching resolved it (strata.silver.supplier_resolution).
-- A contract number in both datasets is kept once, from the later dataset.
-- A joint venture's supplier is JV- and its members' supplier IDs, from whichever source.
-- key: contract_id
WITH contracts AS (
  SELECT
    wb_contract_number,
    count(*) AS supplier_count,
    CAST(sum(supplier_contract_amount_usd) AS DECIMAL(18, 2)) AS contract_amount_usd,
    array_join(array_sort(collect_list(supplier_id)), '-') AS member_ids
  FROM strata.silver.awards_current
  GROUP BY wb_contract_number
),
first_row AS (
  SELECT *
  FROM strata.silver.awards_current
  QUALIFY row_number() OVER (PARTITION BY wb_contract_number ORDER BY supplier_id) = 1
),
since_fy2020 AS (
  SELECT
    f.wb_contract_number AS contract_id,
    'awards' AS source,
    1 AS preference,
    f.wb_contract_number,
    CAST(NULL AS STRING) AS award_notice_id,
    f.project_id,
    f.borrower_country_code AS country_code,
    f.step_reference,
    f.reference_method_code,
    f.borrower_contract_reference_number,
    f.contract_description,
    f.procurement_category,
    f.procurement_method,
    f.procurement_method_as_written,
    f.market_approach,
    f.review_type,
    f.contract_signing_date,
    f.fiscal_year,
    c.contract_amount_usd,
    CAST(c.contract_amount_usd AS DECIMAL(20, 2)) AS contract_amount,
    'USD' AS contract_currency,
    'US dollars' AS amount_basis,
    CASE WHEN c.supplier_count > 1 THEN 'JV-' || c.member_ids ELSE f.supplier_id END AS supplier_id,
    CAST(c.supplier_count AS INT) AS supplier_count,
    c.supplier_count > 1 AS joint_venture,
    f.public_from
  FROM first_row AS f
  JOIN contracts AS c ON c.wb_contract_number = f.wb_contract_number
),
resolved AS (
  SELECT
    source,
    contract_id,
    count(*) AS supplier_count,
    min(coalesce(joint_venture_id, supplier_id)) AS supplier_id,
    count(joint_venture_id) > 0 AS joint_venture
  FROM strata.silver.supplier_resolution
  GROUP BY source, contract_id
),
old_rows AS (
  SELECT *
  FROM strata.silver.awards_fy2001_2016
  QUALIFY row_number() OVER (PARTITION BY contract_number, supplier, supplier_contract_amount_usd
                             ORDER BY fetched_at DESC, page_hash) = 1
),
old_contracts AS (
  SELECT
    contract_number,
    count(*) AS supplier_count,
    CAST(sum(supplier_contract_amount_usd) AS DECIMAL(18, 2)) AS contract_amount_usd
  FROM old_rows
  GROUP BY contract_number
),
old_first AS (
  SELECT *
  FROM old_rows
  QUALIFY row_number() OVER (PARTITION BY contract_number ORDER BY supplier, supplier_contract_amount_usd) = 1
),
fy2001_2016 AS (
  SELECT
    f.contract_number AS contract_id,
    'awards_fy2001_2016' AS source,
    2 AS preference,
    f.contract_number AS wb_contract_number,
    CAST(NULL AS STRING) AS award_notice_id,
    f.project_id,
    coalesce(p.country_code, n.country_code) AS country_code,
    f.step_reference,
    f.reference_method_code,
    f.borrower_contract_reference_number,
    f.contract_description,
    f.procurement_category,
    f.procurement_method,
    f.procurement_method_as_written,
    f.market_approach,
    'Prior' AS review_type,
    f.contract_signing_date,
    f.fiscal_year,
    c.contract_amount_usd,
    CAST(c.contract_amount_usd AS DECIMAL(20, 2)) AS contract_amount,
    'USD' AS contract_currency,
    'US dollars' AS amount_basis,
    r.supplier_id,
    CAST(coalesce(r.supplier_count, c.supplier_count) AS INT) AS supplier_count,
    coalesce(r.joint_venture, c.supplier_count > 1) AS joint_venture,
    f.public_from
  FROM old_first AS f
  JOIN old_contracts AS c ON c.contract_number = f.contract_number
  LEFT JOIN resolved AS r ON r.source = 'awards_fy2001_2016' AND r.contract_id = f.contract_number
  LEFT JOIN strata.gold.project AS p ON p.project_id = f.project_id
  -- One code per name: three names carry two codes (see gold/notice.sql).
  LEFT JOIN (
    SELECT country_name, min(country_code) AS country_code FROM strata.gold.country GROUP BY country_name
  ) AS n ON n.country_name = f.borrower_country
),
award_notices AS (
  SELECT
    *,
    contract_fiscal_year AS fiscal_year
  FROM strata.gold.notice
  WHERE notice_type = 'Contract Award'
),
awarded AS (
  SELECT step_reference AS awarded_reference FROM since_fy2020 WHERE step_reference IS NOT NULL
  UNION
  SELECT step_reference AS awarded_reference FROM fy2001_2016 WHERE step_reference IS NOT NULL
),
from_notices AS (
  SELECT
    notice_id AS contract_id,
    'notices' AS source,
    3 AS preference,
    CAST(NULL AS STRING) AS wb_contract_number,
    notice_id AS award_notice_id,
    project_id,
    country_code,
    step_reference,
    reference_method_code,
    bid_reference_no AS borrower_contract_reference_number,
    bid_description AS contract_description,
    procurement_category,
    procurement_method,
    procurement_method_as_written,
    market_approach,
    CAST(NULL AS STRING) AS review_type,
    contract_signature_date AS contract_signing_date,
    CAST(fiscal_year AS INT) AS fiscal_year,
    CAST(NULL AS DECIMAL(18, 2)) AS contract_amount_usd,
    signed_contract_price AS contract_amount,
    signed_contract_currency AS contract_currency,
    CASE WHEN signed_contract_price IS NULL THEN NULL
         WHEN signed_contract_currency = 'USD' THEN 'US dollars, from award notices'
         ELSE 'local currency, from award notices' END AS amount_basis,
    r.supplier_id,
    CAST(coalesce(r.supplier_count, 0) AS INT) AS supplier_count,
    coalesce(r.joint_venture, false) AS joint_venture,
    n.public_from
  FROM award_notices AS n
  LEFT JOIN awarded AS a ON a.awarded_reference = n.step_reference
  LEFT JOIN resolved AS r ON r.source = 'notices' AND r.contract_id = n.notice_id
  WHERE n.fiscal_year BETWEEN 2017 AND 2019
    AND NOT (n.contract_signature_date IS NULL AND a.awarded_reference IS NOT NULL)
),
every_contract AS (
  SELECT * FROM since_fy2020
  UNION ALL
  SELECT * FROM fy2001_2016
  UNION ALL
  SELECT * FROM from_notices
)
SELECT
  contract_id,
  source,
  wb_contract_number,
  award_notice_id,
  project_id,
  country_code,
  step_reference,
  reference_method_code,
  borrower_contract_reference_number,
  contract_description,
  procurement_category,
  procurement_method,
  procurement_method_as_written,
  market_approach,
  review_type,
  contract_signing_date,
  fiscal_year,
  contract_amount_usd,
  contract_amount,
  contract_currency,
  amount_basis,
  supplier_id,
  supplier_count,
  joint_venture,
  public_from
FROM every_contract
QUALIFY row_number() OVER (PARTITION BY contract_id ORDER BY preference) = 1
