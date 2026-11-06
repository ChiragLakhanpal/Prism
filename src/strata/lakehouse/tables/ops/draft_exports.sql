-- One row for each export of a draft (ticket 35): the record of what its author exported and how they
-- checked it. The evidence pack's PDF and CSV are built from the same record, and its snapshot keeps,
-- for every source the draft cites, whether the author opened it in the evidence drawer after the draft
-- was saved and when they last did, as strata.ops.evidence_opened held it at the moment of export.
-- Prism sends nothing anywhere: the files are kept in strata.ops.draft_files for the author's team.
--
-- draft_id     the draft, in strata.ops.drafts
-- export_id    the export's id
-- exported_at  when it was exported, in UTC
-- actor_id     the user id of the author who exported it
-- actor_name   their name as the Databricks App forwarded it
-- footnotes    how many footnotes the Word file has: one per citation
-- sources      how many distinct sources the draft cites
-- opened       how many of them the author opened before exporting
-- snapshot     the evidence pack's rows as JSON: each source, where it is cited, whether it was opened
--              and when it was last opened
-- public_from  the day it was exported, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.draft_exports (
  draft_id STRING NOT NULL,
  export_id STRING NOT NULL,
  exported_at TIMESTAMP NOT NULL,
  actor_id STRING NOT NULL,
  actor_name STRING,
  footnotes INT NOT NULL,
  sources INT NOT NULL,
  opened INT NOT NULL,
  snapshot STRING NOT NULL,
  public_from DATE NOT NULL
)
