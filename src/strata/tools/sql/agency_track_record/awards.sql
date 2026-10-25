-- agency_track_record: the contracts the awards dataset holds for the packages the call names (:refs, STEP
-- references joined by commas, which no reference contains), public by the as-of date (ADR 0002), so the tool can
-- name a package its plan shows unsigned while the awards dataset shows a signed contract. The earliest signing
-- per package comes first.
SELECT
  c.step_reference,
  c.contract_id,
  c.contract_signing_date,
  c.public_from
FROM strata.gold.contract AS c
WHERE c.source <> 'notices'
  AND c.public_from <= :as_of
  AND c.step_reference IS NOT NULL
  AND array_contains(split(:refs, ','), c.step_reference)
ORDER BY c.step_reference, c.contract_signing_date, c.contract_id
