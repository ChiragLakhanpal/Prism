"""Whether the workspace can run Strata now: the App's compute and the SQL warehouse, read through the SDK before a
command changes anything (ticket 81).

On October 26, 2026 Free Edition's daily limit stopped the SQL warehouse at 12:53 UTC and the App's compute at 12:57.
An App deploy at 14:55 printed steps 1 to 5 as if they had passed, registered no deployment, and failed in step 6 with
TABLE_DOES_NOT_EXIST for a table that existed, because the stopped warehouse answered every statement with an error.
So ops/app/deploy_app.py, ops/bundle/deploy.py and ops/demo/ready.py call refusal() first, and stop with its one
sentence when the workspace cannot run them.

refusal() takes any object with these methods, and the offline tests pass fakes:

- app_compute(name): the App's compute as {"state", "message"}, as apps get gives it, or None when there is no such App;
- start_app(name): start the App's compute and wait until it runs, or raise with what the workspace answered;
- warehouse_state(): the env file's SQL warehouse as {"id", "state", "message"}, as warehouses get gives it;
- start_warehouse(): start the warehouse and wait until it runs, or raise with what the workspace answered.

A command that cannot read the state says so in one sentence (unreadable) instead of a traceback.

The live readers below take the SDK's WorkspaceClient, so the three live adapters share one copy. They read the SDK's
objects by their attributes and import the SDK only to tell a missing App from another error, so importing this file
needs only the standard library.
"""

from __future__ import annotations

import datetime as dt

# apps get's compute_status message when the workspace, not a person, stopped the App (October 26, 2026, 13:01 UTC).
BY_THE_WORKSPACE = "workspace or account status"
# On the paid workspace a stop "due to workspace or account status" that will not start again points to the account
# (ticket 81's review, follow-up 5).
USUAL_CAUSE = ("which on Free Edition usually means the workspace reached its daily compute limit, and on a paid "
               "workspace that the account or its subscription needs attention")
STARTING_MINUTES = 10  # how long a stopped warehouse may take to start; a serverless one takes seconds
APP_STARTING_MINUTES = 20  # how long the App's compute may take to start, as ops/app/app_live.py allows


def one_line(text) -> str:
    return " ".join(str(text).split())


def app_stopped_by_the_workspace(compute: dict | None) -> bool:
    """The App's compute is STOPPED, and apps get says the workspace or the account stopped it. An App a person or
    the 24-hour limit stopped starts again, so that one is not a refusal."""
    return bool(compute) and compute.get("state") == "STOPPED" and BY_THE_WORKSPACE in (compute.get("message") or "").lower()


def refusal(workspace, app: str | None = None) -> str | None:
    """The one sentence that says why the workspace cannot run the command now, or None when it can. With app, the
    App's compute comes first. An App the workspace stopped, and a stopped warehouse, are each asked to start, since
    apps get may keep the workspace's message after the workspace runs again (ticket 81's review, follow-up 1) and a
    warehouse that stopped when it sat idle starts again on the first statement; only one that will not start is a
    refusal."""
    if app is not None:
        compute = workspace.app_compute(app)
        if app_stopped_by_the_workspace(compute):
            try:
                workspace.start_app(app)
            except Exception as error:  # the workspace refused the start, or the compute stopped again
                return (f"I changed nothing, because the app {app}'s compute is STOPPED with the message "
                        f"\"{one_line(compute['message'])}\" and would not start when I asked, saying "
                        f"\"{one_line(error) or type(error).__name__}\", {USUAL_CAUSE}.")
    warehouse = workspace.warehouse_state()
    if warehouse.get("state") == "STOPPED":
        try:
            workspace.start_warehouse()
        except Exception as error:  # the workspace refused the start, or the warehouse stopped again
            return (f"I changed nothing, because the SQL warehouse {warehouse['id']} is STOPPED and would not start "
                    f"when I asked, saying \"{one_line(error) or type(error).__name__}\", {USUAL_CAUSE}.")
    return None


def unreadable(error: BaseException) -> str:
    """The one sentence a deploy says when it could not read the App's compute or the warehouse's state, before it
    exits 2 having changed nothing (ticket 81's review, follow-up 2)."""
    return (f"I changed nothing, because I could not read the app's compute or the SQL warehouse's state: "
            f"{type(error).__name__}: {one_line(error).rstrip('.')}.")


def refused_statement(workspace, statement: str, error: BaseException) -> tuple[list[str], bool]:
    """The lines that say a statement the warehouse refused: the warehouse's state first, then the statement and the
    warehouse's answer, and whether the warehouse was running. A stopped warehouse answered the deploy of 14:55 UTC on
    October 26, 2026 with TABLE_DOES_NOT_EXIST for a table that existed, so the state comes before the answer."""
    running = False
    try:
        warehouse = workspace.warehouse_state()
    except Exception as unread:  # the warehouses API refused too
        first = (f"   The SQL warehouse refused this statement, and I could not read its state: "
                 f"{one_line(unread) or type(unread).__name__}")
    else:
        state, message = warehouse.get("state") or "UNKNOWN", one_line(warehouse.get("message") or "")
        said = f", with the message \"{message}\"" if message else ""
        running = state == "RUNNING"
        if running:
            first = (f"   The SQL warehouse {warehouse['id']} was RUNNING when it refused this statement{said}, so its "
                     "answer below is about the statement.")
        else:
            first = (f"   The SQL warehouse {warehouse['id']} was {state} when it refused this statement{said}. A "
                     "warehouse that is not running refuses every statement, so its answer below may not mean what it "
                     "says.")
    return [first, f"   The statement: {statement}",
            f"   The warehouse said: {one_line(error) or type(error).__name__}"], running


# ── The live readers, which take the SDK's WorkspaceClient ───────────────

def _text(value) -> str | None:
    """An SDK enum's value, such as "STOPPED", or None."""
    return None if value is None else str(getattr(value, "value", value))


def moment(text: str | None) -> dt.datetime | None:
    """An ISO 8601 time from the Apps API, in UTC."""
    if not text:
        return None
    found = dt.datetime.fromisoformat(text)
    return (found if found.tzinfo else found.replace(tzinfo=dt.UTC)).astimezone(dt.UTC)


def app_compute(w, name: str) -> dict | None:
    """The App's compute status, as apps get gives it, or None when there is no such App. The SDK is imported only to
    tell a missing App from another error."""
    try:
        found = w.apps.get(name)
    except Exception as error:
        from databricks.sdk.errors import NotFound

        if isinstance(error, NotFound):
            return None
        raise
    status = found.compute_status
    return {"state": _text(status.state) if status else None, "message": (status.message or "") if status else ""}


def start_app(w, name: str, minutes: int = APP_STARTING_MINUTES) -> None:
    """Start the App's compute and wait until it runs. The SDK raises when the workspace refuses the start, when the
    compute stops again, or when it is not running within the minutes."""
    w.apps.start_and_wait(name, timeout=dt.timedelta(minutes=minutes))


def warehouse_state(w, warehouse_id: str) -> dict:
    """The SQL warehouse's state, as warehouses get gives it, with its health summary when it has one."""
    found = w.warehouses.get(warehouse_id)
    health = found.health
    message = (health.summary or health.message or "") if health else ""
    return {"id": warehouse_id, "state": _text(found.state), "message": message}


def start_warehouse(w, warehouse_id: str, minutes: int = STARTING_MINUTES) -> None:
    """Start the SQL warehouse and wait until it runs. The SDK raises when the workspace refuses the start, when the
    warehouse stops again, or when it is not running within the minutes."""
    w.warehouses.start_and_wait(warehouse_id, timeout=dt.timedelta(minutes=minutes))


def deployments(w, name: str) -> list[dict]:
    """The App's deployments, as apps list-deployments gives them: each one's id, state, message and creation time."""
    found = []
    for deployment in w.apps.list_deployments(name):
        status = deployment.status
        found.append({"id": deployment.deployment_id, "state": _text(status.state) if status else None,
                      "message": (status.message or "") if status else "", "created": moment(deployment.create_time)})
    return found
