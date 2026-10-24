-- IEG's project performance ratings (Finances One DS00053), typed: one row per evaluation of a
-- project from each fetched page. Gold reads the newest.
--
-- evaluation_type            ICRR for an ICR Review, PPAR for a Project Performance Assessment Report
-- evaluation_fiscal_year     the fiscal year IEG evaluated the project in (the dataset's evaluation_fy)
-- approval_fiscal_year, final_closing_fiscal_year   the dataset's approval_fy and final_closing_fy
-- outcome, bank_performance, quality_at_entry, quality_of_supervision, me_quality
--                            IEG's ratings, word for word
-- public_from                June 30 of the evaluation's fiscal year, or the fetch day when that is
--                            later: the dataset gives no date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.ieg_ratings (
  project_id STRING NOT NULL,
  project_name STRING,
  country STRING,
  region STRING,
  global_practice STRING,
  agreement_type STRING,
  lending_instrument_type STRING,
  approval_fiscal_year INT,
  final_closing_fiscal_year INT,
  evaluation_type STRING,
  evaluation_fiscal_year INT,
  outcome STRING,
  bank_performance STRING,
  quality_at_entry STRING,
  quality_of_supervision STRING,
  me_quality STRING,
  page_hash STRING NOT NULL,
  fetched_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
