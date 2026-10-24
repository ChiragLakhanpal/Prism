-- A person's decision on a candidate pair: merge or no merge, with the reviewer, the reason and the two
-- names the person saw.
INSERT INTO strata.ops.supplier_review_decisions
  (pair_id, left_key, right_key, left_name, right_name, decision, reviewer, reason, decided_at, public_from)
VALUES (:pair_id, :left_key, :right_key, :left_name, :right_name, :decision, :reviewer, :reason,
        CAST(:decided_at AS TIMESTAMP), CAST(:public_from AS DATE))
