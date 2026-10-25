-- Every grade the query judges gave, oldest first, so the latest of a judge and passage wins
-- (strata.knowledge.retrieval.judging).
SELECT grade_id, query_id, passage_id, judge_email, judge_name, grade, graded_at
FROM strata.ops.retrieval_grades
ORDER BY graded_at, grade_id
