-- The award notice a query was written from (strata.knowledge.retrieval.judging).
SELECT notice_id, notice_type, notice_date, project_id, step_reference, bid_reference_no, public_from
FROM strata.gold.notice
WHERE notice_id = :notice_id
