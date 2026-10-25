-- How many choices a draft's author has made on its disagreement cards (ticket 36), so the next takes the next
-- number.
SELECT coalesce(max(save_no), 0) AS saves
FROM strata.ops.draft_choices
WHERE draft_id = :draft_id
