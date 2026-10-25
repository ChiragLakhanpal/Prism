-- Rebidding labels (ticket 28; src/strata/estimates/rebidding.py): every package whose specific procurement
-- notice was public on the as-of date and dated from :period_from, with what the records public then say about
-- whether it was advertised again. No field says so, so three sources do, and each is read only as it stood on
-- the as-of date (ADR 0002):
--
--   signed_on       its first contract in the awards dataset, public from its signing date, or else the
--                   Contract Signature Date of its Contract Award notice, public from the day the notice was
--                   published: find_comparables' rule (sql/find_comparables/candidates.sql), so a package
--                   signed only in its award notice is signed here too
--   bids_due        its specific procurement notice's submission deadline, from which the no-award wait runs
--   again_*         a later notice of the same type under the same STEP reference, on a later day: the activity
--                   was advertised again under its own reference. A notice whose status is Revised changes an
--                   earlier one and is no new advertisement.
--   process_status  Process Status in the newest plan version public on the as-of date that lists the package,
--                   never gold.package's newest, so a status published later never reaches an earlier date
--
-- A package's specific procurement notice is its first notice that is not a General Procurement Notice or a
-- Contract Award, where procurement cycle time starts. :refs, when set, keeps the packages it names (STEP
-- references joined by commas, which no reference contains).
WITH notices AS (
  SELECT notice_id, notice_type, notice_date, notice_status, step_reference, submission_deadline, public_from
  FROM strata.gold.notice
  WHERE step_reference IS NOT NULL AND public_from <= :as_of
    AND notice_type NOT IN ('General Procurement Notice', 'Contract Award')
),
first_notice AS (
  SELECT *
  FROM notices
  QUALIFY row_number() OVER (PARTITION BY step_reference ORDER BY notice_date, notice_id) = 1
),
again AS (
  SELECT later.step_reference, later.notice_id, later.notice_date, later.public_from
  FROM notices AS later
  JOIN first_notice AS f
    ON f.step_reference = later.step_reference AND f.notice_type = later.notice_type
   AND later.notice_date > f.notice_date
  WHERE coalesce(later.notice_status, '') <> 'Revised'
  QUALIFY row_number() OVER (PARTITION BY later.step_reference ORDER BY later.notice_date, later.notice_id) = 1
),
signings AS (
  SELECT step_reference, contract_signing_date AS signed_on
  FROM strata.gold.contract
  WHERE step_reference IS NOT NULL AND source <> 'notices' AND public_from <= :as_of
  UNION ALL
  SELECT step_reference, contract_signature_date AS signed_on
  FROM strata.gold.notice
  WHERE notice_type = 'Contract Award' AND contract_signature_date IS NOT NULL AND step_reference IS NOT NULL
    AND public_from <= :as_of
),
signed AS (
  SELECT step_reference, min(signed_on) AS signed_on
  FROM signings
  GROUP BY step_reference
),
listed AS (
  SELECT
    r.activity_reference_no AS step_reference,
    r.process_status,
    r.document_id,
    r.pdf_page,
    v.plan_date,
    v.public_from,
    v.implementing_agency
  FROM strata.silver.plan_rows AS r
  JOIN strata.silver.plan_versions AS v ON v.document_id = r.document_id
  WHERE v.public_from <= :as_of
  QUALIFY row_number() OVER (PARTITION BY r.activity_reference_no
                             ORDER BY v.plan_date DESC, v.public_from DESC, r.document_id DESC, r.pdf_page) = 1
)
SELECT
  f.step_reference,
  p.project_id,
  p.country_code,
  c.country_name,
  p.procurement_category,
  p.procurement_method,
  f.notice_id,
  f.notice_type,
  f.notice_date,
  f.submission_deadline AS bids_due,
  f.public_from AS notice_public_from,
  s.signed_on,
  a.notice_id AS again_notice_id,
  a.notice_date AS again_notice_date,
  a.public_from AS again_public_from,
  l.process_status,
  l.document_id AS plan_document_id,
  l.plan_date,
  l.public_from AS plan_public_from,
  l.implementing_agency,
  l.pdf_page AS plan_pdf_page,
  greatest(f.public_from, p.public_from) AS public_from
FROM first_notice AS f
JOIN strata.gold.package AS p ON p.step_reference = f.step_reference
LEFT JOIN strata.gold.country AS c ON c.country_code = p.country_code
LEFT JOIN signed AS s ON s.step_reference = f.step_reference
LEFT JOIN again AS a ON a.step_reference = f.step_reference
LEFT JOIN listed AS l ON l.step_reference = f.step_reference
WHERE f.notice_date >= :period_from
  AND p.public_from <= :as_of
  AND (CAST(:refs AS STRING) IS NULL OR array_contains(split(:refs, ','), f.step_reference))
ORDER BY f.step_reference
