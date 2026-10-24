-- Each source the nightly job fetches holds every record its API reported at the last run: the
-- coverage_rows measure for the source as a whole (subject all) counts the records held, once in
-- each request they came back in, and its denominator is the total each request reported. It
-- returns true or false rather than the counts, so it holds on the fixture and on the workspace
-- alike. Run it on the warehouse, after the job has run, with:
-- uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- expect: source,complete
-- expect: awards,true
-- expect: awards_fy2001_2016,true
-- expect: cpia,true
-- expect: ibrd_loan_history,true
-- expect: ibrd_loans,true
-- expect: ida_credit_history,true
-- expect: ida_credits,true
-- expect: ieg_ratings,true
-- expect: notices,true
-- expect: projects,true
-- expect: wgi,true
WITH last_run AS (
  SELECT run_id
  FROM strata.ops.data_readiness
  WHERE measure = 'coverage_rows' AND subject = 'all'
  ORDER BY measured_at DESC
  LIMIT 1
)
SELECT d.source, d.count = d.denominator AS complete
FROM strata.ops.data_readiness AS d
JOIN last_run AS r ON r.run_id = d.run_id
WHERE d.measure = 'coverage_rows' AND d.subject = 'all'
ORDER BY d.source
