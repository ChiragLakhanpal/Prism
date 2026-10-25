-- strata.gold.edge: every link between strata (ticket 22; ADR 0004). The keyed links come from the keys the
-- records share: a project and its country, its packages (from its notices, contracts and Procurement Plans),
-- its contracts and its documents; a package and its notices and contracts; a contract and its suppliers; an
-- award notice and the suppliers its awarded bidders resolved to; a document and its passages. The scored
-- links, appeared_together, come from strata.silver.contract_passage_links, which the relink task scores
-- first (strata.knowledge.links). Each link is public from the later of its two ends' public dates. The relink
-- task syncs this table; it is not in strata.lakehouse.gold.ORDER, because the passages it links are read
-- after bronze_to_gold.
-- key: kind, from_id, to_id
WITH packages AS (
  SELECT project_id, step_reference, public_from
  FROM strata.gold.package
  WHERE project_id IS NOT NULL
  UNION ALL
  SELECT project_id, activity_reference_no AS step_reference, public_from
  FROM strata.silver.plan_rows
),
contract_suppliers AS (
  SELECT contract_id, supplier_id
  FROM strata.gold.contract
  WHERE supplier_id IS NOT NULL
  UNION ALL
  SELECT contract_id, supplier_id
  FROM strata.gold.contract_supplier
),
keyed AS (
  SELECT 'borrows' AS kind, concat('strata.gold.project:', project_id) AS from_id, 'project' AS from_kind,
    concat('strata.gold.country:', country_code) AS to_id, 'country' AS to_kind, project_id, public_from
  FROM strata.gold.project
  WHERE country_code IS NOT NULL
  UNION ALL
  SELECT 'plans', concat('strata.gold.project:', project_id), 'project',
    concat('strata.gold.package:', step_reference), 'package', project_id, public_from
  FROM packages
  UNION ALL
  SELECT 'has', concat('strata.gold.project:', project_id), 'project',
    concat('strata.gold.contract:', contract_id), 'contract', project_id, public_from
  FROM strata.gold.contract
  WHERE project_id IS NOT NULL
  UNION ALL
  SELECT 'advertised_in', concat('strata.gold.package:', step_reference), 'package',
    concat('strata.gold.notice:', notice_id), 'notice', project_id, public_from
  FROM strata.gold.notice
  WHERE step_reference IS NOT NULL AND notice_type <> 'Contract Award'
  UNION ALL
  SELECT 'awarded_as', concat('strata.gold.package:', step_reference), 'package',
    concat('strata.gold.contract:', contract_id), 'contract', project_id, public_from
  FROM strata.gold.contract
  WHERE step_reference IS NOT NULL
  UNION ALL
  SELECT 'signed_by', concat('strata.gold.contract:', c.contract_id), 'contract',
    concat('strata.gold.supplier:', s.supplier_id), 'supplier', c.project_id, c.public_from
  FROM contract_suppliers AS s
  JOIN strata.gold.contract AS c ON c.contract_id = s.contract_id
  UNION ALL
  SELECT 'lists_bidders', concat('strata.gold.notice:', r.source_key), 'notice',
    concat('strata.gold.supplier:', r.supplier_id), 'supplier', r.project_id, r.public_from
  FROM strata.silver.supplier_resolution AS r
  WHERE r.source = 'notices' AND r.supplier_id IS NOT NULL
  UNION ALL
  SELECT 'described_in', concat('strata.gold.project:', project_id), 'project',
    concat('strata.silver.documents:', document_id), 'document', project_id, public_from
  FROM strata.silver.documents
  UNION ALL
  SELECT 'described_in', concat('strata.gold.project:', project_id), 'project',
    concat('strata.silver.plan_versions:', document_id), 'document', project_id, public_from
  FROM strata.silver.plan_versions
  UNION ALL
  SELECT 'has',
    CASE WHEN doc_key IS NULL THEN concat('strata.gold.notice:', document_id)
      ELSE concat('strata.silver.documents:', document_id) END,
    CASE WHEN doc_key IS NULL THEN 'notice' ELSE 'document' END,
    concat('strata.gold.passage:', passage_id), 'passage', project_id, public_from
  FROM strata.gold.passage
)
SELECT
  kind,
  from_id,
  min(from_kind) AS from_kind,
  to_id,
  min(to_kind) AS to_kind,
  min(project_id) AS project_id,
  CAST(NULL AS DECIMAL(4, 2)) AS score,
  CAST(NULL AS DECIMAL(4, 2)) AS score_project,
  CAST(NULL AS DECIMAL(4, 2)) AS score_sector,
  CAST(NULL AS DECIMAL(4, 2)) AS score_time,
  CAST(NULL AS DECIMAL(4, 2)) AS score_text,
  CAST(NULL AS DECIMAL(4, 2)) AS score_mentions,
  CAST(NULL AS INT) AS months_apart,
  CAST(NULL AS STRING) AS time_direction,
  CAST(NULL AS STRING) AS sector_code,
  CAST(NULL AS STRING) AS sector_name,
  CAST(NULL AS STRING) AS category,
  CAST(NULL AS STRING) AS matched_terms,
  CAST(NULL AS STRING) AS mentions,
  CAST(NULL AS DATE) AS scored_on,
  min(public_from) AS public_from
FROM keyed
WHERE public_from IS NOT NULL
GROUP BY kind, from_id, to_id
UNION ALL
SELECT
  'appeared_together' AS kind,
  concat('strata.gold.contract:', contract_id) AS from_id,
  'contract' AS from_kind,
  concat('strata.gold.passage:', passage_id) AS to_id,
  'passage' AS to_kind,
  project_id,
  score,
  score_project,
  score_sector,
  score_time,
  score_text,
  score_mentions,
  months_apart,
  time_direction,
  sector_code,
  sector_name,
  category,
  matched_terms,
  mentions,
  scored_on,
  public_from
FROM strata.silver.contract_passage_links
