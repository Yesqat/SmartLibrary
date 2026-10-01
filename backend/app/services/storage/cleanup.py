"""Remove only generated, unreferenced local images older than a 24-hour safety window."""

import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models.catalog import Book
from app.db.models.users import User
from app.db.session import create_db_engine
from app.services.storage.images import PREFIX, SAFE_NAME, LocalImageStorage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Delete eligible orphan files")
    args = parser.parse_args()
    settings = get_settings()
    storage = LocalImageStorage(settings.upload_directory)
    engine = create_db_engine(settings)
    cutoff = (datetime.now(UTC) - timedelta(hours=24)).timestamp()
    candidates = 0
    try:
        with Session(engine) as db:
            if storage.directory.is_dir():
                for path in storage.directory.iterdir():
                    if (
                        not SAFE_NAME.fullmatch(path.name)
                        or path.is_symlink()
                        or path.stat().st_mtime >= cutoff
                    ):
                        continue
                    url = PREFIX + path.name
                    if db.scalar(
                        select(Book.id).where(Book.cover_url == url).limit(1)
                    ) or db.scalar(select(User.id).where(User.avatar_url == url).limit(1)):
                        continue
                    candidates += 1
                    if args.apply:
                        storage.delete(url)
        print(f"Eligible orphan images: {candidates}; apply={args.apply}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
