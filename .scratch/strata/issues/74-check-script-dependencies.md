# 74: The bundle check script's inline dependencies match the nightly job's, so same-rows runs locally again

**What to build:** `ops/bundle/check.py same-rows` crashes locally since the nightly fixture run gained splink and the score task: the script's inline `# dependencies` list (line 3) holds databricks-sdk, pyyaml, duckdb, sqlglot and pytz only, so `_local_engine()` dies with `ModuleNotFoundError: No module named 'splink'` (`src/strata/lakehouse/resolve.py` line 463 through `matching.py` line 126), and with splink added, numpy (`time_estimate.py` line 182 through `scoring.py` line 129). On October 26, 2026 the second session ran it with `uv run --with` for the missing packages to get the day's comparison. Add the packages the local fixture run imports to the script's inline list at the pins `pyproject.toml` holds (splink 5.0.0, xgboost 3.4.1 with xgboost-cpu on Linux, numpy, py3langid 0.3.0, pypdf), and add a test that keeps the list in step with `pyproject.toml`: for each package the lakehouse modules import at module level, the script's list holds it at the same pin, so the next task the nightly gains cannot break the script again. Do the same for `ops/agent/refuse_live.py` and `ops/agent/ask_live.py`, whose lists lack py3langid (the parked follow-up from ticket 42).

Read first: `ops/bundle/check.py` (the header and `_local_engine()`), `ops/bundle/tests/`, `pyproject.toml` (dependencies), `src/strata/lakehouse/resolve.py` line 463, `src/strata/lakehouse/scoring.py` line 129, `ops/agent/refuse_live.py` and `ops/agent/ask_live.py` (their headers), the catch-up file's same-rows blocks of October 26.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** ops
**Phase:** P2
**Design review:** no

- [ ] `uv run --script ops/bundle/check.py same-rows` runs its local half on the fixture without `--with`, proven by a test that imports the script's local engine in a process started with the script's own inline list (or that compares the list with the modules' imports) and by the second session's next run.
- [ ] The inline pins of `check.py`, `refuse_live.py` and `ask_live.py` match `pyproject.toml`'s for the same packages, and a test keeps them matched.
- [ ] The second session's next same-rows run from a snapshot runs without `--with` (recorded in the catch-up file under this ticket).

## Comments

- October 26, 2026, orchestrator: opened at 02:48 PDT from the second session's finding of 09:12 UTC. Small, and on the path of every same-rows comparison the demo-ready check needs.
