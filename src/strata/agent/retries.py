"""Trying a model call again when Azure is busy (ticket 118), for the agent (src/strata/agent/foundry.py) and the
verifier's judge (src/strata/agent/judge.py).

The agent and the judge share one gpt-5.4 deployment with a cap on tokens per minute, so a long answer and its judging
can cross the cap inside one minute. Azure then answers 429, too many requests, and names the seconds to wait in its
Retry-After header (Azure OpenAI also sends retry-after-ms); when it is briefly overloaded it answers 503. A call that
gets either waits that long and tries again, up to config/thresholds.toml's [azure], and then lets the refusal go up
as it came, so each adapter gives up as it did before: the judge with judge_unavailable, the agent with
agent_unavailable. Any other refusal, such as a 403, goes up at once. Each wait is logged with its try count.

The pattern is ticket 107's for the cost pull (src/strata/lakehouse/costs.py). An adapter's error names the answer's
HTTP status and headers as `status` and `headers`, which is all Waits reads of it. sleep stands in for the waits in
the tests.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TypeVar

from strata.config import ConfigError, Thresholds, load_thresholds

log = logging.getLogger("strata.agent")
T = TypeVar("T")

BUSY = frozenset({429, 503})  # too many requests, and service unavailable
# The headers a busy answer names its wait in: seconds, or milliseconds.
RETRY_AFTER, RETRY_AFTER_MS = "retry-after", "retry-after-ms"


def _number(value) -> float | None:
    try:
        number = float(str(value).strip())
    except ValueError:  # Retry-After may also be a date, which is read as no wait named
        return None
    return number if math.isfinite(number) else None


@dataclass(frozen=True)
class Retries:
    """config/thresholds.toml's [azure]: how many times a call tries again after its first try, the wait when Azure
    names none, the longest single wait, and the most one answer waits on one model in all."""

    retries: int
    retry_seconds: float
    max_retry_seconds: float
    max_wait_seconds: float

    @classmethod
    def from_thresholds(cls, thresholds: Thresholds | None = None) -> Retries:
        thresholds = thresholds or load_thresholds()
        found = cls(int(thresholds.value("azure.retries")), *(float(thresholds.value(f"azure.{name}")) for name in (
            "retry_seconds", "max_retry_seconds", "max_wait_seconds")))
        if found.retries < 0 or min(found.retry_seconds, found.max_retry_seconds, found.max_wait_seconds) < 0:
            raise ConfigError(f"In {thresholds.path.name}, [azure] needs retries and waits of 0 or more; it has "
                              f"retries = {found.retries}, retry_seconds = {found.retry_seconds:g}, "
                              f"max_retry_seconds = {found.max_retry_seconds:g} and max_wait_seconds = "
                              f"{found.max_wait_seconds:g}.")
        return found

    def wait(self, headers: Mapping) -> float:
        """The seconds a busy answer asks for: the longest its Retry-After and retry-after-ms headers name, or
        retry_seconds when they name none. Never less than 0 or more than max_retry_seconds."""
        named = []
        for name, value in headers.items():
            number = _number(value)
            if number is not None and str(name).lower() in (RETRY_AFTER, RETRY_AFTER_MS):
                named.append(number / 1000 if str(name).lower() == RETRY_AFTER_MS else number)
        return min(max(max(named, default=self.retry_seconds), 0.0), self.max_retry_seconds)


class Waits:
    """One answer's waits on one model. call() tries a call again while Azure answers it as busy, and every call
    through the same Waits shares max_wait_seconds."""

    def __init__(self, who: str, retries: Retries | None = None, sleep: Callable[[float], None] | None = None):
        self.who, self.retries, self.sleep = who, retries or Retries.from_thresholds(), sleep or time.sleep
        self.waited = 0.0

    def call(self, ask: Callable[[], T], refused: type[Exception]) -> T:
        """ask(), tried again after each busy refusal while retries and the answer's wait are left. Any other error,
        or the last refusal, goes up as it came."""
        retried = 0
        while True:
            try:
                return ask()
            except refused as error:
                status = getattr(error, "status", None)
                if status not in BUSY or retried >= self.retries.retries:
                    raise
                wait = self.retries.wait(getattr(error, "headers", None) or {})
                if self.waited + wait > self.retries.max_wait_seconds:
                    log.warning("%s answered %s and asked for %s more seconds, which would pass the %s seconds one "
                                "answer may wait, so I stopped trying.", self.who, status, f"{wait:g}",
                                f"{self.retries.max_wait_seconds:g}")
                    raise
                retried += 1
                self.waited += wait
                log.warning("%s answered %s, so I am waiting %s seconds before retry %d of %d.", self.who, status,
                            f"{wait:g}", retried, self.retries.retries)
                self.sleep(wait)
