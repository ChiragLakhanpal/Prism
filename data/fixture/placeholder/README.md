# Placeholder fixture

These rows stand in for plan rows that the lakehouse run will read from the recorded plans in `../recorded/`. Ticket 05 recorded those plans, and ticket 08 replaces these rows with the ones it reads from them. At the start of every gate run, `gates/build_fixture.py` loads each CSV file here into the schema `placeholder` of `data/out/fixture.duckdb`. The tests attach that file as `strata`, so they query `plan_rows.csv` as `strata.placeholder.plan_rows`.

`plan_rows.csv` holds five packages from the Northern Water Works Development Agency's October 9, 2026 Procurement Plan for P156634. Every value comes from the spec's Testing Decisions (`.scratch/strata/spec.md`), and a blank cell means the spec does not state that value. The column names follow STEP's fields: Activity Reference No., Method, Estimated Amount (US$), Actual Amount (US$) and Process Status. The `public_from` column is the date the plan became public (ADR 0002).
