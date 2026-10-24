-- The files one export of a draft made, without their bytes: what the export success panel links to.
SELECT name, media_type, size_bytes
FROM strata.ops.draft_files
WHERE draft_id = :draft_id
  AND export_id = :export_id
ORDER BY name
