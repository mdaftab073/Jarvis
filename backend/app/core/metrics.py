import threading
import time
from typing import Any, Dict


class MetricsCollector:
    """
    Thread-safe in-memory application metrics collector.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.start_time = time.time()
        self.total_requests: int = 0
        self.total_errors: int = 0
        self.total_latency_ms: float = 0.0
        self.min_latency_ms: float = float("inf")
        self.max_latency_ms: float = 0.0
        self.director_agent_calls: int = 0
        self.rag_requests: int = 0
        self.endpoint_counts: Dict[str, int] = {}
        self.status_code_counts: Dict[str, int] = {}
        self.agent_counts: Dict[str, int] = {}

    def record_request(
        self,
        method: str,
        path: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        with self._lock:
            self.total_requests += 1
            self.total_latency_ms += duration_ms
            if duration_ms < self.min_latency_ms:
                self.min_latency_ms = duration_ms
            if duration_ms > self.max_latency_ms:
                self.max_latency_ms = duration_ms

            if status_code >= 400:
                self.total_errors += 1

            # Status codes count
            sc_str = str(status_code)
            self.status_code_counts[sc_str] = (
                self.status_code_counts.get(sc_str, 0) + 1
            )

            # Endpoint count
            endpoint_key = f"{method.upper()} {path}"
            self.endpoint_counts[endpoint_key] = (
                self.endpoint_counts.get(endpoint_key, 0) + 1
            )

            # Special counters
            if "/director/" in path:
                self.director_agent_calls += 1
            elif "/rag/" in path or "/materials/" in path:
                self.rag_requests += 1

    def record_agent_call(self, agent_name: str) -> None:
        with self._lock:
            self.agent_counts[agent_name] = (
                self.agent_counts.get(agent_name, 0) + 1
            )
            if agent_name in ("director", "AcademicDirectorAgent"):
                self.director_agent_calls += 1

    def get_metrics(self) -> Dict[str, Any]:
        with self._lock:
            uptime = time.time() - self.start_time
            avg_latency = (
                round(self.total_latency_ms / self.total_requests, 2)
                if self.total_requests > 0
                else 0.0
            )
            return {
                "total_requests": self.total_requests,
                "total_errors": self.total_errors,
                "average_latency_ms": avg_latency,
                "min_latency_ms": (
                    round(self.min_latency_ms, 2)
                    if self.min_latency_ms != float("inf")
                    else 0.0
                ),
                "max_latency_ms": round(self.max_latency_ms, 2),
                "director_agent_calls": self.director_agent_calls,
                "rag_requests": self.rag_requests,
                "uptime_seconds": round(uptime, 2),
                "status_codes": dict(self.status_code_counts),
                "agent_executions": dict(self.agent_counts),
                "endpoint_counts": dict(self.endpoint_counts),
            }

    def reset(self) -> None:
        with self._lock:
            self.start_time = time.time()
            self.total_requests = 0
            self.total_errors = 0
            self.total_latency_ms = 0.0
            self.min_latency_ms = float("inf")
            self.max_latency_ms = 0.0
            self.director_agent_calls = 0
            self.rag_requests = 0
            self.endpoint_counts.clear()
            self.status_code_counts.clear()
            self.agent_counts.clear()


# Global singleton collector
metrics = MetricsCollector()
