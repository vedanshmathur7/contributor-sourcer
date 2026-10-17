"""In-process pub/sub that fans agent events out to SSE subscribers."""

import asyncio
from collections import defaultdict

_subscribers: dict[str, set[asyncio.Queue]] = defaultdict(set)


def subscribe(run_id: str) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=2000)
    _subscribers[run_id].add(q)
    return q


def unsubscribe(run_id: str, q: asyncio.Queue) -> None:
    _subscribers[run_id].discard(q)
    if not _subscribers[run_id]:
        _subscribers.pop(run_id, None)


def publish(run_id: str, event: dict) -> None:
    for q in list(_subscribers.get(run_id, ())):
        try:
            q.put_nowait(event)
        except asyncio.QueueFull:
            pass
