-- The plan reader's dictionary from one project's notices (ticket 131): each notice's id, its reference as the
-- notice writes it and its title, which the repair (src/strata/reader/repair.py) checks a plan row's reference and
-- split words against.
SELECT notice_id, bid_reference_no, bid_description
FROM strata.silver.notices
WHERE project_id = :project_id
ORDER BY notice_date, notice_id
