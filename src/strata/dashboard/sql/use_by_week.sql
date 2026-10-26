-- Tiles 32 to 34: by week (its Monday) in the dates chosen, the people who opened a page of Strata (a route outside
-- /api in strata.ops.usage_events, each person once a week whatever view they used), the answers given
-- (strata.ops.agent_runs), the drafts started (strata.ops.drafts), and the drafts their authors moved to checked and
-- to exported that week (strata.ops.draft_states, each draft counted in the week it reached the state). Newest first.
WITH people AS (
  SELECT CAST(date_trunc('WEEK', public_from) AS DATE) AS week_start, count(DISTINCT viewer_id) AS people
  FROM strata.ops.usage_events
  WHERE public_from BETWEEN :date_from AND :date_to AND route NOT LIKE '/api/%' AND viewer_id IS NOT NULL
  GROUP BY CAST(date_trunc('WEEK', public_from) AS DATE)
),
answers AS (
  SELECT CAST(date_trunc('WEEK', public_from) AS DATE) AS week_start, count(*) AS answers
  FROM strata.ops.agent_runs
  WHERE status = 'answered' AND public_from BETWEEN :date_from AND :date_to
  GROUP BY CAST(date_trunc('WEEK', public_from) AS DATE)
),
started AS (
  SELECT CAST(date_trunc('WEEK', public_from) AS DATE) AS week_start, count(*) AS started
  FROM strata.ops.drafts
  WHERE public_from BETWEEN :date_from AND :date_to
  GROUP BY CAST(date_trunc('WEEK', public_from) AS DATE)
),
reached AS (
  SELECT draft_id, state, min(public_from) AS reached_on
  FROM strata.ops.draft_states
  WHERE state IN ('checked', 'exported')
  GROUP BY draft_id, state
),
states AS (
  SELECT
    CAST(date_trunc('WEEK', reached_on) AS DATE) AS week_start,
    sum(CASE WHEN state = 'checked' THEN 1 ELSE 0 END) AS checked,
    sum(CASE WHEN state = 'exported' THEN 1 ELSE 0 END) AS exported
  FROM reached
  WHERE reached_on BETWEEN :date_from AND :date_to
  GROUP BY CAST(date_trunc('WEEK', reached_on) AS DATE)
),
weeks AS (
  SELECT week_start FROM people
  UNION SELECT week_start FROM answers
  UNION SELECT week_start FROM started
  UNION SELECT week_start FROM states
)
SELECT
  w.week_start,
  coalesce(p.people, 0) AS people,
  coalesce(a.answers, 0) AS answers,
  coalesce(s.started, 0) AS started,
  coalesce(st.checked, 0) AS checked,
  coalesce(st.exported, 0) AS exported
FROM weeks AS w
LEFT JOIN people AS p ON p.week_start = w.week_start
LEFT JOIN answers AS a ON a.week_start = w.week_start
LEFT JOIN started AS s ON s.week_start = w.week_start
LEFT JOIN states AS st ON st.week_start = w.week_start
ORDER BY w.week_start DESC
