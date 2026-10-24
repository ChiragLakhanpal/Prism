-- One file of a draft's export, with its bytes, for a download by someone on the draft's team.
SELECT media_type, content
FROM strata.ops.draft_files
WHERE draft_id = :draft_id
  AND export_id = :export_id
  AND name = :name
