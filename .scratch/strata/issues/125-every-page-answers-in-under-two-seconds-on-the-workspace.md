# 125: Every page answers in under two seconds on the workspace: one round trip, read together, kept for the day

**What to build:** On October 29, 2026 the owner reported that each lookup and tab load on the App takes one to five seconds, and the traces show why: a page's statements run one after another through the SQL warehouse's statements API at 1.7 to 3.4 seconds each (`POST /api/2.0/sql/statements/`, p50 2.2 s over the last two days), so `GET /api/projects/P156634/timeline` ran six statements in 16.5 s and `/summary` took 18.3 s, while the same routes answer in 0.25 to 0.4 s on the local copy. The warehouse (serverless, 2X-Small, auto-stop ten minutes) also pays a cold start after idle, and the warehouse was the largest cost line of the week (106 DBUs). Make every page answer in under two seconds on the workspace, warm, and under five seconds cold, by three means that each live in one place: (1) `src/strata/lakehouse/engine.py`'s warehouse engine runs the statements a page issues together, not one after another (a page's reads are independent `engine.run` calls; give the engine a `run_many` that posts them at once and waits once, and move each route's reads onto it; the statements API's `wait_timeout` and polling interval are tuned so a 300 ms statement does not cost two seconds of waiting); (2) a page's answer is kept for the as-of day per viewer role in the App's memory (`src/strata/server/app.py`'s `read_for`), with a size bound and a `Cache-Control` the browser respects, cleared by the nightly's end or by the age the thresholds file names (`app.page_cache_seconds`), so the second view of any page is instant; (3) the demo's own pages are warmed at startup and every hour: the projects and packages `config/demo.toml` lists (the walkthrough's cases), so a presenter never meets a cold page. Prove it on the fixture with tests that count a route's warehouse calls (one batch per page), that a repeated read within the window issues none, and that a changed as-of date issues a fresh read; the live proof is the orchestrator's: `GET /api/projects/P156634/summary`, `/timeline` and `/packages` and `/api/packages/KE-NWWDA-541055-CW-RFB` each under two seconds on a second read, recorded with their timings in the catch-up file.

Read first: `src/strata/lakehouse/engine.py` (`WarehouseEngine.run`, the statements API call and its waits), `src/strata/server/app.py` (`read_for`, `as_viewer`, the route bodies), `src/strata/server/timeline.py` and `summary.py` (the statements each page issues), `config/thresholds.toml` [app], the App Insights numbers in the catch-up file's block of October 29 (the owner's slow-pages report), and the local copy's timings (0.25 to 0.4 s) as the floor.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** server
**Phase:** P4
**Design review:** no

- [ ] A page's warehouse reads run together: a fixture test counts one statements-API batch per page for the summary, timeline, packages and package routes, and the engine's waits are tuned in one place (`config/thresholds.toml`).
- [ ] A page's answer is kept per as-of day and viewer role for `app.page_cache_seconds`, bounded in size, and a repeated read within the window issues no warehouse call (a test), while a different as-of date or role does (a test); the browser gets a matching `Cache-Control`.
- [ ] The demo's cases (`config/demo.toml`) are warmed at startup and hourly (a test with a fake clock); on the workspace, the four routes above answer in under two seconds on a second read and under five seconds cold, recorded in the catch-up file.

## Comments

- October 29, 2026, orchestrator: opened at 12:15 PDT from the owner's report that every lookup takes seconds; the traces named the cause (statements one after another at two seconds each).
