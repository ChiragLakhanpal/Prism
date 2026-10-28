"""Microsoft Foundry: the project that keeps the agents, and the agent the answer loop talks to (ADR 0001).

Two things are kept in Foundry and Azure, and both are built from the repo (strata.agent.definition):

- the prompt agent, one version per change, on the Foundry project's REST API;
- its guardrail, an RAI policy on the Foundry resource, on Azure Resource Manager.

The adapters:

- LocalFoundry, offline: a project kept in memory, for the gate's sync tests. It is not Foundry.
- FoundryProject, live: the project's agents API and the resource's RAI policies, with an Entra token for
  each (ops/agent/sync.py gets them from the az command line the wizard signed in).
- FoundryAgent, live: one agent through the Responses API, as the answer loop's Agent. It passes the
  request's trace on in a traceparent header, so Foundry's spans join the app's trace in Application
  Insights. A content filter or Prompt Shields refusal becomes the error code content_filter, and any
  other failure agent_unavailable; the details stay in the server log. A call Foundry refuses as busy, 429 or
  503, is first tried again after the wait it names, up to config/thresholds.toml's [azure] (ticket 118;
  src/strata/agent/retries.py).

The REST shapes follow the Foundry agents API as documented for the api_version in config/agents.toml.
They have not been called from this repo yet; the workspace steps in docs/workspace-catchup.md do that.
"""

from __future__ import annotations

import copy
import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Protocol

from strata.agent import traces
from strata.agent.loop import AgentError
from strata.agent.retries import Retries, Waits
from strata.config import AgentSpec

WHO = "The agent on Foundry"  # who the log names when the agent's call waits
ARM = "https://management.azure.com"
FOUNDRY_SCOPE = "https://ai.azure.com/.default"
ARM_SCOPE = "https://management.azure.com/.default"

Token = Callable[[], str]
Call = Callable[[str, str, dict, dict | None], dict]  # (method, url, headers, body) -> the parsed JSON answer


class FoundryError(RuntimeError):
    """Foundry or Azure answered with an error, or could not be reached. A refusal keeps the answer's headers, so a
    busy one can be tried again after the wait it names (src/strata/agent/retries.py)."""

    def __init__(self, status: int | None, detail: str, headers: dict | None = None):
        super().__init__(f"Foundry answered {status}: {detail}" if status else detail)
        self.status, self.detail, self.headers = status, detail, dict(headers or {})


def http_call(method: str, url: str, headers: dict, body: dict | None, timeout: int = 120) -> dict:
    request = urllib.request.Request(url, method=method, headers={**headers, "Content-Type": "application/json"},
                                     data=None if body is None else json.dumps(body).encode("utf-8"))
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as refused:
        raise FoundryError(refused.code, refused.read().decode(errors="replace")[:2000],
                           dict(refused.headers.items()) if refused.headers else None) from refused
    except (OSError, ValueError) as unreachable:
        raise FoundryError(None, f"I could not reach {urllib.parse.urlsplit(url).netloc}: {unreachable}") \
            from unreachable


def entra_token(tenant: str, client_id: str, secret: str, scope: str) -> Token:
    """A service principal's token from Microsoft Entra ID (client credentials), kept until five minutes
    before it expires. The app uses it to reach the Foundry agent."""
    lock, held = threading.Lock(), {"token": None, "until": 0.0}

    def token() -> str:
        with lock:
            if held["token"] is None or time.monotonic() >= held["until"]:
                form = urllib.parse.urlencode({"grant_type": "client_credentials", "client_id": client_id,
                                               "client_secret": secret, "scope": scope}).encode()
                request = urllib.request.Request(f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
                                                 data=form, method="POST",
                                                 headers={"Content-Type": "application/x-www-form-urlencoded"})
                try:
                    with urllib.request.urlopen(request, timeout=30) as response:
                        reply = json.loads(response.read())
                except (OSError, ValueError) as error:
                    raise FoundryError(None, f"Microsoft Entra ID gave no token: {error}") from error
                held["token"] = reply["access_token"]
                held["until"] = time.monotonic() + max(0, int(reply.get("expires_in", 3600)) - 300)
            return held["token"]
    return token


class Foundry(Protocol):
    def agent(self, name: str) -> dict | None:
        """The agent's latest version, with its definition and description, or None."""

    def create_version(self, name: str, body: dict) -> dict:
        """Make a new version of the agent from a definition and a description. Returns the version."""

    def guardrail(self, name: str) -> dict | None:
        """The RAI policy with this name, or None."""

    def put_guardrail(self, name: str, body: dict) -> dict:
        """Create or replace the RAI policy with this name."""

    def guardrail_id(self, name: str) -> str:
        """The id an agent's rai_config names the policy by."""


# ── Offline ──────────────────────────────────────────────────────────────

class LocalFoundry:
    """A Foundry project kept in memory. Each version gets fields of Foundry's own, which the sync ignores."""

    def __init__(self):
        self.versions: dict[str, list[dict]] = {}
        self.policies: dict[str, dict] = {}

    def agent(self, name):
        versions = self.versions.get(name)
        return copy.deepcopy(versions[-1]) if versions else None

    def create_version(self, name, body):
        versions = self.versions.setdefault(name, [])
        number = str(len(versions) + 1)
        definition = copy.deepcopy(body["definition"])
        for tool in definition.get("tools", []):
            tool.setdefault("strict", None)  # a field Foundry adds that the repo never sets
        versions.append({"object": "agent.version", "id": f"{name}:{number}", "name": name, "version": number,
                         "description": body.get("description"), "definition": definition, "metadata": {}})
        return copy.deepcopy(versions[-1])

    def guardrail(self, name):
        return copy.deepcopy(self.policies.get(name))

    def put_guardrail(self, name, body):
        self.policies[name] = {"id": self.guardrail_id(name), "name": name, **copy.deepcopy(body)}
        return copy.deepcopy(self.policies[name])

    def guardrail_id(self, name):
        return f"/local/raiPolicies/{name}"


# ── Live ─────────────────────────────────────────────────────────────────

def account_id(subscription: str, resource_group: str, account: str) -> str:
    """The Foundry resource's Azure resource id."""
    return (f"/subscriptions/{subscription}/resourceGroups/{resource_group}/providers/"
            f"Microsoft.CognitiveServices/accounts/{account}")


class FoundryProject:
    """The Foundry project's agents, and the Foundry resource's RAI policies."""

    def __init__(self, endpoint: str, spec: AgentSpec, token: Token, arm_token: Token, account: str,
                 call: Call = http_call):
        self.endpoint, self.spec, self.token, self.arm_token = endpoint.rstrip("/"), spec, token, arm_token
        self.account, self.call = account, call

    def _foundry(self, method: str, path: str, body: dict | None = None) -> dict:
        url = f"{self.endpoint}{path}?api-version={self.spec.api_version}"
        return self.call(method, url, {"Authorization": f"Bearer {self.token()}"}, body)

    def _arm(self, method: str, name: str, body: dict | None = None) -> dict:
        url = f"{ARM}{self.guardrail_id(name)}?api-version={self.spec.rai_policy_api_version}"
        return self.call(method, url, {"Authorization": f"Bearer {self.arm_token()}"}, body)

    def agent(self, name):
        try:
            found = self._foundry("GET", f"/agents/{urllib.parse.quote(name)}")
        except FoundryError as error:
            if error.status == 404:
                return None
            raise
        return (found.get("versions") or {}).get("latest")

    def create_version(self, name, body):
        return self._foundry("POST", f"/agents/{urllib.parse.quote(name)}/versions", body)

    def guardrail(self, name):
        try:
            return self._arm("GET", name)
        except FoundryError as error:
            if error.status == 404:
                return None
            raise

    def put_guardrail(self, name, body):
        return self._arm("PUT", name, body)

    def guardrail_id(self, name):
        return f"{self.account}/raiPolicies/{urllib.parse.quote(name)}"


def _filtered(detail: str) -> bool:
    lowered = detail.lower()
    return "content_filter" in lowered or "content management policy" in lowered or "jailbreak" in lowered


class FoundryAgent:
    """One Foundry agent through the Responses API: the answer loop's live Agent. Make one for each answer or each
    item: its calls share one budget of waits. A call Foundry refuses with 429 or 503 is tried again after the wait
    it names, up to config/thresholds.toml's [azure] (src/strata/agent/retries.py), and the last refusal becomes
    agent_unavailable. The app makes one for each answer (src/strata/agent/runner.py), and the nightly's lesson
    review writer one for each item."""

    def __init__(self, endpoint: str, spec: AgentSpec, token: Token, call: Call = http_call,
                 traceparent: Callable[[], str | None] = traces.traceparent, retries: Retries | None = None,
                 sleep: Callable[[float], None] | None = None):
        self.url = f"{endpoint.rstrip('/')}/openai/responses?api-version={spec.api_version}"
        self.name, self.version = spec.name, None
        self.token, self.call, self.traceparent = token, call, traceparent
        self.waits = Waits(WHO, retries, sleep)

    def _post(self, body: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.token()}"}
        if parent := self.traceparent():
            headers["traceparent"] = parent
        return self.call("POST", self.url, headers, body)

    def respond(self, items: list[dict], previous_response_id: str | None) -> dict:
        body = {"agent": {"type": "agent_reference", "name": self.name}, "input": items}
        if previous_response_id:
            body["previous_response_id"] = previous_response_id
        try:
            reply = self.waits.call(lambda: self._post(body), FoundryError)
        except FoundryError as error:  # the token, the network or Foundry's own answer, after any retries
            raise AgentError("content_filter" if error.status == 400 and _filtered(error.detail)
                             else "agent_unavailable", str(error)) from error
        if (reply.get("incomplete_details") or {}).get("reason") == "content_filter":
            raise AgentError("content_filter", "A content filter stopped the agent's answer.")
        if reply.get("error") or reply.get("status") == "failed":
            raise AgentError("agent_unavailable", json.dumps(reply.get("error"))[:500])
        self.version = (reply.get("agent") or {}).get("version") or self.version
        return reply
