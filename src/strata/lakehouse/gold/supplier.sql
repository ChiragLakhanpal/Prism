-- strata.gold.supplier: each supplier, one record across the contract awards and the award notices
-- (ticket 19). A STEP supplier ID decides first; a name decides only where a row has no ID
-- (strata.silver.supplier_resolution).
--   members            each STEP supplier ID in the awards since FY2020, as the newest fetch of each
--                      contract holds them (strata.silver.awards_current)
--   ventures           each joint venture of several of them on one awards contract
--   resolved_firms     each supplier the awards since FY2020 do not hold: a STEP supplier ID known only
--                      from award notices, or a supplier known only by name (N-...), from the FY2001 to
--                      FY2016 awards or a notice's bidder with no ID. Its name is the longest way its
--                      rows public on its earliest day write it, since the FY2001 to FY2016 dataset cuts
--                      names off, and a longer name a later row brings was not public then (ticket 63).
--   resolved_ventures  each joint venture of an award notice or a FY2001 to FY2016 row that the awards
--                      since FY2020 do not hold, keyed the same way, so a joint venture an award notice
--                      lists is the same supplier as the one the awards hold
-- An individual consultant keeps their own supplier ID but no name. No column scores, ranks or rates
-- a supplier, and nothing here is a supplier profile.
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
  WHERE c.joint_venture AND c.source = 'awards'
  GROUP BY c.supplier_id
),
resolved AS (
  SELECT *
  FROM strata.silver.supplier_resolution
  WHERE supplier_id IS NOT NULL
),
longest_name AS (
  SELECT supplier_id, name
  FROM resolved
  WHERE name IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY supplier_id ORDER BY public_from, length(name) DESC, name) = 1
),
resolved_firms AS (
  SELECT
    r.supplier_id,
    min(n.name) AS name,
    CASE WHEN count(DISTINCT r.country) = 1 THEN min(r.country) END AS country,
    max(CAST(r.individual_consultant AS INT)) AS individual,
    min(r.public_from) AS public_from
  FROM resolved AS r
  LEFT JOIN longest_name AS n ON n.supplier_id = r.supplier_id
  WHERE NOT EXISTS (SELECT 1 FROM members AS m WHERE m.supplier_id = r.supplier_id)
  GROUP BY r.supplier_id
),
firm_names AS (
  SELECT supplier_id, name, country FROM members
  UNION ALL
  SELECT supplier_id, name, country FROM resolved_firms
),
venture_members AS (
  SELECT r.joint_venture_id, r.supplier_id, min(r.public_from) AS public_from
  FROM resolved AS r
  WHERE r.joint_venture_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM ventures AS v WHERE v.supplier_id = r.joint_venture_id)
  GROUP BY r.joint_venture_id, r.supplier_id
),
resolved_ventures AS (
  SELECT
    v.joint_venture_id AS supplier_id,
    array_join(array_sort(collect_list(f.name)), ' / ') AS name,
    CASE WHEN count(DISTINCT f.country) = 1 THEN min(f.country) END AS country,
    count(*) AS member_count,
    min(v.public_from) AS public_from
  FROM venture_members AS v
  LEFT JOIN firm_names AS f ON f.supplier_id = v.supplier_id
  GROUP BY v.joint_venture_id
),
every_supplier AS (
  SELECT
    supplier_id,
    CASE WHEN individual = 1 THEN NULL ELSE name END AS name,
    country,
    CASE WHEN individual = 1 THEN 'individual consultant' ELSE 'firm' END AS kind,
    CAST(1 AS INT) AS member_count,
    public_from
  FROM members
  UNION ALL
  SELECT supplier_id, name, country, 'joint venture', CAST(member_count AS INT), public_from
  FROM ventures
  UNION ALL
  SELECT
    supplier_id,
    CASE WHEN individual = 1 THEN NULL ELSE name END,
    country,
    CASE WHEN individual = 1 THEN 'individual consultant' ELSE 'firm' END,
    CAST(1 AS INT),
    public_from
  FROM resolved_firms
  UNION ALL
  SELECT supplier_id, name, country, 'joint venture', CAST(member_count AS INT), public_from
  FROM resolved_ventures
)
SELECT
  supplier_id,
  name,
  country,
  kind,
  member_count,
  CASE WHEN supplier_id LIKE 'N-%' OR supplier_id LIKE '%-N-%' THEN 'name' ELSE 'step_supplier_id' END AS resolved_on,
  public_from
FROM every_supplier
