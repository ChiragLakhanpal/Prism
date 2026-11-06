-- Every value a person set on a draft's fields that only people fill (ticket 36): a suggested PPSD row's Risk
-- Owner and, in the Long Form, its Likelihood Rating, Impact Rating, Overall Risk Score and Procurement Process
-- Stage, and the risk table form the draft uses. One row per save, so the history is never rewritten: a removal
-- is a save with no value. strata.ops.draft_fields_latest gives each field's latest value. Prism never writes
-- here; the draft routes (src/strata/server/drafts.py) save a person's own entry, from the author's session only,
-- as the app's own service principal.
--
-- draft_id     the draft, in strata.ops.drafts
-- save_no      the save's number in the draft's history, from 1
-- row_key      the row it sets, such as the risk key cost_estimates; empty for the draft's form
-- field        risk_owner, likelihood, impact, score or stage (config/ppsd_templates.toml), or form
-- value        what the person set, as text; empty when they removed it
-- set_by_id    the user id of the person who set it, always the draft's author
-- set_by_name  their name as the Databricks App forwarded it
-- set_at       when it was set, in UTC
-- public_from  the day it was set, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.draft_fields (
  draft_id STRING NOT NULL,
  save_no INT NOT NULL,
  row_key STRING NOT NULL,
  field STRING NOT NULL,
  value STRING,
  set_by_id STRING NOT NULL,
  set_by_name STRING,
  set_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
