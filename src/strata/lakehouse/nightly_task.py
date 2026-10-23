"""The nightly job's entry point on Databricks serverless compute.

Every task in bundle/nightly.yml runs this file with its own name:

    nightly_task.py --task <task key> --run-id <job run id> --src <synced src folder>

Serverless Python tasks do not tell a script where its own file is (docs/PLAN.md section 12), so
the job passes the folder that holds the strata package with --src. This file puts that folder on
the import path and hands the task to strata.lakehouse.nightly.main with a Spark engine. It never
calls sys.exit on success, so the task ends the way a script that finishes does.
"""

import sys


def src_folder(argv):
    for number, part in enumerate(argv):
        if part == "--src" and number + 1 < len(argv):
            return argv[number + 1]
        if part.startswith("--src="):
            return part.split("=", 1)[1]
    raise SystemExit("Pass the folder that holds the strata package with --src.")


if __name__ == "__main__":
    arguments = sys.argv[1:]
    sys.path.insert(0, src_folder(arguments))

    from pyspark.sql import SparkSession

    from strata.lakehouse.engine import SparkEngine
    from strata.lakehouse.nightly import fetch_live, main

    main(arguments, SparkEngine(SparkSession.builder.getOrCreate()), fetch_live)
