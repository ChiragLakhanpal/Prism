-- The day each item of a project was first read, in any run (ticket 147): an item read again keeps it.
SELECT evidence_id, min(read_on) AS read_on
FROM strata.ops.research_items
WHERE project_id = :project_id
GROUP BY evidence_id
