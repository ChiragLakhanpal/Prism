-- The lesson extractor's batch requests and answers, as sent and as received (ticket 29;
-- src/strata/knowledge/lessons/propose.py). The nightly job's propose_lessons task sends each current
-- ICR, ICR Review and PPAR of the slice to the batch model once, on Azure OpenAI's Global Batch: one row
-- when the request goes, then one more when its answer comes back or the request fails. Bronze only
-- grows, so a request's state is its newest row. silver.lesson_proposals is rebuilt from the answers.
--
-- custom_id    the request's id in its batch: the document and its version, 31525018/v1
-- document_id  the documents API's id
-- version      the document's version of its report (silver.documents)
-- project_id   the document's project
-- batch_id     the batch the request went in
-- model        the deployment that answers it (config/models.toml, roles.batch)
-- status       submitted, completed or failed
-- request      on a submitted row: the request line as sent, as JSON
-- output       on a completed row: the answer's text, the model's JSON, as received
-- error        on a failed row: why it failed
-- recorded_at  when the row was written, in UTC
-- public_from  the day it was written, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.lesson_batches (
  custom_id STRING NOT NULL,
  document_id STRING NOT NULL,
  version INT NOT NULL,
  project_id STRING NOT NULL,
  batch_id STRING NOT NULL,
  model STRING NOT NULL,
  status STRING NOT NULL,
  request STRING,
  output STRING,
  error STRING,
  recorded_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
