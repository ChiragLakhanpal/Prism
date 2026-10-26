-- Governance's "What the measures say" (tile 4): each section's newest sentence, as the nightly job and the daily
-- cost pull wrote it (strata.ops.dashboard_findings; strata.dashboard.findings), in the page's section order. The
-- page's filters don't change it: each sentence names its own period. Measured is the day its measure was taken,
-- or "Not yet" before the first.
SELECT
  f.position,
  f.about,
  f.finding,
  CASE WHEN f.measured_on IS NULL THEN :copy__dash__findings__notYet
       ELSE date_format(f.measured_on, 'MMM d, yyyy') END AS measured
FROM strata.ops.dashboard_findings AS f
WHERE f.page = 'governance'
  AND f.written_at = (
    SELECT max(n.written_at)
    FROM strata.ops.dashboard_findings AS n
    WHERE n.page = f.page AND n.section = f.section
  )
ORDER BY f.position
