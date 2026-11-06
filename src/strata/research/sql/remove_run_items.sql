-- The items a failed save wrote before its run's row, which no read returns: removed by the run they name, so nothing
-- of a failed run stays (CLAUDE.md rule 5: a DELETE with a WHERE).
DELETE FROM strata.ops.research_items
WHERE run_id = :run_id
