"""Create independent production configuration; never reuse development credentials."""

import argparse
import base64
import ipaddress
import re
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--host", required=True, help="Certificate DNS name, without scheme or port"
    )
    parser.add_argument("--http-port", type=int, default=80)
    parser.add_argument("--https-port", type=int, default=443)
    parser.add_argument(
        "--bind", default="127.0.0.1", help="Explicit ingress IP; loopback by default"
    )
    parser.add_argument("--tls-directory", default="var/tls")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9.-]{0,251}[a-z0-9])?", args.host):
        parser.error("Use an ASCII DNS hostname")
    if any(not 1 <= port <= 65535 for port in (args.http_port, args.https_port)):
        parser.error("Ports must be between 1 and 65535")
    ipaddress.IPv4Address(args.bind)
    tls = (ROOT / args.tls_directory).resolve()
    if not tls.is_relative_to(ROOT):
        parser.error("Keep certificate files inside the project workspace")
    origin = f"https://{args.host}" + (f":{args.https_port}" if args.https_port != 443 else "")
    overrides = {
        "APP_ENV": "production",
        "HTTP_PORT": str(args.http_port),
        "FRONTEND_URL": origin,
        "CORS_ORIGINS": f'["{origin}"]',
        "ALLOWED_HOSTS": f'["{args.host}","backend","localhost","127.0.0.1"]',
        "DEV_SEED_PASSWORD": "",
        "QR_ENCRYPTION_KEY": base64.urlsafe_b64encode(secrets.token_bytes(32)).decode(),
    }
    for name in (
        "POSTGRES_PASSWORD",
        "APP_DB_PASSWORD",
        "MIGRATION_DB_PASSWORD",
        "REDIS_PASSWORD",
        "JWT_SECRET",
    ):
        overrides[name] = secrets.token_hex(32)
    lines = ["# Private production configuration; never commit or print this file."]
    for line in (ROOT / ".env.example").read_text("utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            key, value = line.split("=", 1)
            lines.append(f"{key}={overrides.get(key, value)}")
    lines.extend(
        [
            f"PUBLIC_HOST={args.host}",
            f"PUBLIC_ORIGIN={origin}",
            f"HTTPS_PORT={args.https_port}",
            f"DEPLOY_BIND_ADDRESS={args.bind}",
            f"TLS_DIRECTORY={tls.as_posix()}",
        ]
    )
    with (ROOT / ".env.production").open("x", encoding="utf-8", newline="\n") as output:
        output.write("\n".join(lines) + "\n")
    print(
        "Created .env.production with independent secrets. Install the certificate before startup."
    )


if __name__ == "__main__":
    main()
