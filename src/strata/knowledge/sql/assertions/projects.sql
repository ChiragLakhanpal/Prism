-- The projects the assertion run rebuilds: every project whose documents the passage reader read, and every
-- project with a Procurement Plan read. Those are the projects whose ISR, text and plan assertions exist, so
-- they are the ones where a disagreement can be found and decided by the ladder.
--
-- Projects known only from a contract, a notice or an IEG rating are left out since October 24, 2026. The run
-- reads each project with about seven warehouse queries of its own, and the workspace holds 15,933 projects
-- with such a record (12,628 from the IEG ratings dataset alone), which is about eleven hours of queries
-- against the nightly job's 150-minute stop: the fifth live run spent 94 minutes in this task and was
-- cancelled. Reading those projects again needs the per-project queries rewritten to run once for all
-- projects (a follow-up noted in docs/workspace-catchup.md under ticket 04's step 2).
SELECT project_id FROM strata.silver.documents
UNION
SELECT project_id FROM strata.silver.plan_versions
ORDER BY project_id
