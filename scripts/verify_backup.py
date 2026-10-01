"""Restore a backup into a new random database, then remove only that database."""

import argparse
import hashlib
import json
import subprocess
import tarfile
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--project", default="smartlibrary")
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("-f", "--file", action="append", default=[])
    args = parser.parse_args()
    directory = (ROOT / args.directory).resolve()
    if not directory.is_relative_to(ROOT / "var/backups"):
        parser.error("Select an existing backup inside var/backups")
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    for name in ("database.dump", "uploads.tar.gz", "categorization.tar.gz"):
        assert (
            hashlib.sha256((directory / name).read_bytes()).hexdigest() == manifest["sha256"][name]
        )
    for name in ("uploads.tar.gz", "categorization.tar.gz"):
        with tarfile.open(directory / name) as archive:
            for item in archive:
                assert not item.issym() and not item.islnk() and not item.isdev()
                assert not Path(item.name).is_absolute() and ".." not in Path(item.name).parts
                if item.isfile():
                    content = archive.extractfile(item)
                    assert content is not None
                    while content.read(1024 * 1024):
                        pass
        print(f"PASS {name}: readable, safe archive entries")
    compose = ["docker", "compose", "-p", args.project, "--env-file", args.env_file]
    for name in ["docker-compose.yml", *args.file]:
        compose += ["-f", name]

    def run(command: list[str], data: bytes | None = None) -> bytes:
        result = subprocess.run([*compose, *command], cwd=ROOT, input=data, capture_output=True)
        if result.returncode:
            raise RuntimeError(
                "Isolated restore command failed; no persistent database was targeted"
            )
        return result.stdout

    name = "smartlibrary_restore_" + uuid4().hex
    created = False
    try:
        run(
            [
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'exec createdb -U "$POSTGRES_USER" "$1"',
                "sh",
                name,
            ]
        )
        created = True
        run(
            [
                "exec",
                "-T",
                "postgres",
                "sh",
                "-c",
                'exec pg_restore -U "$POSTGRES_USER" -d "$1" --exit-on-error --single-transaction',
                "sh",
                name,
            ],
            (directory / "database.dump").read_bytes(),
        )
        run(
            [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                f"POSTGRES_DB={name}",
                "database",
                "python",
                "-m",
                "app.db.manage",
                "check",
            ]
        )
        verification = """
from sqlalchemy import text
from app.db.manage import engine
db=engine('runtime')
with db.connect() as c:
    query="SELECT extname FROM pg_extension WHERE extname IN ('vector','pg_trgm')"
    assert set(c.scalars(text(query))) == {'vector','pg_trgm'}
    tables=('users','books','book_copies','reservations','borrowings','audit_logs','system_settings')
    for table in tables:
        count=c.scalar(text('SELECT count(*) FROM '+table))
        print(table+': '+str(count)+' restored rows')
    query="SELECT count(*) FROM information_schema.tables WHERE table_schema='public'"
    assert c.scalar(text(query)) == 27
db.dispose()
"""
        result = run(
            [
                "run",
                "--rm",
                "--no-deps",
                "-T",
                "-e",
                f"POSTGRES_DB={name}",
                "database",
                "python",
                "-c",
                verification,
            ]
        )
        print(result.decode().strip())
        print(
            "PASS isolated PostgreSQL restore, Alembic drift, extensions and restricted role reads"
        )
    finally:
        if created:
            run(
                [
                    "exec",
                    "-T",
                    "postgres",
                    "sh",
                    "-c",
                    'exec dropdb -U "$POSTGRES_USER" "$1"',
                    "sh",
                    name,
                ]
            )
            print(
                "Removed only this run's random restored database; persistent database unchanged."
            )


if __name__ == "__main__":
    main()
