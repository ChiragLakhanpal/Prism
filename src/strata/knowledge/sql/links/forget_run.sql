-- A relink run that runs again under the same run id, such as a retried task or the fixture build's second
-- run once the passages are read, first removes what it scored before (ticket 22; CLAUDE.md rule 5).
DELETE FROM strata.silver.contract_passage_links
WHERE run_id = :run_id
