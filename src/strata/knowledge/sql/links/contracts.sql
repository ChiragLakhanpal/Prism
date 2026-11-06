-- The link scorer's contracts (ticket 22): every contract of a project whose reports the passage reader holds,
-- with what the scorer matches a paragraph against, its project's sector in Prism's taxonomy (which the
-- passages carry too) and the project's sector with the largest share, from its newest projects API page.
WITH sectors AS (
  SELECT project_id, sector_code, sector_name
  FROM strata.silver.project_sectors
  QUALIFY row_number() OVER (PARTITION BY project_id ORDER BY fetched_at DESC, share_percent DESC, sector_code) = 1
)
SELECT
  c.contract_id,
  c.project_id,
  c.step_reference,
  c.borrower_contract_reference_number,
  c.wb_contract_number,
  c.contract_description,
  c.procurement_category,
  c.contract_signing_date,
  c.public_from,
  p.sector,
  s.sector_code,
  s.sector_name
FROM strata.gold.contract AS c
JOIN strata.gold.project AS p ON p.project_id = c.project_id
LEFT JOIN sectors AS s ON s.project_id = c.project_id
WHERE EXISTS (
  SELECT 1
  FROM strata.gold.passage AS x
  WHERE x.project_id = c.project_id AND x.doc_key IS NOT NULL
)
ORDER BY c.project_id, c.contract_id
