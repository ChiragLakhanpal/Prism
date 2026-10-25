-- What each person's "Wrong passage" reports did (ticket 32; spec story 100, "You marked 2 passages as
-- wrong; 1 is fixed, and 14 answers now cite the right paragraph"). The weekly retrieval run appends one row
-- per person who has sent one, so the latest row of a person gives their counts, which Lessons (ticket 39)
-- and the dashboard (ticket 45) read.
--
-- viewer_id    the person: the user id the Databricks App forwarded
-- marked       passages they marked as the wrong passage, not withdrawn and not in a preview
-- fixed        of those, passages now ranked lower for that kind of question, by a reviewer or by agreement
-- waiting      of those, passages no reviewer has decided on yet
-- kept         of those, passages a reviewer kept the ranking of
-- recited      answers to the same kind of question on the same project, asked after a passage they marked
--              was ranked lower, that cite a different paragraph and not that one
-- computed_at  when the run counted, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_feedback_viewers (
  viewer_id STRING NOT NULL,
  marked INT NOT NULL,
  fixed INT NOT NULL,
  waiting INT NOT NULL,
  kept INT NOT NULL,
  recited INT NOT NULL,
  computed_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
