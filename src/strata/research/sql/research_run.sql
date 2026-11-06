-- One research run by its id (ticket 147), read before its items.
SELECT run_id, project_id, started, finished, as_of, viewer, sources_asked, reached, note, source_notes
FROM strata.ops.research_runs
WHERE run_id = :run_id
