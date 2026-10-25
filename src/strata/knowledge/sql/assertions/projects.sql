-- The projects the assertion run rebuilds: every project whose documents the passage reader read, and every
-- project with a contract, a notice, a Procurement Plan or an IEG rating. The run reads each family of
-- assertions with one query for all of them (strata.knowledge.assertions.ProjectRows, ticket 43), so the
-- workspace's 15,933 such projects of October 24, 2026 cost a handful of queries, where one query a project
-- took about eleven hours against the nightly job's 150-minute stop.
SELECT project_id FROM strata.silver.documents
UNION
SELECT project_id FROM strata.gold.contract
UNION
SELECT project_id FROM strata.gold.notice
UNION
SELECT project_id FROM strata.silver.plan_versions
UNION
SELECT project_id FROM strata.gold.ieg_rating
ORDER BY project_id
