-- The evidence drawer's disagreement view (ticket 23): the project a disagreement is about, by its id, public
-- on the as-of date (ADR 0002).
SELECT
  d.project_id
FROM strata.gold.disagreement AS d
WHERE d.disagreement_id = :disagreement_id
  AND d.public_from <= :as_of
