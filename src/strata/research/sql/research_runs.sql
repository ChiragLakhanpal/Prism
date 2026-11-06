-- A project's research runs, newest first (ticket 147): the brief stands on the newest.
SELECT run_id, project_id, started, finished, as_of, viewer, sources_asked, reached, note, source_notes
FROM strata.ops.research_runs
WHERE project_id = :project_id
ORDER BY started DESC, run_id DESC
