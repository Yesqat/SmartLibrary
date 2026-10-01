"""Create independent local test credentials without overwriting an existing E2E setup."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    replacements = {
        "APP_ENV": "test",
        "HTTP_PORT": "8081",
        "FRONTEND_URL": "http://localhost:8081",
        "CORS_ORIGINS": '["http://localhost:8081"]',
        "QR_ENCRYPTION_KEY": secrets.token_urlsafe(32),
    }
    for name in (
        "POSTGRES_PASSWORD",
        "REDIS_PASSWORD",
        "JWT_SECRET",
        "APP_DB_PASSWORD",
        "MIGRATION_DB_PASSWORD",
        "DEV_SEED_PASSWORD",
    ):
        replacements[name] = secrets.token_hex(32)
    lines = []
    for line in (ROOT / ".env.example").read_text("utf-8").splitlines():
        key = line.split("=", 1)[0]
        lines.append(f"{key}={replacements[key]}" if key in replacements else line)
    target = ROOT / "work/e2e.env"
    target.parent.mkdir(exist_ok=True)
    try:
        with target.open("x", encoding="utf-8", newline="\n") as output:
            output.write("\n".join(lines) + "\n")
    except FileExistsError:
        raise SystemExit("Existing work/e2e.env preserved; credentials were not changed.") from None
    print("Created private work/e2e.env for smartlibrary-e2e on localhost:8081.")


if __name__ == "__main__":
    main()
