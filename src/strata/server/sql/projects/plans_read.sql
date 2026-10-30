-- A project's Packages (ticket 134): each implementing agency's latest Procurement Plan whose STEP tables the
-- layout parser read (it has a parse_reason), public by the as-of date, with how many activities it lists. A plan
-- read with no rows is still a plan I read, so Packages names it instead of saying I haven't read a plan.
-- Agencies come with the newest plan first.
WITH read_versions AS (
  SELECT
    v.document_id,
    v.implementing_agency,
    v.plan_date,
    v.public_from
  FROM strata.silver.plan_versions AS v
  WHERE v.project_id = :project_id
    AND v.public_from <= :as_of
    AND v.implementing_agency IS NOT NULL
    AND v.parse_reason IS NOT NULL
),
latest AS (
  SELECT *
  FROM read_versions
  QUALIFY row_number() OVER (PARTITION BY implementing_agency ORDER BY plan_date DESC, public_from DESC,
                                                                        document_id DESC) = 1
)
SELECT
  l.implementing_agency,
  l.plan_date,
  (SELECT count(*) FROM strata.silver.plan_rows AS r
   WHERE r.document_id = l.document_id AND r.public_from <= :as_of) AS activities
FROM latest AS l
ORDER BY l.plan_date DESC, l.implementing_agency
