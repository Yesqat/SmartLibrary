"""Actual Redis broker, separate Celery processes, restart and durable DB deduplication."""

import os
import subprocess
import sys
import time
from contextlib import contextmanager
from uuid import uuid4

import pytest
from celery import Celery

from app.tests.database.domain.test_scheduled import count, loan

pytestmark = pytest.mark.integration


def test_real_worker_delivery_and_restart(client, actor, domain_db, tmp_path):
    row, _ = loan(client, actor, domain_db, -1)
    settings = client.app.state.settings
    queue = "test-circulation-" + uuid4().hex
    hostname = queue + "@isolated"
    producer = Celery("verification", broker=settings.redis_dsn, backend=settings.redis_dsn)
    environment = {
        **os.environ,
        "DATABASE_URL": settings.database_dsn,
        "QR_ENCRYPTION_KEY": settings.qr_encryption_key.get_secret_value(),
        "CELERY_RESULT_BACKEND": settings.redis_dsn,
        "EMBEDDING_MODEL": "",
        "APP_ENV": "test",
    }

    @contextmanager
    def worker():
        with (tmp_path / "worker.txt").open("ab") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "celery",
                    "-A",
                    "app.workers.celery_app:celery_app",
                    "worker",
                    "--pool=solo",
                    "--concurrency=1",
                    "--loglevel=WARNING",
                    "--without-gossip",
                    "--without-mingle",
                    "--without-heartbeat",
                    "--hostname=" + hostname,
                    "-Q",
                    queue,
                ],
                env=environment,
                stdout=log,
                stderr=log,
            )
            try:
                deadline = time.monotonic() + 30
                while time.monotonic() < deadline:
                    assert process.poll() is None, "Isolated Celery process stopped during startup"
                    if producer.control.ping(destination=[hostname], timeout=1):
                        break
                else:
                    pytest.fail("Isolated Celery process did not answer ping")
                yield
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

    try:
        for _ in range(2):
            with worker():
                result = producer.send_task(
                    "smartlibrary.circulation.sweep", queue=queue, ignore_result=False
                )
                try:
                    assert result.get(timeout=40)["failed"] == 0
                finally:
                    result.forget()
            assert count(domain_db, "OVERDUE", row["id"]) == 1
    finally:
        # Only keys belonging to this randomly named test queue; never flush shared Redis.
        keys = list(client.app.state.redis.scan_iter(match="*" + queue + "*"))
        if keys:
            client.app.state.redis.delete(*keys)
        producer.close()
