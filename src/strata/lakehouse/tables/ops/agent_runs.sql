-- One row for each run of the answer stream (POST /api/ask): what was asked, what the agent did, what
-- the verifier found and where the run's trace is (spec, "The agent and the answer contract": every
-- agent run is logged in strata.ops). src/strata/agent/runs.py writes it when the stream ends. The AI
-- quality page reads removed sentences and check counts from it (ticket 45).
--
-- run_id                         the run, as the stream's done event names it
-- viewer_id                      the viewer's user id from the Databricks App, never their email
-- question                       the question as asked
-- scope                          the page's scope chip, a P-code or a STEP reference, or empty
-- as_of                          the as-of date the tools ran at, never later than the day of the run
-- view                           staff, piu or public
-- language                       the language the answer was asked in: en, fr, es or pt
-- status                         answered, or failed
-- error_code                     why a failed run stopped: a code from ERROR_CODES as its error event
--                                says, stopped when the viewer left before the done event, or
--                                no_answer when the runner ended with no claims
-- agent, agent_version           the Foundry agent that answered, and its version when known
-- tool_rounds                    rounds of tool calls that ran, at most agent.tool_rounds
-- tool_calls                     JSON: each call with its round, tool, arguments, rows and abstention,
--                                and the calls that did not run, with why
-- response_ids                   JSON: the agent's Responses API response ids, in order
-- sentences_written, sentences_kept, sentences_removed   what the verifier did with the claims
-- numbers_total, numbers_matched, dates_total, dates_matched, quotes_total, quotes_found,
-- sources_total, sources_returned   the counts behind the check line
-- removed                        JSON: each removed sentence with its first reason code
-- application_insights_trace_id  the request's operation id in Application Insights
-- mlflow_trace_id                the run's trace in MLflow, when it has one
-- started_at, finished_at        when the run started and ended, in UTC
-- public_from                    the day the run ended, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.agent_runs (
  run_id STRING NOT NULL,
  viewer_id STRING,
  question STRING NOT NULL,
  scope STRING,
  as_of DATE NOT NULL,
  view STRING NOT NULL,
  language STRING NOT NULL,
  status STRING NOT NULL,
  error_code STRING,
  agent STRING,
  agent_version STRING,
  tool_rounds INT NOT NULL,
  tool_calls STRING NOT NULL,
  response_ids STRING NOT NULL,
  sentences_written INT,
  sentences_kept INT,
  sentences_removed INT,
  numbers_total INT,
  numbers_matched INT,
  dates_total INT,
  dates_matched INT,
  quotes_total INT,
  quotes_found INT,
  sources_total INT,
  sources_returned INT,
  removed STRING NOT NULL,
  application_insights_trace_id STRING,
  mlflow_trace_id STRING,
  started_at TIMESTAMP NOT NULL,
  finished_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
