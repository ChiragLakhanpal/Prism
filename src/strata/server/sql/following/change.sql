-- Following (ticket 37): a viewer followed or unfollowed a project. Each change is a new row; the latest wins.
INSERT INTO strata.ops.follows (viewer_id, project_id, following, changed_at, public_from)
VALUES (:viewer_id, :project_id, :following, CAST(:changed_at AS TIMESTAMP), CAST(:changed_at AS DATE))
