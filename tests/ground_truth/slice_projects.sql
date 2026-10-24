-- The slice's projects, as its criteria select them from strata.gold.project (config/slice.toml: the water
-- and transport projects of Kenya, Bangladesh, Vietnam and Pakistan approved in fiscal 2012 to 2025),
-- written as plain SQL apart from the document run's own code, beside the count the run recorded in
-- strata.ops.data_readiness (measure slice_projects). The 17 are tests/ground_truth/values.toml's
-- [stress_shelf.slice_projects], read from the recorded projects file. On the warehouse the count is the
-- live slice's, so this file runs on DuckDB only; after the live document run, the same two numbers
-- must agree on the warehouse, and the measure's detail says how they differ from docs/PLAN.md's 128.
-- engines: duckdb
-- param: countries = KE,BD,VN,PK
-- param: sectors = water,transport
-- param: first = 2012
-- param: last = 2025
-- expect: selected,recorded
-- expect: 17,17
SELECT
  (SELECT count(*) FROM strata.gold.project
   WHERE array_contains(split(:countries, ','), country_code)
     AND array_contains(split(:sectors, ','), sector)
     AND approval_fiscal_year BETWEEN CAST(:first AS INT) AND CAST(:last AS INT)) AS selected,
  (SELECT max_by(count, measured_at) FROM strata.ops.data_readiness
   WHERE source = 'documents' AND subject = 'all' AND measure = 'slice_projects') AS recorded
