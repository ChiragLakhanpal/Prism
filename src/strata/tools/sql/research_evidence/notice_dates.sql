-- research_evidence: the project's notices public by the call's date, with their own dates, which the notices reader
-- turns into each notice item's fields (src/strata/research/sources/procurement_notices.py, notice_dates; ticket 155).
SELECT notice_id, notice_date, submission_deadline, contract_signature_date
FROM strata.gold.notice
WHERE project_id = :project_id
  AND public_from <= :as_of
