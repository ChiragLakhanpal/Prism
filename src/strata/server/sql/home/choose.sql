-- A viewer removed Home's Start here strip, or showed it again (ticket 41). Each choice is a new row; the latest wins.
INSERT INTO strata.ops.start_here_choices (viewer_id, visible, chosen_at, public_from)
VALUES (:viewer_id, :visible, CAST(:chosen_at AS TIMESTAMP), CAST(:chosen_at AS DATE))
