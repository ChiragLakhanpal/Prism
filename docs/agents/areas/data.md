# Area brief: data

Tickets with `Area: data` build ingestion, the medallion layers in the `strata` catalog, the data readiness measures, the nightly job, and the tables behind the AI/BI dashboard.

Read: `docs/PLAN.md` sections 2, 3, 4, 11, 12 and 14.

- Every table keeps its `public_from` date; assertions also keep the period they describe (ADR 0002).
- Ingestion is idempotent, by watermark and content hash. Bronze keeps API pages as received; bronze and silver rebuild from source and are never edited by hand.
- Notice contact names, emails and phone numbers are stripped at ingestion.
- Each step writes its data readiness measures (coverage, linked, read well, fresh) to `strata.ops`.
- SQL runs on both the local fixture and Databricks SQL, uses three-part names (`strata.<schema>.<table>`) and bound parameters only.
- Develop and test against the local fixture; the merger runs anything on the shared workspace.
- PLAN.md section 12 lists the Databricks behaviors that cost fairshare days; design around them from the start.
