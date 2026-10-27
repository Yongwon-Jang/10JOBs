"""Patrol route for guard mode: visits waypoints in a loop and skips unreachable ones."""
from dataclasses import dataclass, field
import math


@dataclass
class Patrol:
    waypoints: list                      # [(x, y), ...] in map coordinates
    arrive_tolerance: float = 0.2
    max_failures: int = 2                # skip a waypoint after this many failed attempts
    index: int = 0
    failures: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.waypoints:
            raise ValueError('patrol needs at least one waypoint')

    @property
    def current(self):
        return self.waypoints[self.index]

    def arrived(self, x: float, y: float) -> bool:
        cx, cy = self.current
        return math.hypot(cx - x, cy - y) <= self.arrive_tolerance

    def next(self):
        """Advance to the next waypoint that has not failed too often. Returns it, or None if all failed."""
        for _ in range(len(self.waypoints)):
            self.index = (self.index + 1) % len(self.waypoints)
            if self.failures.get(self.index, 0) < self.max_failures:
                return self.current
        return None

    def report_failure(self):
        """Planner could not reach the current waypoint."""
        self.failures[self.index] = self.failures.get(self.index, 0) + 1
        return self.next()

    def report_arrival(self):
        self.failures.pop(self.index, None)
        return self.next()
