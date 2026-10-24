-- The day the documents API's list of a project's documents was last fetched, for the Procurement
-- tab's source line ("Procurement Plans for P156634, through ...").
SELECT max(public_from) AS fetched_on
FROM strata.bronze.document_lists
WHERE project_id = :project_id
