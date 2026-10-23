# 17: Every structured source, for every country, kept as published

**What to build:** Every structured source in PLAN.md section 3 is in gold for every country, refreshed incrementally, with each published version kept where a source revises values in place. New source-registry entries: contract awards since FY2020 for all countries; contract awards FY2001–16 (prior review only, frozen since March 2022, with free-text references); IEG ratings; loans and credits, latest (disbursed and canceled amounts) and monthly history for the slice (closing-date history); procurement notices and projects for all countries; CPIA (IDA countries only) and WGI, each published version kept and joined lagged to what was public at the time. The FY2017–19 gap is filled from award notices, in local currency, and labeled as such. The two sector taxonomies map to one. Duplicate ISR ratings from the projects API are removed. The nightly job's fetch and bronze-to-gold tasks now do real work, and every source's data readiness measures appear on the Data readiness page.

Read first: docs/PLAN.md sections 3 and 4; ADR 0002; docs/agents/areas/data.md.

**Blocked by:** 07 (Kenya's procurement records, bronze to gold)

**Status:** in-progress
**Area:** data
**Phase:** P2
**Design review:** no

- [ ] For each source, the row count recorded in strata.ops equals the total the API reported at fetch time.
- [ ] FY2017–19 has contract rows built from award notices, each labeled as local currency from notices, and the count per fiscal year equals a direct count of award notices for that year.
- [ ] A fixture indicator revised in place keeps both versions, and a join as of a date between them returns the earlier value.
- [ ] P156634's closing-date history shows the closing date moved three times since 2022, matching the loan history records.
- [ ] Awards that use ICB, NCB, Shopping or Direct Contracting are stored with the current Regulations' names and keep the original wording.
- [ ] Every slice project maps to one sector in the single taxonomy, with no project left unmapped.
- [ ] Structured data in strata stays under 0.5 GB, measured and recorded.
- [ ] A second nightly run with no source changes adds no bronze rows, and each new source appears on the Data readiness page with coverage, linked and fresh measures.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/17-structured-sources-everywhere, as soon as ticket 07 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures.
