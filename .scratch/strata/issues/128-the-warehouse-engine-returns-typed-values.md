# 128: The warehouse engine returns typed values, so a page that works on the fixture works on the workspace

**What to build:** On October 29, 2026 the owner opened https://strata-7405609289499029.9.azure.databricksapps.com/projects/P156634/timeline and got the error page (reference 4ea75fa73165f2f36e32f9eadbb1c79c), while the same route answers in 0.4 s on the local copy. Run against the warehouse by hand, the route fails in `src/strata/server/timeline.py` line 215 with `TypeError: '>' not supported between instances of 'str' and 'int'` at `"reissued": (row["version"] or 1) > 1`: the warehouse engine (`src/strata/lakehouse/engine.py`, `WarehouseEngine.run`) asks the statements API for `JSON_ARRAY` with `INLINE` disposition, which returns every value as text, and nothing types the rows afterwards, so an INT column arrives as "2" on the workspace and as 2 from the fixture's DuckDB. Thirty-seven call sites cast by hand (`int(row[...])`, `Decimal(row[...])`), and the ones that forgot fail only live, which no gate catches. Make the engine type every value from the statement's manifest (the `schema.columns[].type_name` the API returns with the result): BIGINT, INT, SMALLINT and TINYINT to int; DECIMAL to Decimal; DOUBLE and FLOAT to float; BOOLEAN to bool; DATE to date; TIMESTAMP to datetime; STRING and the rest unchanged; NULL stays None; and do it in one place (`engine.py`), with a test that feeds a recorded manifest and rows and checks each type, and a test that the fixture engine and the warehouse engine give the same Python types for one query over the same columns. Then remove the hand casts that the typing makes redundant where they would now double-convert (keep ones that guard None), and the timeline route needs no change of its own. Prove it: the timeline test suite stays green on the fixture; a new test replays the live P156634 timeline rows (recorded with their manifest, versions as text) through the engine and the route; the live proof is the orchestrator's: `GET /api/projects/P156634/timeline` on the App answers 200 after the redeploy, recorded in the catch-up file. Keep the gate under 150 seconds.

Read first: `src/strata/lakehouse/engine.py` (`WarehouseEngine.run`, `Result`, the fixture engine's rows), the statements API's result manifest (the `manifest.schema.columns` in the reply the engine already receives), `src/strata/server/timeline.py` (`_report`, line 215), `grep -rn "int(row\[\|Decimal(row\[" src/strata` for the hand casts, and the orchestrator's note of October 29 in the catch-up file with the traceback.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] The warehouse engine types every value from the statement's manifest in one place, with a test per type (int, Decimal, float, bool, date, datetime, text, None) over a recorded manifest and rows, and a test that the fixture engine and the warehouse engine agree on Python types for the same columns.
- [ ] Hand casts that the typing makes redundant are removed (those that guard None stay), and the timeline route's recorded live rows (versions as text) replay through the engine and the route without error.
- [ ] On the paid workspace, after the merge and the App redeploy, `GET /api/projects/P156634/timeline` answers 200 and the page renders (recorded in the catch-up file under this ticket).

## Comments

- October 29, 2026, orchestrator: opened at 12:20 PDT from the owner's report of the timeline page; the traceback came from running the route against the warehouse by hand.
