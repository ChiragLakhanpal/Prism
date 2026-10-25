-- One package's natural frequency from the rebidding champion (ticket 28): the newest score the nightly job's
-- score task wrote for it with the champion's version, public on or before the as-of date (ADR 0002).
SELECT run_id, step_reference, model, version, learner, probability, in10, scored_on, public_from
FROM strata.ops.rebidding_scores
WHERE step_reference = :step_reference AND model = :model AND version = :version AND public_from <= :as_of
ORDER BY scored_on DESC, run_id DESC
LIMIT 1
