"""In-process pub/sub event bus for job status updates.

Replaces polling with push-based SSE notifications.
Each connected user gets an asyncio.Queue that receives
JobEvent objects whenever their jobs change state.

Zero external dependencies — uses only asyncio primitives.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class JobEvent:
    """A single job status change event."""

    job_id: str
    owner_id: str
    event_type: str  # "progress" | "completed" | "failed" | "queued"
    data: dict[str, Any] = field(default_factory=dict)

    def to_sse(self) -> str:
        """Format as an SSE frame (event + data lines)."""
        payload = {"job_id": self.job_id, **self.data}
        return f"event: {self.event_type}\ndata: {json.dumps(payload)}\n\n"


class EventBus:
    """Simple in-process pub/sub using asyncio.Queue per subscriber.

    Thread-safe for asyncio — each user_id maps to a set of queues
    (one per active SSE connection, supporting multiple tabs).
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[JobEvent]]] = {}

    def subscribe(self, user_id: str) -> asyncio.Queue[JobEvent]:
        """Subscribe a user to job events. Returns a personal queue.

        Multiple calls with the same user_id create separate queues
        (one per browser tab / SSE connection).
        """
        queue: asyncio.Queue[JobEvent] = asyncio.Queue(maxsize=256)
        if user_id not in self._subscribers:
            self._subscribers[user_id] = set()
        self._subscribers[user_id].add(queue)
        logger.debug(
            f"EventBus: user {user_id} subscribed "
            f"(total connections: {len(self._subscribers[user_id])})"
        )
        return queue

    def unsubscribe(self, user_id: str, queue: asyncio.Queue[JobEvent]) -> None:
        """Remove a specific queue for a user."""
        queues = self._subscribers.get(user_id)
        if queues:
            queues.discard(queue)
            if not queues:
                del self._subscribers[user_id]
        logger.debug(f"EventBus: user {user_id} unsubscribed")

    async def publish(self, event: JobEvent) -> None:
        """Publish event to ALL queues for the relevant user.

        Non-blocking: if a queue is full, the oldest event is dropped.
        """
        queues = self._subscribers.get(event.owner_id)
        if not queues:
            return

        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(
                    f"EventBus: queue full for user {event.owner_id}, "
                    f"dropping oldest event"
                )
                try:
                    queue.get_nowait()  # Drop oldest
                    queue.put_nowait(event)
                except asyncio.QueueEmpty:
                    pass

    @property
    def connected_users(self) -> int:
        """Number of users with active SSE connections."""
        return len(self._subscribers)

    @property
    def total_connections(self) -> int:
        """Total number of active SSE connections across all users."""
        return sum(len(qs) for qs in self._subscribers.values())


# Global singleton — imported by worker.py and routes/jobs.py
event_bus = EventBus()
