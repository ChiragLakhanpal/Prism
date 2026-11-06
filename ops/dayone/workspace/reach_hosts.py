# Databricks notebook source
"""Prism day-one test 1: ask each World Bank host once from this Databricks compute.

probe_hosts.py uploads this file twice, as a notebook and as a job's Python file, with the hosts
written in where SETTINGS is read. It prints one line that starts with STRATA_DAYONE_RESULT and,
in a notebook, also returns the result as the notebook's exit value.
"""

import json
import urllib.error
import urllib.request

SETTINGS = json.loads(r"""__STRATA_DAYONE_SETTINGS__""")


def fetch_status(url, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": "strata-dayone-probe"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:  # DNS, a refused connection or a timeout: the host did not answer
        return f"no answer ({type(error).__name__}: {str(error)[:120]})"


result = json.dumps({host: fetch_status(url) for host, url in SETTINGS["hosts"].items()})
print("STRATA_DAYONE_RESULT " + result)
try:
    dbutils.notebook.exit(result)  # noqa: F821  dbutils exists only when this runs as a notebook
except NameError:
    pass
