"""Verify this container's worker responds through the real broker."""

import socket

from app.workers.celery_app import celery_app


def main() -> None:
    destination = f"celery@{socket.gethostname()}"
    replies = celery_app.control.ping(destination=[destination], timeout=3)
    if not any(reply.get(destination, {}).get("ok") == "pong" for reply in replies):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
