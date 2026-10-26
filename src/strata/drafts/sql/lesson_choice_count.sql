-- How many lesson choices a draft has had (ticket 39), so the next takes the next number.
SELECT coalesce(max(choice_no), 0) AS choices
FROM strata.ops.draft_lesson_choices
WHERE draft_id = :draft_id
