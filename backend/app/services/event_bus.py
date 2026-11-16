import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from ..models.event import AgentEvent
from ..database import AsyncSessionLocal

logger = logging.getLogger("agent.event_bus")


class EventBus:
    def __init__(self):
        # run_id -> list of subscriber queues
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue = asyncio.Queue()
        if run_id not in self._subscribers:
            self._subscribers[run_id] = []
        self._subscribers[run_id].append(queue)
        logger.debug(f"Subscriber added for run {run_id}. Total: {len(self._subscribers[run_id])}")
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue):
        if run_id in self._subscribers:
            if queue in self._subscribers[run_id]:
                self._subscribers[run_id].remove(queue)
            if not self._subscribers[run_id]:
                del self._subscribers[run_id]

    async def emit(
        self,
        run_id: str,
        event_type: str,
        payload: Dict[str, Any],
        step_number: Optional[int] = None,
        persist: bool = True,
    ):
        event_data = {
            "run_id": run_id,
            "event_type": event_type,
            "step_number": step_number,
            "payload": payload,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # 1. Distribute in-memory to SSE subscribers
        if run_id in self._subscribers:
            for queue in list(self._subscribers[run_id]):
                try:
                    queue.put_nowait(event_data)
                except Exception as e:
                    logger.warning(f"Failed to push event to queue: {e}")

        # 2. Persist to database asynchronously
        if persist:
            try:
                async with AsyncSessionLocal() as session:
                    db_event = AgentEvent(
                        run_id=run_id,
                        event_type=event_type,
                        step_number=step_number,
                        payload=payload,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(db_event)
                    await session.commit()
            except Exception as e:
                logger.error(f"Failed to persist event {event_type} for run {run_id}: {e}")


event_bus = EventBus()
