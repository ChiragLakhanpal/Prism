-- strata.gold.project_closing_date: how each project's closing date moved, month by month, from the
-- monthly loan history (strata.silver.loan_history, the newest fetch of each loan and month). A
-- project's closing date in a month is the latest closing date any of its loans reported that
-- month. One row for the first month of its history, then one for each month it changed.
-- key: project_id, reported_on
WITH latest AS (
  SELECT project_id, loan_number, end_of_period, closing_date
  FROM strata.silver.loan_history
  WHERE project_id IS NOT NULL AND end_of_period IS NOT NULL AND closing_date IS NOT NULL
  QUALIFY row_number() OVER (PARTITION BY loan_number, end_of_period ORDER BY fetched_at DESC, page_hash) = 1
),
monthly AS (
  SELECT project_id, end_of_period, max(closing_date) AS closing_date
  FROM latest
  GROUP BY project_id, end_of_period
),
ordered AS (
  SELECT
    project_id,
    end_of_period,
    closing_date,
    lag(closing_date) OVER (PARTITION BY project_id ORDER BY end_of_period) AS previous_closing_date
  FROM monthly
)
SELECT
  project_id,
  closing_date,
  previous_closing_date,
  end_of_period AS reported_on,
  end_of_period AS public_from
FROM ordered
WHERE previous_closing_date IS NULL OR previous_closing_date <> closing_date
