"""The probes' live adapters: the calls that reach Databricks, Azure and the World Bank.

The offline tests pass fake adapters to each probe instead, and test only the standard-library
helpers here (render_source, parse_result, fetch_status) and the code under workspace/. The
Databricks SDK is imported inside the functions that need it, so importing this module needs
only the standard library. Every failure the platform reports becomes a ProbeError that names
the step, so a probe can record it as a result instead of crashing. A step that only gets a
test ready raises SetupError instead, so its failure records the test as not run.
"""

from __future__ import annotations

import base64
import contextlib
import datetime as dt
import io
import json
import os
import re
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from dayone import ProbeError, SetupError, count_words

HERE = Path(__file__).resolve().parent
WORKSPACE_SOURCES = HERE / "workspace"
PROGRAMMING_ERRORS = (NameError, AttributeError, TypeError, SyntaxError, ImportError, AssertionError)


@contextlib.contextmanager
def step(what: str, failure: type[ProbeError] = ProbeError):
    """Turn whatever the platform raises during `what` into a failure that names the step.

    Pass failure=SetupError for a step that only gets the test ready.
    """
    try:
        yield
    except ProbeError:
        raise
    except PROGRAMMING_ERRORS:
        raise
    except Exception as error:  # SDK, HTTP and subprocess errors all land here
        message = " ".join(str(error).split()) or type(error).__name__
        raise failure(f"{what} failed: {message[:400]}") from error


# ── Databricks ───────────────────────────────────────────────────────────

def workspace(env: dict):
    """A workspace client from the env file's token or service principal, never from a shell profile."""
    for key in [k for k in os.environ if k.startswith("DATABRICKS_")]:
        del os.environ[key]
    from databricks.sdk import WorkspaceClient

    host = env["DATABRICKS_HOST"]
    if env.get("DATABRICKS_TOKEN"):
        return WorkspaceClient(host=host, token=env["DATABRICKS_TOKEN"], auth_type="pat")
    if env.get("DATABRICKS_CLIENT_ID") and env.get("DATABRICKS_CLIENT_SECRET"):
        return WorkspaceClient(host=host, client_id=env["DATABRICKS_CLIENT_ID"],
                               client_secret=env["DATABRICKS_CLIENT_SECRET"], auth_type="oauth-m2m")
    raise SetupError("The env file has no Databricks token or service principal. "
                     "Run the wizard first: bash ops/wizard/strata-setup.sh")


class LiveGenie:
    def __init__(self, env: dict):
        self.w = workspace(env)

    def user_id(self) -> str:
        with step("Reading the token's user", SetupError):
            return str(self.w.current_user.me().id)

    def ask(self, space_id: str, question: str) -> dict:
        with step("Asking Genie"):
            message = self.w.genie.start_conversation_and_wait(space_id, question,
                                                               timeout=dt.timedelta(minutes=10))
        answers = []
        for attachment in message.attachments or []:
            text = getattr(getattr(attachment, "text", None), "content", None)
            query = getattr(getattr(attachment, "query", None), "query", None)
            answers += [part for part in (text, query and f"SQL: {query}") if part]
        error = getattr(message.error, "error", None) if message.error else None
        return {"status": message.status.value if message.status else "UNKNOWN",
                "user_id": str(message.user_id), "conversation_id": message.conversation_id,
                "message_id": message.message_id or message.id, "answer": " ".join(answers)[:300], "error": error}


# ── Code that runs inside Databricks ─────────────────────────────────────

SETTINGS_MARK = "__STRATA_DAYONE_SETTINGS__"
NOTEBOOK_HEADER = "# Databricks notebook source"
RESULT_MARK = "STRATA_DAYONE_RESULT "


USER_AGENT = "strata-dayone-probe"  # documents.worldbank.org answers Python's default agent with 403


def read_url(url: str, timeout: int = 60) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def fetch_status(url: str, timeout: int = 20):
    """The HTTP status a URL answers with, or why it did not answer.

    workspace/ holds three copies, and test_workspace_code.py checks that all four match.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception as error:  # DNS, a refused connection or a timeout: the host did not answer
        return f"no answer ({type(error).__name__}: {str(error)[:120]})"


def render_source(filename: str, settings: dict, notebook: bool) -> str:
    """A file under workspace/ with its settings written in. A job's copy drops the notebook header."""
    text = (WORKSPACE_SOURCES / filename).read_text().replace(SETTINGS_MARK, json.dumps(settings))
    if not notebook and text.startswith(NOTEBOOK_HEADER):
        text = text[len(NOTEBOOK_HEADER):].lstrip("\n")
    return text


def parse_result(text: str) -> dict:
    """The JSON a workspace script returned as a notebook's exit value or printed after RESULT_MARK."""
    text = (text or "").strip()
    if text.startswith("{"):
        return json.loads(text)
    for line in reversed(text.splitlines()):
        if line.startswith(RESULT_MARK):
            return json.loads(line[len(RESULT_MARK):])
    raise SetupError(f"The run printed no result line. Its last output was: {text[-300:] or 'nothing'}")


def workspace_folder(w, config: dict) -> str:
    with step("Reading the token's user", SetupError):
        me = w.current_user.me().user_name
    return f"/Workspace/Users/{me}/{config['names']['workspace_folder']}"


RUN_MINUTES = 30  # how long a probe's job or notebook run may take


def run_on_serverless(w, config: dict, name: str, source: str, notebook: bool) -> tuple[str, str]:
    """Run source once on serverless compute. Returns the run's page and what it returned or printed.

    The scripts under workspace/ catch every error they test for and always print a result. So a
    run that fails before it prints one never tested anything, and it raises SetupError. Databricks
    stops a run at the same deadline the probe waits for, so a stuck run cannot use up the daily
    serverless quota.
    """
    from databricks.sdk.service import compute, jobs
    from databricks.sdk.service import workspace as ws

    folder = workspace_folder(w, config)
    kind = "notebook" if notebook else "job"
    with step(f"Uploading {name} to {folder}", SetupError):
        w.workspace.mkdirs(folder)
        if notebook:
            path = f"{folder}/{name}_notebook"  # a notebook and a file may not share a base name
            w.workspace.import_(path=path, content=base64.b64encode(source.encode()).decode(),
                                format=ws.ImportFormat.SOURCE, language=ws.Language.PYTHON, overwrite=True)
            task = jobs.SubmitTask(task_key="probe",
                                   notebook_task=jobs.NotebookTask(notebook_path=path, source=jobs.Source.WORKSPACE))
            environments = None
        else:
            path = f"{folder}/{name}_job.py"
            w.workspace.upload(path, source.encode(), format=ws.ImportFormat.AUTO, overwrite=True)
            task = jobs.SubmitTask(task_key="probe", environment_key="probe",
                                   spark_python_task=jobs.SparkPythonTask(python_file=path,
                                                                          source=jobs.Source.WORKSPACE))
            environments = [jobs.JobEnvironment(environment_key="probe",
                                                spec=compute.Environment(environment_version="2"))]
    with step(f"Starting the {kind} run", SetupError):
        waiter = w.jobs.submit(run_name=f"strata-dayone-{name}-{kind}", tasks=[task], environments=environments,
                               timeout_seconds=RUN_MINUTES * 60)
        run_id = waiter.run_id
    try:
        waiter.result(timeout=dt.timedelta(minutes=RUN_MINUTES))
    except PROGRAMMING_ERRORS:
        raise
    except Exception:  # a failed run still has a page and an output, which are read next
        pass
    with step(f"Reading the {kind} run's output", SetupError):
        run = w.jobs.get_run(run_id)
        output = w.jobs.get_run_output(run.tasks[0].run_id)
    text = (output.notebook_output.result if notebook and output.notebook_output else output.logs) or ""
    if output.error and RESULT_MARK not in text and not text.strip().startswith("{"):
        raise SetupError(f"The {kind} run failed before it printed a result: {output.error} ({run.run_page_url})")
    return run.run_page_url, text


# ── The probe app, for tests 1 and 10 ────────────────────────────────────

APP_DIR = WORKSPACE_SOURCES / "probe_app"
# The probes give the app they make this description, so they can tell it from an app someone else made.
PROBE_APP_DESCRIPTION = "Strata day-one probe app"  # the live probe app's, so it keeps the old name (ADR 0006)


def app_headers(env: dict, config: dict) -> dict:
    """Headers that carry the browser sign-in the wizard saved for the Databricks command line."""
    profile = config["names"]["oauth_profile"]
    for key in [k for k in os.environ if k.startswith("DATABRICKS_")]:
        del os.environ[key]
    with step(f"Using the browser sign-in saved under the profile {profile}", SetupError):
        from databricks.sdk.core import Config

        return Config(profile=profile, host=env["DATABRICKS_HOST"]).authenticate()


def call_app(env: dict, config: dict, url: str, path: str, attempts: int = 6) -> dict:
    """GET a route of the probe app and return its JSON, waiting for a freshly started app."""
    headers = app_headers(env, config)
    last = None
    for attempt in range(attempts):
        try:
            request = urllib.request.Request(url.rstrip("/") + path, headers=headers)
            with urllib.request.urlopen(request, timeout=120) as response:
                return json.loads(response.read().decode())
        except (urllib.error.URLError, ValueError, TimeoutError) as error:
            last = error
            if attempt + 1 < attempts:
                time.sleep(15)
    raise SetupError(f"Calling the app at {path} failed: {last}")


def ensure_probe_app(w, env: dict, config: dict) -> str:
    """Deploy the probe app unless it already runs this version. Returns its address.

    It refuses to deploy over an app whose last deployment came from somewhere else, or over an
    app with no deployment that the probes did not make, so a later run of a probe never replaces
    Prism's own app.
    """
    import hashlib

    from databricks.sdk.errors import NotFound
    from databricks.sdk.service import apps
    from databricks.sdk.service import workspace as ws

    name, scope = config["names"]["app"], config["names"]["secret_scope"]
    app_py, requirements = (APP_DIR / "app.py").read_text(), (APP_DIR / "requirements.txt").read_text()
    version = hashlib.sha256((app_py + requirements + json.dumps(config["hosts"])).encode()).hexdigest()[:12]
    app_yaml = (APP_DIR / "app.yaml").read_text().replace(
        SETTINGS_MARK, json.dumps({"hosts": config["hosts"], "version": version}))
    folder = f"{workspace_folder(w, config)}/probe_app"
    secret = apps.AppResource(name="appinsights", secret=apps.AppResourceSecret(
        scope=scope, key="APPLICATIONINSIGHTS_CONNECTION_STRING",
        permission=apps.AppResourceSecretSecretPermission.READ))
    with step(f"Finding or making the app {name}", SetupError):
        try:
            app = w.apps.get(name)
        except NotFound:
            app = w.apps.create_and_wait(apps.App(name=name, description=PROBE_APP_DESCRIPTION,
                                                  resources=[secret]), timeout=dt.timedelta(minutes=20))
    source = getattr(app.active_deployment, "source_code_path", None)
    free_name = "Set names.app in ops/dayone/dayone.toml to a free app name to run this probe."
    if source and source.rstrip("/") != folder:
        raise SetupError(f"The app {name} runs code from {source}, not the probe app, so I left it alone. {free_name}")
    if source is None and app.description != PROBE_APP_DESCRIPTION:
        raise SetupError(f"The probes did not make the app {name}, so I left it alone. {free_name}")
    if app.url and source:
        try:
            if call_app(env, config, app.url, "/dayone", attempts=1).get("version") == version:
                return app.url
        except ProbeError:
            pass
    with step(f"Preparing the app {name}", SetupError):
        if not any(r.name == "appinsights" for r in app.resources or []):
            app = w.apps.update(name, apps.App(name=name, description=app.description,
                                               resources=[*(app.resources or []), secret]))
        if app.compute_status is None or app.compute_status.state != apps.ComputeState.ACTIVE:
            w.apps.start_and_wait(name, timeout=dt.timedelta(minutes=20))
    with step(f"Uploading the probe app to {folder}", SetupError):
        w.workspace.mkdirs(folder)
        for filename, text in (("app.py", app_py), ("requirements.txt", requirements), ("app.yaml", app_yaml)):
            w.workspace.upload(f"{folder}/{filename}", text.encode(), format=ws.ImportFormat.AUTO, overwrite=True)
    with step(f"Deploying the app {name}", SetupError):
        w.apps.deploy_and_wait(name, apps.AppDeployment(source_code_path=folder), timeout=dt.timedelta(minutes=20))
        return w.apps.get(name).url


class LiveHosts:
    """Test 1's places: this computer, a notebook, a job and the probe app."""

    def __init__(self, env: dict, config: dict):
        self.env, self.config = env, config
        self.w = workspace(env)

    def from_here(self, hosts: dict) -> dict:
        return {host: fetch_status(url) for host, url in hosts.items()}

    def _run(self, hosts: dict, notebook: bool):
        source = render_source("reach_hosts.py", {"hosts": hosts}, notebook)
        link, text = run_on_serverless(self.w, self.config, "reach_hosts", source, notebook)
        return link, parse_result(text)

    def from_notebook(self, hosts: dict):
        return self._run(hosts, notebook=True)

    def from_job(self, hosts: dict):
        return self._run(hosts, notebook=False)

    def from_app(self, hosts: dict):
        url = ensure_probe_app(self.w, self.env, self.config)
        return url, call_app(self.env, self.config, url, "/dayone/reach")


def sql(w, warehouse_id: str, statement: str, parameters: dict[str, str] | None = None, minutes: int = 10,
        failure: type[ProbeError] = ProbeError) -> tuple[list, str]:
    """Run one statement on the warehouse and wait for it. Returns its rows and its statement ID.

    Values go in `parameters` and the statement names them as :name, so no value is ever written
    into the statement's text. Pass failure=SetupError for a statement that only gets a test ready.
    """
    from databricks.sdk.service.sql import StatementParameterListItem, StatementState

    first = " ".join(statement.split()[:4])
    bound = [StatementParameterListItem(name=name, value=value) for name, value in (parameters or {}).items()]
    with step(f"Running \"{first} ...\" on the warehouse", failure):
        response = w.statement_execution.execute_statement(statement=statement, warehouse_id=warehouse_id,
                                                           parameters=bound or None, wait_timeout="50s")
        deadline = time.monotonic() + minutes * 60
        while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
            if time.monotonic() > deadline:
                # Stop it, so an abandoned statement does not use up the daily compute quota.
                with contextlib.suppress(Exception):
                    w.statement_execution.cancel_execution(response.statement_id)
                raise failure(f"The statement {response.statement_id} ran longer than {minutes} minutes, "
                              "so I asked the warehouse to cancel it.")
            time.sleep(5)
            response = w.statement_execution.get_statement(response.statement_id)
    if response.status.state != StatementState.SUCCEEDED:
        reason = response.status.error.message if response.status.error else "no message"
        raise failure(f"The statement {response.statement_id} ended {response.status.state.value}: {reason}")
    rows = (response.result.data_array if response.result else None) or []
    return rows, response.statement_id


PLAIN_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def setting_name(name: str, parts: int) -> str:
    """A schema or volume name from dayone.toml, checked before it is written into a statement.

    CREATE SCHEMA and CREATE VOLUME take these names as settings, not as input, because the
    warehouse may not accept a bound name there.
    """
    pieces = name.split(".")
    if len(pieces) != parts or not all(PLAIN_NAME.fullmatch(piece) for piece in pieces):
        example = ".".join(["workspace", "strata_dayone", "files"][:parts])
        raise SetupError(f"{name} in ops/dayone/dayone.toml is not a name of {count_words(parts, 'plain part')}, "
                         f"such as {example}.")
    return name


def create_passage_table(table: str) -> tuple[str, dict[str, str]]:
    return ("CREATE TABLE IF NOT EXISTS IDENTIFIER(:table) (id STRING, text STRING, embedding ARRAY<FLOAT>) "
            "TBLPROPERTIES (delta.enableChangeDataFeed = true)", {"table": table})


def merge_passages(table: str, passages: list) -> tuple[str, dict[str, str]]:
    """A MERGE that adds the passages the table lacks, with every id, text and vector bound."""
    rows, parameters = [], {"table": table}
    for i, (pid, text, vector) in enumerate(passages):
        rows.append(f"(:id{i}, :text{i}, from_json(:vec{i}, 'array<float>'))")
        parameters.update({f"id{i}": pid, f"text{i}": text, f"vec{i}": json.dumps(vector)})
    return ("MERGE INTO IDENTIFIER(:table) AS t USING (SELECT * FROM VALUES " + ", ".join(rows) +
            " AS s(id, text, embedding)) AS s ON t.id = s.id WHEN NOT MATCHED THEN INSERT *"), parameters


# The warehouse must see the uploaded file before the parse can count as a result.
READABLE_SQL = "SELECT length(content) AS bytes FROM READ_FILES(:path, format => 'binaryFile')"

PARSE_SQL = """
WITH parsed AS (
  SELECT ai_parse_document(content) AS doc
  FROM READ_FILES(:path, format => 'binaryFile')
)
SELECT size(try_cast(doc:document:pages AS ARRAY<VARIANT>)) AS pages,
       CAST(doc:error_status AS STRING) AS error_status
FROM parsed
"""


def search_pads(api: str, **filters: str) -> list[dict]:
    """Project Appraisal Documents from the World Bank's documents API, newest first."""
    query = {"format": "json", "rows": "10", "fl": "docty,pdfurl,projectid,docdt",
             "docty_exact": "Project Appraisal Document", "sort": "docdt", "order": "desc", **filters}
    url = f"{api}?{urllib.parse.urlencode(query)}"
    with step(f"Searching the World Bank documents API ({', '.join(filters.values())})"):
        documents = json.loads(read_url(url, timeout=60)).get("documents", {})
    return [{"project": doc.get("projectid", "unknown").split(",")[0],
             "url": doc["pdfurl"].replace("http://", "https://", 1)}
            for doc in documents.values() if isinstance(doc, dict) and doc.get("pdfurl")]


class LivePad:
    """Test 3: find a long PAD, put it in a volume and run ai_parse_document on it."""

    def __init__(self, env: dict, config: dict):
        self.env, self.config = env, config
        self.w = workspace(env)

    def find_pad(self, settings: dict) -> dict:
        import pypdf

        candidates = []
        for project in settings["projects"]:
            candidates += search_pads(settings["search_api"], proid=project)
        candidates += search_pads(settings["search_api"], count_exact=settings["fallback_country"])
        tried = []
        for candidate in candidates[: settings["max_downloads"]]:
            with step(f"Downloading {candidate['url']}"):
                data = read_url(candidate["url"], timeout=300)
                pages = len(pypdf.PdfReader(io.BytesIO(data)).pages)
            if pages >= settings["min_pages"]:
                return {**candidate, "pages": pages, "data": data}
            tried.append(f"{candidate['project']} ({pages} pages)")
        raise ProbeError(f"None of the PADs I tried had {settings['min_pages']} pages or more: {', '.join(tried)}.")

    def parse(self, name: str, data: bytes) -> dict:
        """Everything before PARSE_SQL only gets the PAD ready, so its failures raise SetupError."""
        schema = setting_name(self.config["names"]["schema"], 2)
        volume = setting_name(self.config["names"]["volume"], 3)
        path = "/Volumes/" + volume.replace(".", "/") + f"/{name}"
        warehouse = self.env["DATABRICKS_WAREHOUSE_ID"]
        sql(self.w, warehouse, f"CREATE SCHEMA IF NOT EXISTS {schema}", failure=SetupError)
        sql(self.w, warehouse, f"CREATE VOLUME IF NOT EXISTS {volume}", failure=SetupError)
        with step(f"Uploading the PAD to {path}", SetupError):
            self.w.files.upload(path, io.BytesIO(data), overwrite=True)
        readable, _ = sql(self.w, warehouse, READABLE_SQL, {"path": path}, failure=SetupError)
        if not readable:
            raise SetupError(f"The warehouse could not see {path} after the upload.")
        started = time.monotonic()
        rows, statement = sql(self.w, warehouse, PARSE_SQL, {"path": path}, minutes=30)
        pages, error = (rows[0] + [None, None])[:2] if rows else (None, "The statement returned no rows.")
        if error in ("", "[]", "null"):
            error = None
        return {"pages": int(pages) if pages is not None else None, "error": error,
                "statement": statement, "seconds": time.monotonic() - started, "path": path}


class LiveSearch:
    """Test 4: an AI Search endpoint, a Delta Sync index with its own vectors, and a hybrid query."""

    def __init__(self, env: dict, config: dict):
        self.env = env
        self.w = workspace(env)

    def ensure_endpoint(self, name: str) -> str:
        from databricks.sdk.errors import NotFound
        from databricks.sdk.service.vectorsearch import EndpointStatusState, EndpointType

        with step(f"Finding or making the AI Search endpoint {name}"):
            try:
                info = self.w.vector_search_endpoints.get_endpoint(name)
            except NotFound:
                info = self.w.vector_search_endpoints.create_endpoint_and_wait(
                    name, EndpointType.STANDARD, timeout=dt.timedelta(minutes=40))
            deadline = time.monotonic() + 40 * 60
            waiting = (EndpointStatusState.PROVISIONING, EndpointStatusState.STARTING)
            while info.endpoint_status.state in waiting and time.monotonic() < deadline:
                time.sleep(30)
                info = self.w.vector_search_endpoints.get_endpoint(name)
        return info.endpoint_status.state.value

    def ensure_index(self, endpoint: str, table: str, index: str, dimensions: int, passages: list) -> dict:
        from databricks.sdk.errors import NotFound
        from databricks.sdk.service import vectorsearch as vs

        warehouse = self.env["DATABRICKS_WAREHOUSE_ID"]
        schema = setting_name(table.rsplit(".", 1)[0], 2)
        sql(self.w, warehouse, f"CREATE SCHEMA IF NOT EXISTS {schema}", failure=SetupError)
        sql(self.w, warehouse, *create_passage_table(table), failure=SetupError)
        sql(self.w, warehouse, *merge_passages(table, passages), failure=SetupError)
        with step(f"Finding or making the index {index}"):
            try:
                self.w.vector_search_indexes.get_index(index)
                fresh = False
            except NotFound:
                self.w.vector_search_indexes.create_index(
                    name=index, endpoint_name=endpoint, primary_key="id", index_type=vs.VectorIndexType.DELTA_SYNC,
                    delta_sync_index_spec=vs.DeltaSyncVectorIndexSpecRequest(
                        source_table=table, pipeline_type=vs.PipelineType.TRIGGERED,
                        columns_to_sync=["id", "text", "embedding"],
                        embedding_vector_columns=[vs.EmbeddingVectorColumn(name="embedding",
                                                                           embedding_dimension=dimensions)]))
                fresh = True
        if not fresh:
            with contextlib.suppress(Exception):  # a sync that is already running is fine
                self.w.vector_search_indexes.sync_index(index)
        with step(f"Waiting for the index {index}"):
            deadline = time.monotonic() + 30 * 60
            status = self.w.vector_search_indexes.get_index(index).status
            while not (status and status.ready and (status.indexed_row_count or 0) >= len(passages)):
                if time.monotonic() > deadline:
                    break
                time.sleep(30)
                status = self.w.vector_search_indexes.get_index(index).status
        return {"ready": bool(status and status.ready), "rows": (status.indexed_row_count or 0) if status else 0,
                "message": (status.message or "") if status else ""}

    def hybrid_query(self, index: str, text: str, vector: list) -> list:
        with step("Asking the index a hybrid query"):
            answer = self.w.vector_search_indexes.query_index(index_name=index, columns=["id", "text"],
                                                              query_text=text, query_vector=vector,
                                                              query_type="HYBRID", num_results=3)
        return (answer.result.data_array if answer.result else None) or []


class LiveTraces:
    """Test 10: the probe app sends a span, and Application Insights is asked for it."""

    QUERY = ("union dependencies, requests, traces | where timestamp > ago(2h) "
             "| where tostring(customDimensions['strata.dayone.marker']) == '{marker}' "
             "| project timestamp, itemType, operation_Id | take 5")

    def __init__(self, env: dict, config: dict):
        self.env, self.config = env, config
        self.w = workspace(env)

    def send(self, marker: str) -> dict:
        url = ensure_probe_app(self.w, self.env, self.config)
        return {**call_app(self.env, self.config, url, f"/dayone/trace?marker={marker}"), "app": url}

    def find(self, marker: str, minutes: int = 10) -> list:
        parts = dict(part.split("=", 1) for part in self.env["APPLICATIONINSIGHTS_CONNECTION_STRING"].split(";")
                     if "=" in part)
        app_id = parts.get("ApplicationId")
        if not app_id:
            raise SetupError("The connection string has no ApplicationId, so I cannot ask Application Insights. "
                             "Copy the full connection string from the resource's Overview page with the wizard.")
        body = json.dumps({"query": self.QUERY.format(marker=marker)})
        deadline = time.monotonic() + minutes * 60
        while True:
            answer = az_json("rest", "--method", "post", "--resource", "https://api.applicationinsights.io",
                             "--url", f"https://api.applicationinsights.io/v1/apps/{app_id}/query", "--body", body)
            rows = ((answer or {}).get("tables") or [{}])[0].get("rows") or []
            if rows or time.monotonic() > deadline:
                return rows
            time.sleep(30)


class LiveAzureFromJob:
    """Test 2's job: reach Foundry and Azure OpenAI from serverless job compute."""

    def __init__(self, env: dict, config: dict):
        self.config = config
        self.w = workspace(env)

    def from_job(self, settings: dict):
        source = render_source("azure_from_job.py", settings, notebook=False)
        link, text = run_on_serverless(self.w, self.config, "azure_from_job", source, notebook=False)
        return link, parse_result(text)


# ── Azure, through the az command line the wizard signed in ──────────────

def az_json(*args: str, timeout: int = 180):
    """Run the az command line and parse its JSON. A missing or signed-out az raises SetupError."""
    what = f"az {' '.join(args[:2])}"
    try:
        done = subprocess.run(["az", *args, "-o", "json"], capture_output=True, text=True, timeout=timeout)
    except OSError as error:
        raise SetupError(f"{what} could not start: {error}. Install the Azure command line, then run the "
                         "wizard: bash ops/wizard/strata-setup.sh") from error
    except subprocess.TimeoutExpired as error:
        raise ProbeError(f"{what} did not finish within {timeout} seconds.") from error
    if done.returncode != 0:
        reason = (done.stderr.strip().splitlines() or ["no message"])[-1]
        failure = SetupError if "az login" in done.stderr else ProbeError
        raise failure(f"{what} failed: {reason[:400]}")
    return json.loads(done.stdout or "null")


class LiveAzure:
    """Reads deployments, budgets and the subscription from Azure Resource Manager."""

    def __init__(self, config: dict):
        names = config["names"]
        self.resource_group, self.account = names["resource_group"], names["foundry_resource"]
        try:
            self.subscription_id = az_json("account", "show")["id"]
        except ProbeError as error:  # az can read nothing, so no test can run
            raise SetupError(f"The Azure command line could not read your account. {error}") from error

    def _get(self, path: str, version: str):
        return az_json("rest", "--method", "get", "--url",
                       f"https://management.azure.com{path}?api-version={version}")

    def deployments(self) -> list[dict]:
        return self._get(f"/subscriptions/{self.subscription_id}/resourceGroups/{self.resource_group}"
                         f"/providers/Microsoft.CognitiveServices/accounts/{self.account}/deployments",
                         "2024-10-01").get("value", [])

    def budgets(self) -> list[dict]:
        return self._get(f"/subscriptions/{self.subscription_id}/providers/Microsoft.Consumption/budgets",
                         "2023-05-01").get("value", [])

    def subscription(self) -> dict:
        return self._get(f"/subscriptions/{self.subscription_id}", "2022-12-01")
