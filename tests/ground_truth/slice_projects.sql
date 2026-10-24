-- The slice's projects, as its criteria select them from strata.gold.project (config/slice.toml: the water
-- and transport projects of Kenya, Bangladesh, Vietnam and Pakistan with a Board date in fiscal 2012 to
-- 2025), counted in plain SQL apart from the document run's own code, agree with the count the run
-- recorded in strata.ops.data_readiness (measure slice_projects), on every engine (ticket 18, criterion 1).
-- The count itself differs by engine: the fixture's is tests/ground_truth/values.toml's
-- [stress_shelf.slice_projects], 17, which tests/test_document_slice.py checks, and the warehouse's is
-- the live slice's, whose difference from docs/PLAN.md's 128 the measure's detail gives.
-- engines: duckdb, databricks
-- param: countries = KE,BD,VN,PK
-- param: sectors = water,transport
-- param: first = 2012
-- param: last = 2025
-- expect: agree
-- expect: true
SELECT
  (SELECT count(*) FROM strata.gold.project
   WHERE array_contains(split(:countries, ','), country_code)
     AND array_contains(split(:sectors, ','), sector)
     AND approval_fiscal_year BETWEEN CAST(:first AS INT) AND CAST(:last AS INT))
  = (SELECT max_by(count, measured_at) FROM strata.ops.data_readiness
     WHERE source = 'documents' AND subject = 'all' AND measure = 'slice_projects') AS agree
