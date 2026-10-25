-- A four-hop path over the edge table, answered by recursive SQL (ticket 22; ADR 0004: paths are at most four
-- hops): from the supplier of IN-RRSMP-7431-CW-RFB, through its contract and its project, to paragraph 54 of the
-- project's completion report. The query walks every edge in either direction from the supplier, never
-- through a node twice, up to four hops, with only the edges public by the as-of date, and keeps the paths
-- that end at the paragraph through a project and a completion report.
--
-- The expected row comes from the records, not from the code: award notice OP00044090 awarded the contract to
-- AMIT CONSTRUCTION, with no STEP supplier ID (values.toml [award_notice_bids.showcase] and award-7431-signed);
-- gold keys a contract known from its award notice by the notice's id; the ICR of P130164 is document
-- 31525018 (values.toml icr-disclosed), and its paragraph 54 is the rebidding lesson (icr-para-54). The
-- supplier's own key is the one ticket 19 gives a supplier known only by name, so the query starts from its
-- name. DuckDB runs it in the gate. Whether the workspace's SQL warehouse runs WITH RECURSIVE is checked
-- there (docs/workspace-catchup.md), so this file names DuckDB only until it does.
-- param: supplier_name = AMIT CONSTRUCTION
-- param: passage_id = 31525018/v1/54
-- param: as_of = 2026-10-23
-- engines: duckdb
-- expect: supplier,contract,project,document,passage,hops
-- expect: AMIT CONSTRUCTION,OP00044090,P130164,31525018,31525018/v1/54,4
WITH RECURSIVE links AS (
  SELECT from_id AS node, to_id AS next_node
  FROM strata.gold.edge
  WHERE public_from <= CAST(:as_of AS DATE)
  UNION ALL
  SELECT to_id AS node, from_id AS next_node
  FROM strata.gold.edge
  WHERE public_from <= CAST(:as_of AS DATE)
),
start AS (
  SELECT concat('strata.gold.supplier:', supplier_id) AS node
  FROM strata.gold.supplier
  WHERE name = :supplier_name
),
paths (node, path, hops) AS (
  SELECT node, concat('|', node, '|'), 0
  FROM start
  UNION ALL
  SELECT l.next_node, concat(p.path, l.next_node, '|'), p.hops + 1
  FROM paths AS p
  JOIN links AS l ON l.node = p.node
  WHERE p.hops < 4 AND instr(p.path, concat('|', l.next_node, '|')) = 0
)
SELECT
  :supplier_name AS supplier,
  replace(split_part(path, '|', 3), 'strata.gold.contract:', '') AS contract,
  replace(split_part(path, '|', 4), 'strata.gold.project:', '') AS project,
  replace(split_part(path, '|', 5), 'strata.silver.documents:', '') AS document,
  replace(node, 'strata.gold.passage:', '') AS passage,
  hops
FROM paths
WHERE node = concat('strata.gold.passage:', :passage_id)
  AND split_part(path, '|', 3) LIKE 'strata.gold.contract:%'
  AND split_part(path, '|', 4) LIKE 'strata.gold.project:%'
  AND EXISTS (
    SELECT 1
    FROM strata.silver.documents AS d
    WHERE concat('strata.silver.documents:', d.document_id) = split_part(path, '|', 5)
      AND d.document_type = 'Implementation Completion and Results Report'
  )
