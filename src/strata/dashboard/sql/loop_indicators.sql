-- Each loop's indicators (tile 19): the six rows the nightly job wrote last (strata.ops.loop_indicators), in loop
-- order. Every cell holds words; Measured is the day the measure was taken, or "Not yet".
SELECT
  i.position,
  i.loop,
  i.indicator,
  i.kind,
  i.latest,
  i.target,
  i.against,
  CASE WHEN i.measured_on IS NULL THEN :copy__dash__findings__notYet
       ELSE date_format(i.measured_on, 'MMM d, yyyy') END AS measured
FROM strata.ops.loop_indicators AS i
WHERE i.written_at = (SELECT max(n.written_at) FROM strata.ops.loop_indicators AS n)
ORDER BY i.position
