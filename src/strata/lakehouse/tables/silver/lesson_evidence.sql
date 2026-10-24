-- The evidence each passing proposal rests on (ticket 29; docs/PLAN.md section 5): its own quote, and
-- each restatement an ICR Review or PPAR made of the ICR paragraph it came from, once for each report
-- number, from the newest version that restated it. A decided lesson rests on the evidence of every
-- proposal a lead added to it (strata.ops.lesson_evidence), so a restatement that arrives after the
-- decision still reaches it. Rebuilt for each project with strata.silver.lesson_proposals.
--
-- proposal_id      the proposal (strata.silver.lesson_proposals)
-- role             source, the proposal's own quote; or restatement
-- passage_id       the passage the quote is in
-- document_id      its document, and the document's version
-- version
-- project_id       the document's project
-- document_type    the documents API's type, word for word
-- report_number    its report number
-- document_date    the document's date (docdt)
-- paragraph        the passage's paragraph, as the report prints it
-- cited_page       the PDF page the quote is on, from 1
-- quote            the words, word for word on that page
-- restated_by_ieg  whether this is IEG's restatement in an ICR Review or a PPAR
-- public_from      the document's public date (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.lesson_evidence (
  proposal_id STRING NOT NULL,
  role STRING NOT NULL,
  passage_id STRING NOT NULL,
  document_id STRING NOT NULL,
  version INT NOT NULL,
  project_id STRING NOT NULL,
  document_type STRING NOT NULL,
  report_number STRING,
  document_date DATE,
  paragraph STRING,
  cited_page INT NOT NULL,
  quote STRING NOT NULL,
  restated_by_ieg BOOLEAN NOT NULL,
  public_from DATE NOT NULL
)
