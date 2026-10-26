-- Whether a viewer keeps Home's Start here strip (ticket 41): their latest choice, or no row when they never chose.
SELECT visible
FROM strata.ops.start_here_choices
WHERE viewer_id = :viewer_id
ORDER BY chosen_at DESC
LIMIT 1
