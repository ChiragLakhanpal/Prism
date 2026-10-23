"""One JSON POST to a live service, for the adapters that call Azure (embed.py and shields.py).

A refusal or an unreachable service raises the adapter's own error with the service's name, so the
passage run stops and says which service failed, rather than keep passages with no vector or no
Prompt Shields result.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request


def post_json(url: str, headers: dict, body: dict, *, timeout: int, error: type[Exception], service: str) -> dict:
    """The parsed JSON answer to a POST of body to url."""
    request = urllib.request.Request(url, method="POST", data=json.dumps(body).encode("utf-8"),
                                     headers={**headers, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as refused:
        raise error(f"{service} answered {refused.code}: {refused.read().decode(errors='replace')[:300]}") from refused
    except urllib.error.URLError as unreachable:
        raise error(f"I could not reach {service}: {unreachable.reason}") from unreachable
