-- strata.gold.supplier: each STEP supplier ID in the awards as the newest fetch of each contract
-- holds them (strata.silver.awards_current), and each joint venture of several of them. An
-- individual consultant keeps their own supplier ID but no name.
-- key: supplier_id
WITH latest AS (
  SELECT *
  FROM strata.silver.awards_current
  WHERE supplier_id IS NOT NULL
),
members AS (
  SELECT
    supplier_id,
    min(supplier) AS name,
    min(supplier_country) AS country,
    max(CAST(individual_consultant AS INT)) AS individual,
    min(public_from) AS public_from
  FROM latest
  GROUP BY supplier_id
),
ventures AS (
  SELECT
    c.supplier_id,
    array_join(array_sort(collect_list(l.supplier)), ' / ') AS name,
    CASE WHEN count(DISTINCT l.supplier_country) = 1 THEN min(l.supplier_country) END AS country,
    min(c.supplier_count) AS member_count,
    min(c.public_from) AS public_from
  FROM strata.gold.contract AS c
  JOIN latest AS l ON l.wb_contract_number = c.wb_contract_number
  WHERE c.joint_venture
  GROUP BY c.supplier_id
)
SELECT
  supplier_id,
  CASE WHEN individual = 1 THEN NULL ELSE name END AS name,
  country,
  CASE WHEN individual = 1 THEN 'individual consultant' ELSE 'firm' END AS kind,
  CAST(1 AS INT) AS member_count,
  public_from
FROM members
UNION ALL
SELECT
  supplier_id,
  name,
  country,
  'joint venture' AS kind,
  CAST(member_count AS INT) AS member_count,
  public_from
FROM ventures
