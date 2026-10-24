-- The showcase disagreement, written as plain SQL apart from get_disagreements' own code: ISR 7's rating of
-- progress towards the PDO against the ICR's paragraph 78, with the side the evidence ladder leans on.
-- get_disagreements' benchmark question (evals/benchmark.yaml, get-disagreements-p130164) expects the same.
--
-- ISR 7 is documents API id 26733307, archived August 26, 2016 and rated Satisfactory (values.toml,
-- isr-7-date and isr-7-rating); its overall ratings are its first page's passage s4. The ICR is 31525018,
-- dated October 10, 2019 and public on November 2, 2019 (icr-date, icr-disclosed); paragraph 78 is on PDF
-- page 27 (icr-para-78). The mid-term review was on May 16, 2016 (mid-term-review). Progress towards the
-- PDO is an outcome judgment, so the ladder's outcome rule leans on the ICR (config/evidence_ladder.toml).
-- Run it on the warehouse after the live run with: uv run --script ops/bundle/check.py same-rows --env-file .env
-- engines: duckdb, databricks
-- param: project_id = P130164
-- param: attribute = pdo_progress
-- expect: first_evidence,first_value,first_made_at,second_evidence,second_page,second_public_from,period_start,lean_evidence,rule_id
-- expect: strata.gold.passage:26733307/v1/s4,Satisfactory,2016-08-26,strata.gold.passage:31525018/v1/78,27,2019-11-02,2016-05-16,strata.gold.passage:31525018/v1/78,outcome
SELECT
  a.evidence_id AS first_evidence,
  a.value AS first_value,
  a.made_at AS first_made_at,
  b.evidence_id AS second_evidence,
  b.pdf_page AS second_page,
  b.public_from AS second_public_from,
  d.period_start,
  l.evidence_id AS lean_evidence,
  d.rule_id
FROM strata.gold.disagreement AS d
JOIN strata.gold.assertion AS a ON a.assertion_id = d.first_assertion_id
JOIN strata.gold.assertion AS b ON b.assertion_id = d.second_assertion_id
JOIN strata.gold.assertion AS l ON l.assertion_id = d.lean_assertion_id
WHERE d.subject_id = :project_id
  AND d.attribute = :attribute
