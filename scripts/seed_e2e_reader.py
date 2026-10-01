"""Create one fresh development Reader for non-registration browser scenarios.

Run with the Compose database operator service. Never resets existing accounts,
changes API rate limits or creates privileged roles. Prints only the new email.
"""

import os
from uuid import uuid4

from app.core.config import Settings
from app.db.manage import engine
from app.schemas.auth import RegisterInput
from app.services.audit.events import AuditContext
from app.services.auth.service import AuthService

settings = Settings()
if settings.app_env not in {"development", "test"}:
    raise SystemExit("Browser fixtures require a development/test environment")
password = os.environ.get("DEV_SEED_PASSWORD", "")
if len(password) < 12:
    raise SystemExit("Configure private DEV_SEED_PASSWORD before seeding")
database = engine("runtime")
try:
    data = RegisterInput.model_validate(
        {
            "email": f"e2e-admin-{uuid4().hex}@example.com",
            "password": password,
            "first_name": "Оқырман",
            "last_name": "Тексеру",
        }
    )
    user = AuthService(database, settings, AuditContext()).register(data)
    print(user.email)
finally:
    database.dispose()
