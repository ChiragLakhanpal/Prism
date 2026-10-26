"""The daily cost pull's entry point on Databricks serverless compute (bundle/costs.yml; ticket 45).

    cost_task.py --run-id <job run id> --src <synced src folder> --secret-scope <scope>

Serverless Python tasks do not tell a script where its own file is, so the job passes the folder that holds the
strata package with --src. This file reads the service principal's sign-in and the subscription from the secret
scope, pulls the charges with strata.lakehouse.costs on a Spark engine, then writes the Governance page's Azure spend
sentence (strata.dashboard.findings). Key values never reach a log: it prints only which keys it found.
"""

import datetime as dt
import sys

KEYS = ("FOUNDRY_TENANT_ID", "FOUNDRY_CLIENT_ID", "FOUNDRY_CLIENT_SECRET", "AZURE_SUBSCRIPTION_ID")


def option(argv, name):
    for number, part in enumerate(argv):
        if part == name and number + 1 < len(argv):
            return argv[number + 1]
    return None


def main(argv, engine, secret, clock=lambda: dt.datetime.now(dt.UTC)):
    """Pull the charges and write the spend sentence. secret(name) reads one key from the scope."""
    from strata.config import load_budget
    from strata.dashboard import findings
    from strata.lakehouse import costs

    found = {}
    for key in KEYS:
        try:
            found[key] = secret(key)
        except Exception:  # noqa: BLE001 - dbutils raises its own error for a key the scope does not hold
            found[key] = None
    missing = [key for key, value in found.items() if not value]
    print(f"Keys read from the secret scope: {', '.join(key for key in KEYS if key not in missing) or 'none'}.")
    run_id = option(argv, "--run-id") or "local"
    budget = load_budget()
    if missing:
        source = None
    else:
        source = costs.AzureCostManagement(found["AZURE_SUBSCRIPTION_ID"], budget.resource_group,
                                           found["FOUNDRY_TENANT_ID"], found["FOUNDRY_CLIENT_ID"],
                                           found["FOUNDRY_CLIENT_SECRET"])
    try:
        if source is None:
            raise costs.CostError("not_authorized", f"The secret scope lacks {', '.join(missing)}.")
        costs.pull(engine, source, run_id, clock, budget)
    finally:
        findings.write(engine, run_id, clock, sections=("spend",))


if __name__ == "__main__":
    arguments = sys.argv[1:]
    src = option(arguments, "--src")
    if src is None:
        raise SystemExit("Pass the folder that holds the strata package with --src.")
    sys.path.insert(0, src)

    from databricks.sdk.runtime import dbutils
    from pyspark.sql import SparkSession

    from strata.lakehouse.engine import SparkEngine

    scope = option(arguments, "--secret-scope") or "strata"
    main(arguments, SparkEngine(SparkSession.builder.getOrCreate()), lambda key: dbutils.secrets.get(scope, key))
