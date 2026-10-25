-- The latest choice on each disagreement card under a draft (ticket 36): the newest row of each draft and
-- disagreement in strata.ops.draft_choices, whose rows are only ever appended. The disagreements hold and the
-- evidence pack read this view, so "latest" is decided once.
CREATE OR REPLACE VIEW strata.ops.draft_choices_latest AS
SELECT c.*
FROM strata.ops.draft_choices AS c
QUALIFY row_number() OVER (PARTITION BY c.draft_id, c.disagreement_id ORDER BY c.save_no DESC, c.set_at DESC) = 1
