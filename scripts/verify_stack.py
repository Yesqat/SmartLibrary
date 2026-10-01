"""Verify eight services; --test-outages briefly stops and restores each dependency."""

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SERVICES = (
    "frontend",
    "backend",
    "postgres",
    "redis",
    "worker",
    "ml-worker",
    "beat",
    "nginx",
)


def run(*args: str) -> str:
    result = subprocess.run(
        args, cwd=ROOT, capture_output=True, text=True, timeout=180, check=False
    )
    if result.returncode:
        # Do not echo Docker inspection/configuration payloads containing credentials.
        raise RuntimeError(f"Command failed ({result.returncode}): {' '.join(args[:4])}")
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", action="store_true")
    parser.add_argument("--test-outages", action="store_true")
    args = parser.parse_args()
    compose = ["docker", "compose", "-f", "docker-compose.yml"]
    if args.dev:
        compose += ["-f", "docker-compose.dev.yml"]
    config = json.loads(run(*compose, "config", "--format", "json"))
    port = config["services"]["nginx"]["ports"][0]["published"]
    base = f"http://127.0.0.1:{port}"
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def request(path: str) -> tuple[int, bytes, object]:
        try:
            response = opener.open(base + path, timeout=15)
        except urllib.error.HTTPError as exc:
            response = exc
        with response:
            return response.status, response.read(), response.headers

    def expect_json(path: str, status: int, expected: dict) -> None:
        actual_status, body, _ = request(path)
        assert actual_status == status, f"{path}: expected {status}, got {actual_status}"
        assert json.loads(body) == expected, f"{path}: unexpected response"

    def ready(dependency: str | None = None) -> None:
        expected = {
            "status": "unavailable" if dependency else "ready",
            "dependencies": {
                name: "unavailable" if name == dependency else "ok"
                for name in ("postgres", "redis")
            },
        }
        deadline = time.monotonic() + 90
        while True:
            try:
                expect_json("/api/v1/ready", 503 if dependency else 200, expected)
                return
            except (AssertionError, OSError):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(2)

    def live() -> None:
        expect_json("/api/v1/health", 200, {"status": "ok"})
        expect_json("/health", 200, {"status": "ok"})
        status, body, headers = request("/")
        assert status == 200 and 'lang="kk"' in body.decode(), "Frontend unavailable"
        assert headers["X-Content-Type-Options"] == "nosniff"

    def containers() -> None:
        for service in SERVICES:
            container_id = run(*compose, "ps", "-q", service)
            assert container_id, f"Missing {service} container"
            state = json.loads(run("docker", "inspect", container_id))[0]
            assert state["State"]["Status"] == "running", f"{service} not running"
            assert state["State"]["Health"]["Status"] == "healthy", f"{service} not healthy"
            if service != "nginx":
                assert not state["HostConfig"]["PortBindings"], f"{service} has published ports"
            else:
                bindings = state["HostConfig"]["PortBindings"]
                assert all(b["HostIp"] == "127.0.0.1" for v in bindings.values() for b in v)
            if service in {"postgres", "redis"}:
                networks = state["NetworkSettings"]["Networks"]
                assert len(networks) == 1, f"{service} connected to extra networks"
                network = json.loads(run("docker", "network", "inspect", next(iter(networks))))[0]
                assert network["Internal"], f"{service} network is not internal"
            print(f"PASS {service}: healthy; network/port policy verified", flush=True)
        for service in ("frontend", "backend", "worker", "ml-worker", "beat"):
            assert run(*compose, "exec", "-T", service, "id", "-u") != "0"
        print("PASS application processes run as non-root", flush=True)

    containers()
    live()
    ready()
    status, body, _ = request("/docs")
    assert status == 200 and b"swagger-ui" in body
    status, body, _ = request("/openapi.json")
    assert status == 200
    assert json.loads(body) == json.loads((ROOT / "docs/openapi.json").read_text("utf-8"))
    run(*compose, "exec", "-T", "nginx", "nginx", "-t")
    run(*compose, "exec", "-T", "worker", "python", "-m", "app.workers.healthcheck")
    run(*compose, "exec", "-T", "ml-worker", "python", "-m", "app.workers.healthcheck")
    run(*compose, "exec", "-T", "beat", "python", "-m", "app.workers.scheduler")
    print(
        "PASS frontend, liveness, readiness, Swagger, OpenAPI, Nginx and Celery ping",
        flush=True,
    )
    database_check = (
        "from app.core.config import get_settings; "
        "from app.db.session import create_db_engine; from sqlalchemy import text; "
        "engine=create_db_engine(get_settings()); "
        "connection=engine.connect(); "
        'names=set(connection.scalars(text("SELECT name FROM pg_available_extensions '
        "WHERE name IN ('vector', 'pg_trgm')\"))); "
        "assert names == {'vector', 'pg_trgm'}; "
        "connection.close(); engine.dispose(); print('PASS vector and pg_trgm are available')"
    )
    print(
        run(*compose, "exec", "-T", "backend", "python", "-c", database_check),
        flush=True,
    )
    if args.test_outages:
        for dependency in ("postgres", "redis"):
            try:
                run(*compose, "stop", "--timeout", "10", dependency)
                ready(dependency)
                live()
                print(
                    f"PASS {dependency} outage: readiness 503; liveness and UI 200",
                    flush=True,
                )
            finally:
                run(*compose, "start", dependency)
                run(*compose, "up", "-d", "--wait", "--wait-timeout", "120")
            ready()
            print(f"PASS {dependency} recovery: readiness 200", flush=True)
        containers()
    print("Current stack verification passed", flush=True)


if __name__ == "__main__":
    main()
