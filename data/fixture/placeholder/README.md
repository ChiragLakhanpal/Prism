# Placeholder fixture

These rows stand in for the real fixture until ticket 05 records the demo plan and the showcase project and the lakehouse run builds the tables from them. Each CSV file here becomes the table `strata.placeholder.<file name>` in `data/out/fixture.duckdb`, which `gates/build_fixture.py` builds at the start of every gate run.

`plan_rows.csv` holds five packages from the Northern Water Works Development Agency's October 9, 2026 Procurement Plan for P156634. Every value comes from the spec's Testing Decisions (`.scratch/strata/spec.md`), and a blank cell means the spec does not state that value. The column names follow STEP's fields: Activity Reference No., Method, Estimated Amount (US$), Actual Amount (US$) and Process Status. The `public_from` column is the date the plan became public (ADR 0002).
