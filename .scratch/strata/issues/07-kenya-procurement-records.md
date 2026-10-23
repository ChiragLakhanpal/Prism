# 07: Kenya's procurement records, bronze to gold, with data readiness measures

**What to build:** Kenya's procurement records flow from the World Bank APIs into gold tables on the workspace, and the same transforms build the fixture database offline that seams 2 and 3 use. Three sources are registered, one entry each in the source registry: contract awards since FY2020 (Finances One DS00005), procurement notices and projects (both from the v3 search APIs). Fetching is idempotent, by watermark and content hash. Bronze keeps pages as received with fetch time and source. Silver types and cleans them on purpose: fiscal years run July to June, mixed date formats become dates, loan numbers normalize from their four forms, currencies keep their units, old method names map to the current Regulations' names (ICB becomes Request for Bids, open international), the STEP reference is parsed, and contact names, emails and phone numbers are stripped and counted. Gold builds country, project, package (keyed by STEP reference), notice, contract, contract supplier (one row per joint-venture member) and supplier (by STEP supplier ID only; name matching comes later), every row with its public_from date. The run writes Kenya's data readiness measures to strata.ops: coverage (rows and years), linked (awards carrying a STEP reference, contracts joined to a notice) and fresh (as of, and cadence). If day-one test 1 failed, fetching runs as the Container Apps job that pushes files into the volume.

Read first: docs/PLAN.md sections 3 and 4; ADR 0002; docs/agents/areas/data.md; the spec's "Data and the lakehouse run".

**Blocked by:** 04 (The strata catalog and the bundle skeleton); 05 (Fixtures for the demo plan and the showcase project)

**Status:** in-progress
**Area:** data
**Phase:** P1
**Design review:** no

- [ ] The offline fixture run builds every gold table named above, and each Kenya award, notice and project value in the ground-truth file appears in gold with its public_from date.
- [ ] A scan of silver and gold finds no email address or phone number, and the count of stripped contact details is recorded as a data readiness measure.
- [ ] A loan number in each of its forms (the four that docs/PLAN.md section 3 names, and the older four-digit form with a country code, such as 6030-KE) normalizes to one value and joins to its project.
- [ ] The fixture's joint-venture award becomes one joint-venture supplier linked to its members, with the contract amount counted once.
- [ ] Rows from "INDIVIDUAL CONSULTANT" never yield a supplier name that a tool can return.
- [ ] A notice that says ICB is stored as Request for Bids with market approach open international, keeping the original wording in its own column.
- [ ] A second fetch with no source changes adds no bronze rows.
- [ ] On the workspace, the job ingests Kenya, and the STEP-reference link rate in strata.ops equals a direct count query over gold run as a check.
- [ ] Every query uses bound parameters and three-part names, enforced by a lint in the gate.

## Comments

- October 23, 2026, orchestrator: dispatched to an implementer in its own worktree on branch strata/07-kenya-procurement-records, as soon as tickets 04 and 05 landed. Credentials are still missing, so every live step is parked in docs/workspace-catchup.md; the offline side is built against the fixtures. Ticket 12 reads the gold tables: a package's signing date comes from the awards dataset or, when it has no row, from its Contract Award notice's Contract Signature Date, and its canceled state from its plan row's status. tests/ground_truth/values.toml says 45 signed, 3 canceled and 4 still open across P156634, P176758 and P170941.

- October 23, 2026, orchestrator: round 4's review approved with three polish items, and the verifier failed criterion 3 only. 49 fixture notices write a credit in an older form (6030-KE, IDA- 6030-KE, IDA 5268-KE, 5310-IN), which gold stored as a credit no project has, as two values for one credit, or as no loan at all. The criterion above now names that fifth form. The implementer fixes it in a fifth round in the same worktree (.claude/worktrees/wf_1a4ee1cf-75b-3) with the verifier's four steps, adds the form to docs/PLAN.md section 3 in the same change, and takes the review's seven phone labels (P1). The ticket then goes back to the reviewer and the verifier.
