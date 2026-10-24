-- The projects the assertion run rebuilds: every project whose documents the passage reader read, and every
-- project with a contract, a notice, a Procurement Plan or an IEG rating.
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
