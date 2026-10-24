"""The quarterly lesson cross-check's entry point on Databricks serverless compute (bundle/lessons.yml).

    cross_check_task.py --src <synced src folder>

Serverless Python tasks do not tell a script where its own file is (docs/PLAN.md section 12), so the job
passes the folder that holds the strata package with --src. This file puts that folder on the import path
and hands the run to strata.knowledge.lessons.cross_check.main with a Spark engine.
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

    from strata.knowledge.lessons.cross_check import main
    from strata.lakehouse.engine import SparkEngine

    main(arguments, SparkEngine(SparkSession.builder.getOrCreate()))
