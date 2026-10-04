import logging
import os
import signal
import socket
import threading
from types import FrameType

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.jobs.registry import JobRegistry, get_job_registry, recover_stale_jobs
from app.jobs.worker_state import record_worker_heartbeat


logger = logging.getLogger(__name__)


class JobWorker:
    def __init__(
        self,
        registry: JobRegistry | None = None,
        poll_interval_seconds: float | None = None,
        heartbeat_interval_seconds: float | None = None,
    ):
        self.registry = registry or get_job_registry()
        self.poll_interval_seconds = (
            poll_interval_seconds or settings.JOB_POLL_INTERVAL_SECONDS
        )
        self.heartbeat_interval_seconds = (
            heartbeat_interval_seconds or settings.WORKER_HEARTBEAT_INTERVAL_SECONDS
        )
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}"
        self._stop_event = threading.Event()
        self._heartbeat_stop = threading.Event()

    def request_shutdown(
        self,
        signum: int | None = None,
        frame: FrameType | None = None,
    ) -> None:
        logger.info("Worker shutdown requested: signal=%s", signum)
        _ = frame
        self._stop_event.set()

    def run_once(self) -> bool:
        job_id = self.registry.claim_next_job()
        if job_id is None:
            return False
        self.registry.execute_claimed_job(job_id)
        return True

    def _heartbeat_loop(self) -> None:
        while not self._heartbeat_stop.wait(self.heartbeat_interval_seconds):
            try:
                record_worker_heartbeat(self.worker_id)
            except SQLAlchemyError:
                logger.exception("Could not update worker heartbeat: worker_id=%s", self.worker_id)

    def run(self) -> None:
        previous_handlers = {}
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                previous_handlers[sig] = signal.signal(sig, self.request_shutdown)

        heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            name="job-worker-heartbeat",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            while not self._stop_event.is_set():
                try:
                    record_worker_heartbeat(self.worker_id)
                    recovered = recover_stale_jobs(settings.JOB_RUNNING_TIMEOUT_MINUTES)
                    if recovered:
                        logger.info("Recovered stale jobs on worker startup: count=%s", recovered)
                    break
                except SQLAlchemyError:
                    logger.exception("Worker startup is waiting for the database schema")
                    self._stop_event.wait(self.poll_interval_seconds)

            while not self._stop_event.is_set():
                try:
                    if not self.run_once():
                        self._stop_event.wait(self.poll_interval_seconds)
                except SQLAlchemyError:
                    logger.exception("Worker could not poll or execute a queued job")
                    self._stop_event.wait(self.poll_interval_seconds)
        finally:
            self._heartbeat_stop.set()
            heartbeat_thread.join()
            for sig, handler in previous_handlers.items():
                signal.signal(sig, handler)


def main() -> None:
    logging.basicConfig(level=settings.LOG_LEVEL)
    JobWorker().run()


if __name__ == "__main__":
    main()
