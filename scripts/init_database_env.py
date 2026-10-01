"""Add PHASE 2 operator/runtime credentials to an existing local .env without replacing values."""

import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / ".env"
source = path.read_text(encoding="utf-8")
values = dict(
    line.split("=", 1)
    for line in source.splitlines()
    if "=" in line and not line.lstrip().startswith("#")
)
additions = {
    "APP_DB_USER": "smartlibrary_app",
    "APP_DB_PASSWORD": secrets.token_hex(32),
    "MIGRATION_DB_USER": "smartlibrary_migrator",
    "MIGRATION_DB_PASSWORD": secrets.token_hex(32),
    "DEV_SEED_PASSWORD": secrets.token_urlsafe(24),
}
for key, value in additions.items():
    if key not in values:
        source = source.rstrip("\n") + f"\n{key}={value}\n"
    elif not values[key]:
        source = source.replace(f"{key}=\n", f"{key}={value}\n")
path.write_text(source, encoding="utf-8", newline="\n")
print(
    "PHASE 2 local credential fields prepared. "
    "Existing nonempty values preserved; no secrets printed."
)
