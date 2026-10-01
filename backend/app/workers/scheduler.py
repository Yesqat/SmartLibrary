"""Beat liveness reports completed scheduler ticks, not just a running PID."""

import time
from pathlib import Path
from typing import Any

from celery.beat import PersistentScheduler

HEARTBEAT = Path("var/beat/heartbeat")


class HealthyScheduler(PersistentScheduler):  # type: ignore[misc]
    def tick(self, *args: Any, **kwargs: Any) -> float:
        delay = float(super().tick(*args, **kwargs))
        HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
        HEARTBEAT.write_text(str(time.time()), encoding="ascii")
        return min(delay, 30.0)


if __name__ == "__main__":
    try:
        age = time.time() - float(HEARTBEAT.read_text(encoding="ascii"))
        raise SystemExit(0 if 0 <= age <= 120 else 1)
    except (OSError, ValueError):
        raise SystemExit(1) from None
