-- The size of each query set of the labeled set, as each build of it found (ticket 32): how many queries and
-- how many labels. The weekly retrieval run appends one row per query set and build, so the latest build
-- gives the size the dashboard and the replay harness state (strata.knowledge.retrieval.labels).
--
-- build_id     the build (strata.ops.retrieval_labels)
-- query_set    icr_review_citations, pad_lessons, notice_queries or feedback
-- queries      how many queries the set holds
-- labels       how many passages are labeled for them
-- documents    how many documents the set's labels were read from, for a silver set; empty otherwise
-- built_at     when the build ran, in UTC
-- public_from  the day, in UTC (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_label_builds (
  build_id STRING NOT NULL,
  query_set STRING NOT NULL,
  queries INT NOT NULL,
  labels INT NOT NULL,
  documents INT,
  built_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
