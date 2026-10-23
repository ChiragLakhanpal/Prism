"""Async helpers for the harness.

with_heartbeats passes on what a source yields and adds a HEARTBEAT whenever the source
has been quiet for a while, so a proxy does not close a stream while the agent thinks.
It reads the source in its own task, so a pause never cancels the source part way.
"""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from typing import TypeVar

T = TypeVar("T")
HEARTBEAT = object()
_END = object()


async def with_heartbeats(source: AsyncIterator[T], every: float) -> AsyncIterator[T | object]:
    queue: asyncio.Queue = asyncio.Queue()

    async def pump() -> None:
        try:
            async for item in source:
                await queue.put((item, None))
            await queue.put((_END, None))
        except Exception as error:  # passed on to the reader, which raises it
            await queue.put((_END, error))

    task = asyncio.create_task(pump())
    try:
        while True:
            try:
                item, error = await asyncio.wait_for(queue.get(), every)
            except TimeoutError:
                yield HEARTBEAT
                continue
            if error is not None:
                raise error
            if item is _END:
                return
            yield item
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
