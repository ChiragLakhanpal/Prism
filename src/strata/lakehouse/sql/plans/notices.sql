-- The plan reader's dictionary from one project's notices (ticket 131): each notice's id, its reference and its
-- title, which the repair (src/strata/reader/repair.py) checks a plan row's reference and split words against. The
-- reference is the STEP reference silver normalized (KE/TAVEVO/82746/GO/RFB as KE-TAVEVO-82746-GO-RFB), or the
-- reference as the notice writes it when it is not one.
SELECT notice_id, COALESCE(step_reference, bid_reference_no) AS bid_reference_no, bid_description
FROM strata.silver.notices
WHERE project_id = :project_id
ORDER BY notice_date, notice_id
