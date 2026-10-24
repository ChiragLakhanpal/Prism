-- IEG's ratings of a project, one row per evaluation, from the newest fetch: the independent
-- evaluation at the top of the evidence ladder for outcome judgments (spec, "The knowledge model").
--
-- evaluation_type   ICRR for an ICR Review, PPAR for a Project Performance Assessment Report
-- evaluation_fy     the fiscal year IEG evaluated the project in
-- outcome, bank_performance, quality_at_entry, quality_of_supervision, me_quality   word for word
-- public_from       June 30 of evaluation_fy, as the dataset gives no date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.gold.ieg_rating (
  project_id STRING NOT NULL,
  evaluation_type STRING NOT NULL,
  evaluation_fy INT NOT NULL,
  outcome STRING,
  bank_performance STRING,
  quality_at_entry STRING,
  quality_of_supervision STRING,
  me_quality STRING,
  global_practice STRING,
  public_from DATE NOT NULL
)
