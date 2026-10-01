"""Export a private PostgreSQL snapshot, uploaded images and learned categorization artifact.

Stop writers first when a single consistent database/image backup is required.
Only an ignored directory inside var/backups is created. Binary streams never pass
through a shell text pipe. Copy/encrypt the result to separately managed storage.
"""

import argparse
import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="smartlibrary")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("-f", "--file", action="append", default=[])
    args = parser.parse_args()
    compose = ["docker", "compose", "-p", args.project, "--env-file", args.env_file]
    for name in ["docker-compose.yml", *args.file]:
        compose += ["-f", name]
    target = (
        ROOT / "var/backups" / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex[:8])
    )
    target.mkdir(parents=True)
    exports = {
        "database.dump": [
            "exec",
            "-T",
            "postgres",
            "sh",
            "-c",
            'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom',
        ],
        "uploads.tar.gz": [
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "--entrypoint",
            "tar",
            "backend",
            "czf",
            "-",
            "-C",
            "/app/var/uploads",
            ".",
        ],
        "categorization.tar.gz": [
            "run",
            "--rm",
            "--no-deps",
            "-T",
            "--entrypoint",
            "sh",
            "backend",
            "-c",
            "if [ -d /app/var/models/categorization ]; then "
            "exec tar czf - -C /app/var/models categorization; "
            "else exec tar czf - --files-from /dev/null; fi",
        ],
    }
    hashes = {}
    for name, command in exports.items():
        with (target / name).open("xb") as output:
            result = subprocess.run(
                [*compose, *command],
                cwd=ROOT,
                stdout=output,
                stderr=subprocess.PIPE,
                check=False,
            )
        if result.returncode:
            raise SystemExit(
                f"Backup failed for {name}; incomplete directory retained, no success manifest"
            )
        hashes[name] = hashlib.sha256((target / name).read_bytes()).hexdigest()
    (target / "manifest.json").write_text(
        json.dumps(
            {
                "generated_at": datetime.now(UTC).isoformat(),
                "project": args.project,
                "sha256": hashes,
                "restore_notes": "Use a new database and original roles: BACKUP_RECOVERY.md.",
                "model_weights": "Redownload exact pinned revisions; learned artifact is included.",
                "secrets": "Retain QR/auth/config secrets separately in protected storage.",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Backup complete: {target.relative_to(ROOT)}. Contains private data; keep it protected.")


if __name__ == "__main__":
    main()
