-- The day of the first measure, whenever it became public: the page says when its measures start
-- when it is asked for a date before them.
SELECT min(public_from) AS first_measured_on
FROM strata.ops.data_readiness
