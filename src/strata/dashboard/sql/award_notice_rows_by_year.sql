-- The contracts gold builds from award notices for the fiscal years no awards dataset covers (the
-- awards source's known gap, fy2017_2019; gold/contract.sql), by fiscal year. The snapshot writes them
-- as tile 4's third dataset. The app shows these years as a Gap row with no count.
SELECT fiscal_year, count(*) AS records
FROM strata.gold.contract
WHERE source = 'notices'
GROUP BY fiscal_year
