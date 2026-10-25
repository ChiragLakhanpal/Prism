-- The labeled set retrieval is measured on (ticket 32; the spec's "Evaluation"): one row for each passage
-- labeled relevant to a query. The weekly retrieval run builds it again each time under a new build_id, and
-- readers take the latest build (strata.knowledge.retrieval.labels).
--
-- Three query sets are evaluation sets: the ICR Reviews' "ICR para N" citations and the PADs' "Lessons
-- Learned and Reflected in the Project Design" sections (silver labels, read from the documents), and the
-- queries written from award notices, graded by two query judges. A fourth set, feedback, holds the labels
-- passage reviewers accepted from passage reports; only it may train anything, and building an evaluation
-- set from it fails, so evaluation sets never take live feedback.
--
-- build_id     the build that wrote the row
-- query_set    icr_review_citations, pad_lessons, notice_queries or feedback
-- query_id     the query, such as icrr:ICRR0021929:54
-- query_text   the query's words
-- query_date   the query's date: retrieval for it uses only documents public before it
-- project_id   the project the query is about, which its search keeps to, or empty for every project
-- passage_id   a passage labeled for the query
-- grade        2 answers it, 1 partly (nDCG's gains); a feedback label is 0, a passage ranked lower
-- origin       where the label came from: icr_review_citation, pad_lessons, judged, feedback_reviewed or
--              feedback_agreement
-- weight       the label's weight: 1 for a document's own words or two judges, the Dawid and Skene weight
--              for an agreement
-- built_at     when the build ran, in UTC
-- public_from  the day the label could first be known: the later of the query's date and the build's day
--              for a judged or feedback label, the query's date for a silver label (ADR 0002)
CREATE TABLE IF NOT EXISTS strata.ops.retrieval_labels (
  build_id STRING NOT NULL,
  query_set STRING NOT NULL,
  query_id STRING NOT NULL,
  query_text STRING NOT NULL,
  query_date DATE NOT NULL,
  project_id STRING,
  passage_id STRING NOT NULL,
  grade INT NOT NULL,
  origin STRING NOT NULL,
  weight DOUBLE NOT NULL,
  built_at TIMESTAMP NOT NULL,
  public_from DATE NOT NULL
)
