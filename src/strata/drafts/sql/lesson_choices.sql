-- Every choice the authors of the drafts in :ids made for rows that cite a changed lesson (ticket 39), in order.
-- :ids holds the draft ids joined by commas, which no draft id contains.
SELECT draft_id, choice_no, row_key, lesson_id, action, cited_version, current_version, reason, rewrite, draft_state,
       actor_id, actor_name, chosen_at
FROM strata.ops.draft_lesson_choices
WHERE array_contains(split(:ids, ','), draft_id)
ORDER BY draft_id, choice_no, chosen_at
