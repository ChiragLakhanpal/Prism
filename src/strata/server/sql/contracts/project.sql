-- A project's contracts (ticket 138): its rows in strata.gold.contract that were public on the as-of date (ADR
-- 0002), from every source that table holds. The Timeline tab's Records lane and the Connections tab both read them
-- here, so the two tabs count a project's contracts the same way. Each comes with its source, its STEP reference
-- (the FY2001 to FY2016 awards seldom carry one) and its signing date.
SELECT
  c.contract_id,
  c.source,
  c.step_reference,
  c.contract_signing_date,
  c.public_from
FROM strata.gold.contract AS c
WHERE c.project_id = :project_id
  AND c.public_from <= :as_of
ORDER BY c.contract_id
