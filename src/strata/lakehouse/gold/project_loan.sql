-- strata.gold.project_loan: the financing numbers in each project's newest page: its loans and credits,
-- and its IDA grants, trust funds and the other numbers its record names, each with its financier.
-- key: loan_number, project_id
WITH newest AS (
  SELECT project_id, page_hash
  FROM strata.silver.projects
  QUALIFY row_number() OVER (PARTITION BY project_id ORDER BY fetched_at DESC, page_hash) = 1
)
SELECT
  l.loan_number,
  l.project_id,
  min(l.loan_number_as_written) AS loan_number_as_written,
  min(l.public_from) AS public_from,
  min(l.financier) AS financier
FROM strata.silver.project_loans AS l
JOIN newest AS n ON n.project_id = l.project_id AND n.page_hash = l.page_hash
GROUP BY l.loan_number, l.project_id
