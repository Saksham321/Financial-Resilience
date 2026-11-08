"""Bounded, process-local operational counters; no user IDs or raw URLs."""
from collections import Counter
from threading import Lock
from time import monotonic


class SystemMetrics:
    def __init__(self):
        self.started = monotonic()
        self.lock = Lock()
        self.requests = Counter()
        self.duration_seconds = 0.0

    def observe(self, method, route, status, duration):
        with self.lock:
            self.requests[(method, route, status)] += 1
            self.duration_seconds += duration

    def snapshot(self):
        with self.lock:
            return {
                "scope": "current_process_since_start",
                "uptime_seconds": round(monotonic() - self.started, 3),
                "requests_total": sum(self.requests.values()),
                "request_duration_seconds_total": round(self.duration_seconds, 6),
                "requests": [
                    {"method": method, "route": route, "status": status, "count": count}
                    for (method, route, status), count in sorted(self.requests.items())
                ],
            }


system_metrics = SystemMetrics()
