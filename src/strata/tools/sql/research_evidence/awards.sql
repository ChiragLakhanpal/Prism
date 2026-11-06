-- research_evidence: the project's contract award notices public by the call's date, for the summary's counts of the
-- awards made in the days before closing (config/thresholds.toml, research.late_award_days).
SELECT notice_id, notice_date, procurement_method, bid_reference_no
FROM strata.gold.notice
WHERE project_id = :project_id
  AND notice_type = 'Contract Award'
  AND public_from <= :as_of
ORDER BY notice_date, notice_id
