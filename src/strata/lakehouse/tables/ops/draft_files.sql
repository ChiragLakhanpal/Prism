-- The files each export of a draft made (ticket 35): the Word file and the evidence pack's PDF and CSV,
-- kept with the export record so the author's team can download them again. The draft runtime writes
-- them as the app's own service principal, and the file route reads them only for the draft's team.
--
-- draft_id     the draft, in strata.ops.drafts
-- export_id    the export in strata.ops.draft_exports that made the file
-- name         the file's name, such as review-notes-P156634-northern-water-works-development-agency-2026-10-09.docx
-- media_type   its media type
-- size_bytes   its size
-- content      its bytes in base64, so the same column works on DuckDB and the SQL warehouse
-- public_from  the day it was made, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.draft_files (
  draft_id STRING NOT NULL,
  export_id STRING NOT NULL,
  name STRING NOT NULL,
  media_type STRING NOT NULL,
  size_bytes INT NOT NULL,
  content STRING NOT NULL,
  public_from DATE NOT NULL
)
