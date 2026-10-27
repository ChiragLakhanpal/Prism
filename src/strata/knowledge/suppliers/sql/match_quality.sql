-- How often auto-merge is right on the pairs people labeled (strata.ops.supplier_match_quality): the
-- latest run's candidate pairs (strata.ops.supplier_pairs), each with its latest label
-- (strata.ops.supplier_pair_labels) given to the pair's two names. A pair that auto-merged is right when its
-- label is merge.
--
-- Below :min_labeled labeled auto-merged pairs, the precision and its interval stay empty (DESIGN.md
-- section 7, rules 6 and 15). The interval is the 95% Wilson score interval, with :z from the
-- thresholds file. lowest_threshold_meeting_target is the lowest match probability at which the
-- labeled pairs at or above it, at least :min_labeled of them, are right at :precision_target or more.
WITH pairs AS (
  SELECT p.pair_id, p.left_name, p.right_name, p.match_probability, p.route
  FROM strata.ops.supplier_pairs AS p
  WHERE p.run_id = (SELECT max_by(q.run_id, q.matched_at) FROM strata.ops.supplier_pairs AS q)
),
labels AS (
  SELECT l.pair_id, l.left_name, l.right_name, l.label
  FROM strata.ops.supplier_pair_labels AS l
  QUALIFY row_number() OVER (PARTITION BY l.pair_id, l.left_name, l.right_name ORDER BY l.labeled_at DESC) = 1
),
labeled AS (
  SELECT p.match_probability, p.route, l.label
  FROM pairs AS p
  JOIN labels AS l ON l.pair_id = p.pair_id AND l.left_name = p.left_name AND l.right_name = p.right_name
),
counted AS (
  SELECT
    (SELECT count(*) FROM pairs) AS candidate_pairs,
    (SELECT count(*) FROM labeled) AS labeled_pairs,
    (SELECT count(*) FROM pairs WHERE route = 'auto_merge') AS auto_merged,
    (SELECT count(*) FROM labeled WHERE route = 'auto_merge') AS labeled_auto_merged,
    (SELECT count(*) FROM labeled WHERE route = 'auto_merge' AND label = 'merge') AS labeled_auto_merged_right
),
at_each_probability AS (
  SELECT
    t.match_probability AS threshold,
    count(*) AS labeled_at_or_above,
    count(CASE WHEN l.label = 'merge' THEN 1 END) AS right_at_or_above
  FROM (SELECT DISTINCT match_probability FROM labeled) AS t
  JOIN labeled AS l ON l.match_probability >= t.match_probability
  GROUP BY t.match_probability
),
lowest AS (
  SELECT min(threshold) AS threshold
  FROM at_each_probability
  WHERE labeled_at_or_above >= :min_labeled AND right_at_or_above >= :precision_target * labeled_at_or_above
),
measured AS (
  SELECT
    c.*,
    CASE WHEN c.labeled_auto_merged >= :min_labeled
         THEN CAST(c.labeled_auto_merged_right AS DOUBLE) / c.labeled_auto_merged END AS share,
    CAST(c.labeled_auto_merged AS DOUBLE) AS n
  FROM counted AS c
)
SELECT
  m.candidate_pairs,
  m.labeled_pairs,
  m.auto_merged,
  m.labeled_auto_merged,
  m.labeled_auto_merged_right,
  m.share AS auto_merge_precision,
  CASE WHEN m.share IS NOT NULL THEN
    (m.share + :z * :z / (2 * m.n) - :z * sqrt(m.share * (1 - m.share) / m.n + :z * :z / (4 * m.n * m.n)))
      / (1 + :z * :z / m.n) END AS interval_low,
  CASE WHEN m.share IS NOT NULL THEN
    (m.share + :z * :z / (2 * m.n) + :z * sqrt(m.share * (1 - m.share) / m.n + :z * :z / (4 * m.n * m.n)))
      / (1 + :z * :z / m.n) END AS interval_high,
  (SELECT threshold FROM lowest) AS lowest_threshold_meeting_target
FROM measured AS m
