-- A person kept one side of a disagreement for an answer or a draft (ticket 23): one new row in
-- strata.ops.disagreement_choices. Rows are only added, so going back to Strata's choice adds a row too.
INSERT INTO strata.ops.disagreement_choices
  (choice_id, viewer, disagreement_id, kept_assertion_id, leaned_assertion_id, reason, run_id, draft_id, made_at,
   public_from)
VALUES
  (:choice_id, :viewer, :disagreement_id, :kept_assertion_id, :leaned_assertion_id, :reason, :run_id, :draft_id,
   CAST(:made_at AS TIMESTAMP), CAST(CAST(:made_at AS TIMESTAMP) AS DATE))
