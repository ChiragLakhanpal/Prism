-- The batch model's answers as received (src/strata/knowledge/batch.py), one row per request it answered.
-- Bronze only grows. A run asks only the requests whose request_hash has no answer from the same
-- deployment yet, so an unchanged report is not asked about again. An error is no answer, so its request
-- is asked again. A request in a batch that had not finished when the run stopped waiting is held with
-- no content and the error "pending:" and the batch's id, and the next run waits for that batch.
--
-- custom_id      the request's key, such as assertions:31525018/v1 (a report and its version)
-- request_hash   SHA-256 of the request's body: the deployment, the rules and the data
-- read_by        what answered: the deployment, or the offline stand-in, which says so in its name
-- content        the answer's message content, the JSON the model wrote; empty when it gave an error
-- error          why there is no content, or pending: and the id of the batch still running
-- answered_at    when the run read the answer, in UTC
-- public_from    the public date of what the request asked about, such as the report (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.bronze.batch_answers (
  custom_id STRING NOT NULL,
  request_hash STRING NOT NULL,
  read_by STRING NOT NULL,
  content STRING,
  error STRING,
  answered_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
