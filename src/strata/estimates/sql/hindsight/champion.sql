-- The hindsight test (ticket 34): the champion, the newest run the release gate promoted. A challenger is compared
-- with it on the same blamed risks, and replaces it only when promoted (strata.estimates.hindsight.decide).
SELECT run_id
FROM strata.ops.evaluation_result
WHERE scorer = :scorer
  AND segment_kind = :gate
  AND measure = :promoted
  AND value = :yes
ORDER BY ran_at DESC, run_id DESC
LIMIT 1
