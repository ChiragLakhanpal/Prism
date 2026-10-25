-- Following (ticket 37): whether Strata holds a record of a project, public by today, before a viewer follows it.
-- The same project record project_signals reads (src/strata/tools/sql/project_signals/project.sql), without the checks.
SELECT p.project_id
FROM strata.gold.project AS p
WHERE p.project_id = :project_id
  AND p.public_from <= :as_of
