-- research_evidence: the latest deep research run on a project as of the call's date (tickets 147 and 148), the one
-- whose as-of day is on or before it that finished last.
SELECT run_id, project_id, started, finished, as_of, sources_asked, reached, note, source_notes
FROM strata.ops.research_runs
WHERE project_id = :project_id
  AND as_of <= :as_of
  AND finished IS NOT NULL
ORDER BY finished DESC, run_id DESC
LIMIT 1
