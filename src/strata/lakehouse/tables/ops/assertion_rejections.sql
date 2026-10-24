-- The assertions the batch model read from a report that the run did not keep, each with its reason
-- (src/strata/knowledge/assertions.py). The check rejects; it never repairs. Rebuilt for each project
-- of the run, so it holds the latest run's rejections. get_disagreements counts them per project, and the
-- timeline states the count under its chart (brief 23).
--
-- run_id        the run that rejected it
-- project_id    the report's project
-- document_id   the report, by its documents API id
-- version       its version of its report number
-- passage_id    the passage the model cited
-- pdf_page      the PDF page the model cited
-- attribute     what the model said the assertion was about
-- value         the value the model gave
-- quote         the words the model quoted
-- reason        quote_not_on_page (its words are not in the cited passage on that page), passage_not_found,
--               unknown_attribute, unknown_period or value_not_on_scale
-- read_by       the model that read it
-- rejected_at   when, in UTC
-- public_from   the report's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.assertion_rejections (
  run_id STRING NOT NULL,
  project_id STRING NOT NULL,
  document_id STRING NOT NULL,
  version INT,
  passage_id STRING,
  pdf_page INT,
  attribute STRING,
  value STRING,
  quote STRING,
  reason STRING NOT NULL,
  read_by STRING NOT NULL,
  rejected_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
