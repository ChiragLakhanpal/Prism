-- One row per lesson the batch model proposed, with the quote check's outcome (ticket 29;
-- src/strata/knowledge/lessons/propose.py). A proposal enters the review queue only when its quote is
-- word for word on the page it cites, in the passage it cites; otherwise it is kept here as the model
-- wrote it, with the reason, and never repaired. Rebuilt for each project from
-- strata.bronze.lesson_batches on every run, so a proposal keeps its id from run to run.
--
-- proposal_id   the cited passage, then the proposal's place in the answer: 31525018/v1/54#1
-- document_id   the document the model read, and its version
-- version
-- project_id    the document's project
-- document_type the documents API's type, word for word
-- report_number the document's report number, empty when it has none
-- passage_id    the passage the proposal cites (strata.silver.passages)
-- paragraph     that passage's paragraph, as the report prints it (54, or 12 in an ICR Review)
-- cited_page    the PDF page the proposal cites, from 1
-- statement     the lesson in one sentence, as the model wrote it
-- quote         the words the model quoted, as it wrote them
-- risk_factors  the risk factors' keys, as a JSON list (config/lessons.toml)
-- stage         the stage's key (config/lessons.toml)
-- kind          worked or did_not_work (config/lessons.toml)
-- edition_key   the edition of the procurement rules the project's PAD names (config/editions.toml),
--               empty when it names none
-- quote_check   passed; quote_not_on_page, when the quote is not word for word on the cited page;
--               quote_not_in_passage, when it is on the page but not in the cited passage;
--               unknown_passage, when the document has no such passage; or not_in_lists, when a risk
--               factor, the stage or the kind is not on its closed list
-- model         the deployment that proposed it
-- batch_id      the batch its answer came in
-- proposed_on   the day its answer came back, in UTC
-- public_from   proposed_on: the day Strata made the proposal (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.silver.lesson_proposals (
  proposal_id STRING NOT NULL,
  document_id STRING NOT NULL,
  version INT NOT NULL,
  project_id STRING NOT NULL,
  document_type STRING NOT NULL,
  report_number STRING,
  passage_id STRING NOT NULL,
  paragraph STRING,
  cited_page INT,
  statement STRING NOT NULL,
  quote STRING NOT NULL,
  risk_factors STRING NOT NULL,
  stage STRING,
  kind STRING,
  edition_key STRING,
  quote_check STRING NOT NULL,
  model STRING NOT NULL,
  batch_id STRING NOT NULL,
  proposed_on DATE NOT NULL,
  public_from DATE NOT NULL
)
