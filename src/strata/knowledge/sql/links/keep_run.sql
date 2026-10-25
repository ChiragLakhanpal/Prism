-- The relink task keeps only its latest run's links (ticket 22): the rows an earlier run scored leave through
-- this DELETE, after the new run's rows are in (CLAUDE.md rule 5).
DELETE FROM strata.silver.contract_passage_links
WHERE run_id <> :run_id
