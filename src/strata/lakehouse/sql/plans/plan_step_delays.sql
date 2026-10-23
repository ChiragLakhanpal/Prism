-- Delay per STEP step (GLOSSARY.md, "Delay"): the days from a step's first published planned date
-- to the date it actually happened. This file is the one definition of delay.
--
-- The first published planned date is the step's Planned date in the earliest plan version that
-- lists the activity, across every implementing agency's series, because an activity can move from
-- one agency's plan to another's. Plan updates re-date steps, so a later version's Planned date is
-- never used instead. When that earliest version has no Planned date for the step, or its tables
-- have not been read yet, the first planned date and the delay stay empty.
INSERT INTO strata.silver.plan_step_delays (
  document_id, project_id, activity_reference_no, step, step_order, planned_on, actual_on,
  first_planned_on, first_planned_document, first_planned_plan_date, delay_days, public_from
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
  f.document_id AS first_planned_document,
  f.plan_date AS first_planned_plan_date,
  CASE WHEN s.actual_on IS NOT NULL AND f.planned_on IS NOT NULL
       THEN CAST(datediff(s.actual_on, f.planned_on) AS INT) END AS delay_days,
  s.public_from
FROM strata.silver.plan_steps AS s
LEFT JOIN (
  SELECT e.activity_reference_no, e.document_id, e.plan_date, p.step, p.planned_on
  FROM (
    SELECT
      l.activity_reference_no,
      v.document_id,
      v.plan_date,
      ROW_NUMBER() OVER (PARTITION BY l.activity_reference_no
                         ORDER BY v.plan_date, v.public_from, v.document_id) AS listed
    FROM strata.silver.plan_listings AS l
    JOIN strata.silver.plan_versions AS v ON v.document_id = l.document_id
    WHERE l.project_id = :project_id
  ) AS e
  JOIN strata.silver.plan_steps AS p
    ON p.document_id = e.document_id AND p.activity_reference_no = e.activity_reference_no
  WHERE e.listed = 1
) AS f
  ON f.activity_reference_no = s.activity_reference_no AND f.step = s.step
WHERE s.project_id = :project_id
