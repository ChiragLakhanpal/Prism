-- KPI drafts_exported (config/kpis.toml): drafts started in the dates chosen that their authors marked as checked and
-- then exported, out of the drafts started (strata.ops.drafts and strata.ops.draft_states, ticket 35). Only a draft's
-- author can do either, and a draft is exported only from checked, so an exported state counts. Always one row:
-- "None yet" before the first draft.
WITH started AS (
  SELECT draft_id
  FROM strata.ops.drafts
  WHERE public_from BETWEEN :date_from AND :date_to
),
exported AS (
  SELECT DISTINCT s.draft_id
  FROM started AS s
  JOIN strata.ops.draft_states AS st ON st.draft_id = s.draft_id AND st.state = 'exported'
),
counted AS (
  SELECT (SELECT count(*) FROM exported) AS exported, (SELECT count(*) FROM started) AS started
)
SELECT
  exported AS numerator,
  started AS denominator,
  exported AS value,
  CASE
    WHEN started = 0 THEN :copy__kpi__display__none
    ELSE replace(replace(:copy__kpi__display__share, '{n}', format_number(exported, 0)), '{d}',
                 format_number(started, 0))
  END AS display
FROM counted
