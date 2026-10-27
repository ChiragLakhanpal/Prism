-- A person's label on a candidate pair, from the labeling tool: merge or no merge, with the two names the latest
-- run gave the pair.
INSERT INTO strata.ops.supplier_pair_labels
  (pair_id, left_key, right_key, left_name, right_name, label, labeler, labeled_at, public_from)
VALUES (:pair_id, :left_key, :right_key, :left_name, :right_name, :label, :labeler, CAST(:labeled_at AS TIMESTAMP),
        CAST(:public_from AS DATE))
