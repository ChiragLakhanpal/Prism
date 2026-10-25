-- Two of project_signals' four signals on P156634 as of October 22, 2026, written as plain SQL over the plan
-- reader's and the loan history's tables, apart from the tool's own code (src/strata/tools/project_signals.py):
--
-- late_direct: each Direct Selection activity estimated at US$1,000,000 or more whose first listing is in a
-- plan published within 12 months before the closing date, and whose agency's previous plan does not list it.
-- Only KE-CWSB-567630-CW-DIR, first listed in the Coast Water Services Board's plan of August 17, 2026
-- (tests/ground_truth/values.toml, plan-cwsb-567630-first-listed and plan-cwsb-567630-estimated);
-- KE-CWSB-506334-CW-DIR's first listing is that agency's earliest plan read, with none before it.
--
-- closing_moves: the months the loan history first showed a new closing date, counted per project: three,
-- from November 2022 (values.toml, closing-p156634-move-1 to move-3).
--
-- The thresholds are config/thresholds.toml's [signals] late_direct_min_usd and late_direct_months.
-- Changing one there means changing it here in the same change (CLAUDE.md rule 4).
-- param: project_id = P156634
-- param: as_of = 2026-10-22
-- param: closing = 2026-10-31
-- param: since = 2025-10-31
-- param: min_usd = 1000000
-- expect: signal,reference,value
-- expect: closing_moves,P156634,3
-- expect: late_direct,KE-CWSB-567630-CW-DIR,2600000.00
SELECT 'late_direct' AS signal, r.activity_reference_no AS reference,
  CAST(r.estimated_amount_usd AS STRING) AS value
FROM strata.silver.plan_listings AS l
JOIN strata.silver.plan_versions AS v ON v.document_id = l.document_id
JOIN strata.silver.plan_rows AS r ON r.document_id = l.document_id AND r.activity_reference_no = l.activity_reference_no
WHERE l.project_id = :project_id
  AND l.is_first_listing
  AND l.public_from <= CAST(:as_of AS DATE)
  AND v.previous_document_id IS NOT NULL
  AND v.plan_date >= CAST(:since AS DATE)
  AND v.plan_date <= CAST(:closing AS DATE)
  AND r.method = 'Direct Selection'
  AND r.estimated_amount_usd >= CAST(:min_usd AS DECIMAL(18, 2))
UNION ALL
SELECT 'closing_moves' AS signal, h.project_id AS reference, CAST(count(*) AS STRING) AS value
FROM strata.gold.project_closing_date AS h
WHERE h.project_id = :project_id
  AND h.previous_closing_date IS NOT NULL
  AND h.public_from <= CAST(:as_of AS DATE)
GROUP BY h.project_id
ORDER BY signal
