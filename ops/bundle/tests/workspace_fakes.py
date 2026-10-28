"""The workspace's state as ops/bundle/workspace_state.py reads it, shared by the fake workspaces of the three commands
that read it first: the App deploy (ops/app/tests/test_deploy_app.py), the bundle deploy
(ops/bundle/tests/test_deploy.py) and the demo-ready command (tests/test_demo_ready.py). Ticket 81 made the reads; its
review's follow-up 6 put the fakes in one place (ticket 62).

A fake workspace inherits WorkspaceStateFake, calls hold_state() from its own __init__, and keeps its apps in
self.apps, each with "running". It records an App start in app_started(), which a fake may write its own way.
"""

# What apps get strata answered at 13:01 UTC on October 26, 2026 (docs/workspace-catchup.md, ticket 06).
STOPPED_BY_THE_WORKSPACE = {"state": "STOPPED", "message": "App compute was stopped due to workspace or account status."}
# What databricks warehouses start answered at 10:33 UTC on October 25, 2026 (docs/workspace-catchup.md, ticket 11).
FREE_DAILY_LIMIT = "Sorry, cannot run the resource because you have hit your free daily limit. Please come back again tomorrow."
# How each refusal ends, as the commands print it.
USUAL_CAUSE = ("which on Free Edition usually means the workspace reached its daily compute limit, and on a paid "
               "workspace that the account or its subscription needs attention.")
# The reads and starts refusal() calls, which a command's live adapter has as the fake does.
STATE_METHODS = {"app_compute", "warehouse_state", "start_warehouse", "start_app"}


class WorkspaceStateFake:
    def hold_state(self, compute=None, warehouse="RUNNING", warehouse_answer=None, warehouse_id="wh-1",
                   app_answer=None):
        """The App's compute as apps get gives it, when a test sets it; the env file's SQL warehouse, which answers a
        start with warehouse_answer when a test sets it, or refuses to be read when that is an exception; and an App
        start, which fails with app_answer when a test sets it."""
        self.compute = compute
        self.warehouse = {"id": warehouse_id, "state": warehouse, "message": ""}
        self.warehouse_answer, self.warehouse_starts = warehouse_answer, 0
        self.app_answer = app_answer

    def app_compute(self, name):
        if name not in self.apps:
            return None
        if self.compute:
            return dict(self.compute)
        running = self.apps[name]["running"]
        return {"state": "ACTIVE" if running else "STOPPED",
                "message": "App compute is running." if running else "App compute is stopped."}

    def warehouse_state(self):
        if isinstance(self.warehouse_answer, Exception):  # the warehouses API itself refused
            raise self.warehouse_answer
        return dict(self.warehouse)

    def start_warehouse(self):
        self.warehouse_starts += 1
        if self.warehouse_answer:
            raise RuntimeError(self.warehouse_answer)
        self.warehouse["state"] = "RUNNING"

    def start_app(self, name):
        if self.app_answer:
            raise RuntimeError(self.app_answer)
        self.compute = None  # it runs now, so apps get reads the App's own state again
        self.app_started(name)

    def app_started(self, name):
        self.apps[name]["running"] = True
