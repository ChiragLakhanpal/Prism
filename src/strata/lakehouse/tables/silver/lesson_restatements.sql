-- One row per restatement the batch model found in an ICR Review or a PPAR: IEG's own words saying again
-- what a numbered ICR paragraph says, as 10.b of P130164's ICR Review does with "(ICR para 54)" (ticket
-- 29). Each is checked like a proposal's quote; one that passes attaches to the proposals from that ICR
-- paragraph as a second piece of evidence (strata.silver.lesson_evidence). Rebuilt for each project from
-- strata.bronze.lesson_batches on every run.
--
-- document_id    the ICR Review or PPAR, and its version
-- version
-- project_id     its project
-- document_type  the documents API's type, word for word
-- report_number  its report number, such as ICRR0021929
-- restates       the ICR paragraph it says again, as the ICR prints it (54)
-- passage_id     the passage the restatement is in
-- paragraph      that passage's paragraph (10.b)
-- cited_page     the PDF page it cites, from 1
-- quote          IEG's words, as the model wrote them
-- quote_check    passed, or the reason it failed, as for a proposal (strata.silver.lesson_proposals)
-- batch_id       the batch its answer came in
-- found_on       the day its answer came back, in UTC
-- public_from    the restating document's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.lesson_restatements (
  document_id STRING NOT NULL,
  version INT NOT NULL,
  project_id STRING NOT NULL,
  document_type STRING NOT NULL,
  report_number STRING,
  restates STRING NOT NULL,
  passage_id STRING NOT NULL,
  paragraph STRING,
  cited_page INT,
  quote STRING NOT NULL,
  quote_check STRING NOT NULL,
  batch_id STRING NOT NULL,
  found_on DATE NOT NULL,
  public_from DATE NOT NULL
)
