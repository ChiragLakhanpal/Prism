-- Saving a baseline: who saved which version, and when. One row per project and agency, so the row is
-- merged: saving another version replaces it in one statement, and two people saving at once still leave
-- one row (the 21 review, round 2). A save never replaces a later one, so when two overlap the row keeps
-- the later save, whose steps the earlier one's clean-up never deletes (the 21 review, round 3).
MERGE INTO strata.ops.plan_baselines AS t
USING (
  SELECT
    :project_id AS project_id,
    :agency_id AS agency_id,
    :implementing_agency AS implementing_agency,
    :document_id AS document_id,
    CAST(:plan_date AS DATE) AS plan_date,
    :saved_by AS saved_by,
    :saved_by_name AS saved_by_name,
    CAST(:saved_at AS TIMESTAMP) AS saved_at,
    CAST(:public_from AS DATE) AS public_from
) AS s
ON t.project_id = s.project_id AND t.agency_id = s.agency_id
WHEN MATCHED AND t.saved_at <= s.saved_at THEN UPDATE SET
  implementing_agency = s.implementing_agency,
  document_id = s.document_id,
  plan_date = s.plan_date,
  saved_by = s.saved_by,
  saved_by_name = s.saved_by_name,
  saved_at = s.saved_at,
  public_from = s.public_from
WHEN NOT MATCHED THEN INSERT
  (project_id, agency_id, implementing_agency, document_id, plan_date, saved_by, saved_by_name, saved_at, public_from)
  VALUES (s.project_id, s.agency_id, s.implementing_agency, s.document_id, s.plan_date, s.saved_by, s.saved_by_name,
          s.saved_at, s.public_from)
