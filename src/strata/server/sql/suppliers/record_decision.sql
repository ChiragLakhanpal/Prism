-- A person's decision on a candidate pair: merge or no merge, with the reviewer and the reason.
INSERT INTO strata.ops.supplier_review_decisions
  (pair_id, left_key, right_key, decision, reviewer, reason, decided_at, public_from)
VALUES (:pair_id, :left_key, :right_key, :decision, :reviewer, :reason, CAST(:decided_at AS TIMESTAMP),
        CAST(:public_from AS DATE))
