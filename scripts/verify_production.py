"""Verify the isolated localhost production-mode deployment with actual TLS validation."""

import json
import ssl
import subprocess
from pathlib import Path
from uuid import UUID

import httpx

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = [
    "docker",
    "compose",
    "-p",
    "smartlibrary-production-check",
    "--env-file",
    ".env.production",
    "-f",
    "docker-compose.yml",
    "-f",
    "docker-compose.production.yml",
]


def run(args: list[str]) -> str:
    result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError("Production verification command failed; sensitive output withheld")
    return result.stdout


def main() -> None:
    run([*COMPOSE, "config", "--quiet"])
    for service in (
        "frontend",
        "backend",
        "worker",
        "ml-worker",
        "beat",
        "postgres",
        "redis",
        "nginx",
    ):
        cid = run([*COMPOSE, "ps", "-q", service]).strip()
        state = json.loads(run(["docker", "inspect", cid]))[0]
        assert state["State"]["Health"]["Status"] == "healthy", service
        bindings = state["HostConfig"]["PortBindings"]
        if service != "nginx":
            assert not bindings, service
        else:
            assert all(row["HostIp"] == "127.0.0.1" for rows in bindings.values() for row in rows)
        if service in {"postgres", "redis"}:
            networks = state["NetworkSettings"]["Networks"]
            assert len(networks) == 1
            assert json.loads(run(["docker", "network", "inspect", next(iter(networks))]))[0][
                "Internal"
            ]
        if service in {"frontend", "backend", "worker", "ml-worker", "beat"}:
            assert run([*COMPOSE, "exec", "-T", service, "id", "-u"]).strip() != "0"
        print(f"PASS {service}: healthy, private network/port and process checks")
    tls = ssl.create_default_context(cafile=str(ROOT / "var/tls-verification/ca.pem"))
    with httpx.Client(verify=tls, trust_env=False, timeout=30) as client:
        response = client.get("http://localhost:8082/catalog?language=kk")
        assert response.status_code == 308
        assert response.headers["location"] == "https://localhost:8443/catalog?language=kk"
        origin = "https://localhost:8443"
        for path in ("/", "/health", "/api/v1/health", "/api/v1/ready", "/nginx-health"):
            response = client.get(origin + path)
            assert response.status_code == 200, path
            assert response.headers["strict-transport-security"] == "max-age=31536000"
        page = client.get(origin + "/login")
        csp = page.headers["content-security-policy"]
        assert "'nonce-" in csp and "'unsafe-eval'" not in csp
        assert "no-store" in page.headers["cache-control"]
        for path in ("/docs", "/openapi.json"):
            assert client.get(origin + path).status_code == 404
        assert client.get(origin + "/api/v1/users/me").status_code == 401
        assert client.get(origin + "/", headers={"Host": "attacker.example"}).status_code == 421
        csrf = client.get(
            origin + "/api/v1/auth/csrf", headers={"Origin": "https://attacker.example"}
        )
        assert csrf.status_code == 403 and "access-control-allow-origin" not in csrf.headers
        cookies = client.get(origin + "/api/v1/auth/csrf").headers.get_list("set-cookie")
        assert any(
            "__Host-sl_csrf=" in value and "Secure" in value and "HttpOnly" in value
            for value in cookies
        )
        csrf_token = client.get(origin + "/api/v1/auth/csrf").json()["csrf_token"]
        failed = client.post(
            origin + "/api/v1/auth/login",
            json={
                "email": "absent-proxy-check@example.com",
                "password": "Not a valid account 917!",
            },
            headers={
                "Origin": origin,
                "X-CSRF-Token": csrf_token,
                "X-Real-IP": "198.51.100.21",
                "X-Forwarded-For": "198.51.100.21",
                "Forwarded": "for=198.51.100.21;proto=http",
            },
        )
        assert failed.status_code == 401
        request_id = str(UUID(failed.headers["x-request-id"]))
        check_ip = f"""
from sqlalchemy import text
from app.core.config import Settings
from app.db.session import create_db_engine
db=create_db_engine(Settings())
with db.connect() as c:
    query=text("SELECT ip_address FROM audit_logs WHERE request_id=:id")
    ip=c.scalar(query, {{'id':'{request_id}'}})
    assert ip and str(ip) != '198.51.100.21'
db.dispose()
"""
        run([*COMPOSE, "exec", "-T", "backend", "python", "-c", check_ip])
        print("PASS Nginx discards spoofed client-address forwarding headers")
        oversized = client.post(origin + "/api/v1/books", content=b"x" * (11 * 1024 * 1024))
        assert oversized.status_code == 413
        assert oversized.json()["error"]["code"] == "UPLOAD_TOO_LARGE"
    run([*COMPOSE, "exec", "-T", "nginx", "nginx", "-t"])
    run([*COMPOSE, "run", "--rm", "database", "python", "-m", "app.db.manage", "check"])
    print("PASS TLS chain/host, redirects, HSTS/CSP, CORS, Secure CSRF, limits, routing and schema")


if __name__ == "__main__":
    main()
