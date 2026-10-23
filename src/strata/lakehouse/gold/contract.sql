-- strata.gold.contract: one row per contract, from the rows of its suppliers that the newest fetch
-- of it holds (strata.silver.awards_current). A joint venture's members each have a row with their
-- share, so the contract's amount adds the shares and is counted once, and its supplier is the
-- joint venture, JV- and its members' IDs.
-- key: wb_contract_number
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
)
SELECT
  f.wb_contract_number,
  f.project_id,
  f.borrower_country_code AS country_code,
  f.step_reference,
  f.reference_method_code,
  f.borrower_contract_reference_number,
  f.contract_description,
  f.procurement_category,
  f.procurement_method,
  f.review_type,
  f.contract_signing_date,
  f.fiscal_year,
  c.contract_amount_usd,
  CASE WHEN c.supplier_count > 1 THEN 'JV-' || c.member_ids ELSE f.supplier_id END AS supplier_id,
  CAST(c.supplier_count AS INT) AS supplier_count,
  c.supplier_count > 1 AS joint_venture,
  f.public_from
FROM first_row AS f
JOIN contracts AS c ON c.wb_contract_number = f.wb_contract_number
