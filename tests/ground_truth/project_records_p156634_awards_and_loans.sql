-- Two of project_records' five parts on P156634 as of October 22, 2026, written as plain SQL over the contract
-- and loan tables, apart from the tool's own code (src/strata/tools/project_records.py):
--
-- awards: each contract signed after the latest ISR's date, ISR 19 of June 30, 2026: KE-CWSB-567630-CW-DIR, signed
-- on August 28, 2026, and KE-CWSB-565568-GO-RFQ, signed on September 4, 2026 (tests/ground_truth/values.toml,
-- award-567630-signed and award-565568-signed).
--
-- disbursement: each loan or credit the loans data holds for the project, the two credits IDA60290 and IDA60300
-- that the loan history records (data/fixture/recorded/api/credits/P156634-P130164-history.json).
-- param: project_id = P156634
-- param: as_of = 2026-10-22
-- param: since = 2026-06-30
-- expect: part,reference,signed
-- expect: awards,KE-CWSB-567630-CW-DIR,2026-08-28
-- expect: awards,KE-CWSB-565568-GO-RFQ,2026-09-04
-- expect: disbursement,IDA60290,
-- expect: disbursement,IDA60300,
SELECT 'awards' AS part, c.step_reference AS reference, CAST(c.contract_signing_date AS STRING) AS signed
FROM strata.gold.contract AS c
WHERE c.project_id = :project_id
  AND c.public_from <= CAST(:as_of AS DATE)
  AND c.contract_signing_date > CAST(:since AS DATE)
UNION ALL
SELECT DISTINCT 'disbursement' AS part, l.loan_number AS reference, CAST(NULL AS STRING) AS signed
FROM strata.gold.loan AS l
WHERE l.project_id = :project_id
  AND l.public_from <= CAST(:as_of AS DATE)
ORDER BY part, signed, reference
