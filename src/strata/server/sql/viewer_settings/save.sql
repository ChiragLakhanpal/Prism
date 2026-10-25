-- A viewer chose the language of answers and drafts (ticket 42). Each change is a new row; the latest wins.
INSERT INTO strata.ops.viewer_settings (viewer_id, working_language, changed_at, public_from)
VALUES (:viewer_id, :working_language, CAST(:changed_at AS TIMESTAMP), CAST(:changed_at AS DATE))
