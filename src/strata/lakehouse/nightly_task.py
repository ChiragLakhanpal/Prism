"""The nightly job's entry point on Databricks serverless compute.

Every task in bundle/nightly.yml runs this file with its own name:

    nightly_task.py --task <task key> --run-id <job run id> --src <synced src folder>

Serverless Python tasks do not tell a script where its own file is (docs/PLAN.md section 12), so
the job passes the folder that holds the strata package with --src. This file puts that folder on
the import path, reads the tasks' keys from the secret scope that --secret-scope names into the
task's environment (strata.lakehouse.nightly.keys_from_scope), and hands the task to
strata.lakehouse.nightly.main with a Spark engine. It never calls sys.exit on success, so the task
ends the way a script that finishes does.
"""

import os
import sys


def option(argv, name):
    for number, part in enumerate(argv):
        if part == name and number + 1 < len(argv):
            return argv[number + 1]
        if part.startswith(f"{name}="):
            return part.split("=", 1)[1]
    return None


def src_folder(argv):
    found = option(argv, "--src")
    if found is None:
        raise SystemExit("Pass the folder that holds the strata package with --src.")
    return found


if __name__ == "__main__":
    arguments = sys.argv[1:]
    sys.path.insert(0, src_folder(arguments))

    from pyspark.sql import SparkSession

    from strata.lakehouse.engine import SparkEngine
    from strata.lakehouse.nightly import keys_from_scope, main

    scope = option(arguments, "--secret-scope")
    if scope:
        from databricks.sdk.runtime import dbutils

        found = keys_from_scope(dbutils.secrets.get, scope, os.environ)
        print(f"Keys read from the secret scope {scope}: {', '.join(found) or 'none'}.")  # names, never values
    main(arguments, SparkEngine(SparkSession.builder.getOrCreate()))  # pages from the live APIs
