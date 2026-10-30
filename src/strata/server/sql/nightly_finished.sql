-- When the nightly job last finished a task (strata.ops.pipeline_runs), which the App's warm reads each time it runs
-- (ticket 125; src/strata/server/warm.py): a later time than the one it saw before means the night's data changed,
-- so every page the App keeps goes. NULL before any run.
SELECT max(finished_at) AS finished_at
FROM strata.ops.pipeline_runs
