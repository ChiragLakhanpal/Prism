-- Delay per STEP step (GLOSSARY.md, "Delay"): the days from a step's first published planned date
-- to the date it actually happened. This file is the one definition of delay.
--
-- The first published planned date is the step's Planned date in the activity's first listing, the
-- earliest plan version read that lists it, across every implementing agency's series. The plan
-- reader decides the first listing once and marks it in silver.plan_listings (is_first_listing).
-- Plan updates re-date steps, so a later version's Planned date is never used instead. When the
-- first listing has no Planned date for the step, or its tables have not been read yet, the first
-- planned date and the delay stay empty. When an older listed version went unread, the delay is
-- still measured from the first listing read, and first_listing_confirmed says it is not confirmed.
--
-- A row rests on two versions, its own and the first listing, so it is public only once both are
-- (ADR 0002): its public_from is the later of the two. An earlier-dated plan can be disclosed after
-- a later-dated one, and an as-of answer must not see a delay measured from a plan not yet public.
INSERT INTO strata.silver.plan_step_delays (
  document_id, project_id, activity_reference_no, step, step_order, planned_on, actual_on,
  first_planned_on, first_planned_document, first_planned_plan_date, first_listing_confirmed, delay_days,
  public_from
)
SELECT
  s.document_id,
  s.project_id,
  s.activity_reference_no,
  s.step,
  s.step_order,
  s.planned_on,
  s.actual_on,
  f.planned_on AS first_planned_on,
  l.document_id AS first_planned_document,
  v.plan_date AS first_planned_plan_date,
  l.first_listing_confirmed,
  CASE WHEN s.actual_on IS NOT NULL AND f.planned_on IS NOT NULL
       THEN CAST(datediff(s.actual_on, f.planned_on) AS INT) END AS delay_days,
  GREATEST(s.public_from, v.public_from) AS public_from
FROM strata.silver.plan_steps AS s
LEFT JOIN strata.silver.plan_listings AS l
  ON l.project_id = s.project_id
  AND l.activity_reference_no = s.activity_reference_no
  AND l.is_first_listing
LEFT JOIN strata.silver.plan_versions AS v ON v.document_id = l.document_id
LEFT JOIN strata.silver.plan_steps AS f
  ON f.document_id = l.document_id
  AND f.activity_reference_no = l.activity_reference_no
  AND f.step = s.step
WHERE s.project_id = :project_id
