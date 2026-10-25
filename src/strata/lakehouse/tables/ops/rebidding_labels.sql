-- How many packages each source says were advertised again (ticket 28): one row per source per run, written by
-- the nightly job's score task (strata.estimates.rebidding.record_label_counts). No field says a package was
-- advertised again, so three sources say it, and each package is counted once per source.
--
-- run_id       the run that counted
-- source       no_award (no award followed its notice rebidding.no_award_after_days after its bids were due),
--              same_reference (a later notice of the same type under the same STEP reference), canceled_row
--              (Process Status Canceled in the newest plan version public that day, and no signed contract), or
--              any, the packages one or more sources name
-- count        how many packages the source names
-- denominator  the packages it looked at: every package whose specific procurement notice is dated from
--              past_range.period_from and was public that day
-- as_of        the day the records were read as of
-- measured_at  when, in UTC
-- public_from  the day it was counted (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.rebidding_labels (
  run_id STRING NOT NULL,
  source STRING NOT NULL,
  count BIGINT NOT NULL,
  denominator BIGINT NOT NULL,
  as_of DATE NOT NULL,
  measured_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
