"""Prism day-one test 2: reach the Foundry and Azure OpenAI endpoints from a Databricks job.

probe_azure_from_job.py uploads this file as a job's Python file, with the endpoints and the
secret scope written in where SETTINGS is read. It reads the Azure OpenAI key from the app's
secret scope, never from the command line. It asks both endpoints once without a key, because
any HTTP answer shows the network allows the call, then lists the Azure OpenAI models with the
key. It prints one line that starts with STRATA_DAYONE_RESULT.
"""

import json
import urllib.error
import urllib.request

SETTINGS = json.loads(r"""__STRATA_DAYONE_SETTINGS__""")


def fetch_status(url, headers=None, timeout=30):
    request = urllib.request.Request(url, headers={"User-Agent": "strata-dayone-probe", **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:  # DNS, a refused connection or a timeout: the endpoint did not answer
        return f"no answer ({type(error).__name__}: {str(error)[:120]})"


models = SETTINGS["openai_endpoint"].rstrip("/") + "/models"
result = {"foundry": fetch_status(SETTINGS["foundry_endpoint"]), "openai": fetch_status(models)}
try:
    from databricks.sdk.runtime import dbutils

    key = dbutils.secrets.get(SETTINGS["scope"], "AZURE_OPENAI_API_KEY")
    result["openai_with_key"] = fetch_status(models, {"api-key": key})
except Exception as error:  # the scope or the key is missing
    result["openai_with_key"] = f"no key ({type(error).__name__}: {str(error)[:120]})"
print("STRATA_DAYONE_RESULT " + json.dumps(result))
