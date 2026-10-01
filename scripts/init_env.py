"""Create local development configuration without printing or overwriting secrets."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
source = (root / ".env.example").read_text(encoding="utf-8")
for key in (
    "POSTGRES_PASSWORD",
    "REDIS_PASSWORD",
    "JWT_SECRET",
    "APP_DB_PASSWORD",
    "MIGRATION_DB_PASSWORD",
    "DEV_SEED_PASSWORD",
):
    source = source.replace(f"{key}=\n", f"{key}={secrets.token_hex(32)}\n")
source = source.replace("QR_ENCRYPTION_KEY=\n", f"QR_ENCRYPTION_KEY={secrets.token_urlsafe(32)}\n")
try:
    with (root / ".env").open("x", encoding="utf-8", newline="\n") as target:
        target.write(source)
except FileExistsError:
    raise SystemExit("Existing .env preserved. Edit it explicitly if needed.") from None
print("Created .env with random development secrets. No secrets were printed.")
