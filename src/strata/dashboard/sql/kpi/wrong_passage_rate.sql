-- KPI wrong_passage_rate (config/kpis.toml), the retrieval loop's leading indicator: "Wrong passage" and "Not useful"
-- reports per 100 sources opened, by week, as the weekly retrieval run stored them (strata.ops.retrieval_feedback_weekly,
-- each week and kind from its newest measure; ticket 32). per_100 is the stored rate, empty for a week with fewer
-- than retrieval.min_opened sources opened, so the chart has no point there and the table shows the counts. Reports
-- sent in a preview or withdrawn never count. Newest first, in the dates chosen.
WITH latest AS (
  SELECT f.week_start, f.kind, f.reports, f.opened, f.per_100
  FROM strata.ops.retrieval_feedback_weekly AS f
  WHERE f.week_start BETWEEN :date_from AND :date_to
    AND f.computed_at = (
      SELECT max(n.computed_at)
      FROM strata.ops.retrieval_feedback_weekly AS n
      WHERE n.week_start = f.week_start AND n.kind = f.kind
    )
),
weeks AS (
  SELECT
    week_start,
    max(opened) AS opened,
    CAST(max(CASE WHEN kind = 'wrong_passage' THEN reports END) AS BIGINT) AS wrong_passage,
    CAST(max(CASE WHEN kind = 'not_useful' THEN reports END) AS BIGINT) AS not_useful,
    max(CASE WHEN kind = 'wrong_passage' THEN per_100 END) AS wrong_per_100,
    max(CASE WHEN kind = 'not_useful' THEN per_100 END) AS not_useful_per_100
  FROM latest
  GROUP BY week_start
)
SELECT
  week_start,
  opened,
  coalesce(wrong_passage, 0) AS wrong_passage,
  coalesce(not_useful, 0) AS not_useful,
  wrong_per_100,
  not_useful_per_100,
  CASE
    WHEN wrong_per_100 IS NOT NULL THEN format_number(wrong_per_100, 1)
    ELSE replace(replace(:copy__dash__ai__tiles__opened__fewer, '{reports}', format_number(coalesce(wrong_passage, 0), 0)),
                 '{opened}', format_number(opened, 0))
  END AS wrong_per_100_cell
FROM weeks
ORDER BY week_start DESC
