"""Stable event order: numeric priority then insertion sequence on the same day."""

import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass(order=True, frozen=True)
class ScheduledEvent:
    day: int
    priority: int
    sequence: int
    kind: str = field(compare=False)
    data: dict[str, Any] = field(default_factory=dict, compare=False)


class EventScheduler:
    def __init__(self):
        self._queue = []
        self._sequence = 0
        self.current_day = -1

    def schedule(self, day: int, kind: str, *, priority: int = 20, **data) -> None:
        if day < 0 or day < self.current_day:
            raise ValueError("Cannot schedule an event in the simulated past")
        heapq.heappush(self._queue, ScheduledEvent(day, priority, self._sequence, kind, data))
        self._sequence += 1

    def pop_day(self) -> tuple[int, tuple[ScheduledEvent, ...]]:
        if not self._queue:
            raise IndexError("Empty event schedule")
        day = self._queue[0].day
        self.current_day = day
        events = []
        while self._queue and self._queue[0].day == day:
            events.append(heapq.heappop(self._queue))
        return day, tuple(events)

    def __bool__(self):
        return bool(self._queue)
