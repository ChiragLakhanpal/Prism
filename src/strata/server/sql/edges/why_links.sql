-- "Why this source" (ticket 22): every appeared_together edge into one passage (:passage, its evidence id) that was
-- public on the as-of date (ADR 0002), strongest first, with its contract, the contract's activity and its project's
-- state, so the drawer explains the link in words from the score's parts.
SELECT
  e.score,
  e.score_project,
  e.score_sector,
  e.score_time,
  e.score_text,
  e.score_mentions,
  e.months_apart,
  e.time_direction,
  e.sector_code,
  e.sector_name,
  e.category,
  e.matched_terms,
  e.mentions,
  c.contract_id,
  c.source,
  c.step_reference,
  c.wb_contract_number,
  c.award_notice_id,
  c.contract_signing_date,
  c.project_id,
  p.status AS project_status,
  p.closing_date AS project_closing_date
FROM strata.gold.edge AS e
JOIN strata.gold.contract AS c ON e.from_id = concat('strata.gold.contract:', c.contract_id)
LEFT JOIN strata.gold.project AS p ON p.project_id = c.project_id
WHERE e.kind = 'appeared_together'
  AND e.to_id = :passage
  AND e.public_from <= :as_of
ORDER BY e.score DESC, c.contract_signing_date, c.contract_id
