# 04: The strata catalog and the bundle skeleton

**What to build:** One command deploys Strata's catalog and an empty nightly job to the shared workspace, and the same table definitions build on DuckDB offline. The Declarative Automation Bundle declares the strata catalog with its bronze, silver, gold and ops schemas and the bronze files volume, and a nightly job whose tasks run in PLAN.md section 11's order (fetch by watermark, bronze to gold, parse and embed, sync the index, re-link, propose lessons, detect disagreements, score, measure data readiness, refresh drafts). Each task is a no-op for now that records its run in strata.ops. The deploy also grants read access on the catalog to the people who will use the app, so later tickets can query as each viewer. The schedule sits at an hour that does not overlap fairshare's nightly job (check fairshare's schedule, as PLAN.md section 18 asks) or review hours.

This ticket also lands the engine adapter and transpile step that let one plain SQL query run unchanged on Databricks and on DuckDB, a schema test that enforces ADR 0002, and four of the spec's single places as empty but loadable files: the source registry, the slice file, the model file and the thresholds file.

Read first: docs/PLAN.md sections 2, 4 and 11; ADRs 0002 and 0004; the spec's "Ten single places" and "Data and the lakehouse run".

**Blocked by:** 01 (Repo scaffold with fairshare's rules, hooks, shell and the offline gate); 03 (Credentials, Azure caps and the day-one tests)

**Status:** ready-for-agent
**Area:** data
**Phase:** P0
**Design review:** no

- [ ] One deploy command creates the catalog, its four schemas and the volume; running it a second time reports no changes.
- [ ] A manual run of the nightly job completes and writes one pipeline-run row per task to strata.ops, in the order PLAN.md section 11 gives.
- [ ] The bundle's notes record fairshare's schedule and Strata's, and Strata's window does not overlap fairshare's given the measured duration of both jobs.
- [ ] One sample query returns identical rows on DuckDB in the gate and on the workspace's SQL warehouse.
- [ ] The gate fails when a table definition without a public_from column is added and passes again when it is removed.
- [ ] The source registry, slice file, model file and thresholds file each load through one tested function; the slice file names Kenya, Bangladesh, Vietnam and Pakistan, water and transport, FY2012–2025, P130164 as the showcase and the NWWDA plan of P156634 as the demo plan.
- [ ] A listing of fairshare's catalog taken before and after the deploy is identical.
