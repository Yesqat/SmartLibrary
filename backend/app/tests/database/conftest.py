import os

import pytest

from app.db.manage import engine
from app.db.seed import seed_development


@pytest.fixture(scope="session")
def test_database_name():
    name = os.environ.get("PHASE2_TEST_DATABASE", "")
    if not name:
        pytest.skip("Run the database-tests Compose service for real PostgreSQL integration")
    if not name.startswith("smartlibrary_test_") or len(name) != 50:
        pytest.fail("Integration tests require the tool's isolated test database")
    return name


@pytest.fixture(scope="session")
def db_engine(test_database_name):
    seed_development(test_database_name)
    db = engine("migration", test_database_name)
    yield db
    db.dispose()


@pytest.fixture(scope="session")
def runtime_engine(test_database_name):
    db = engine("runtime", test_database_name)
    yield db
    db.dispose()


@pytest.fixture
def connection(db_engine):
    with db_engine.connect() as connection:
        transaction = connection.begin()
        yield connection
        transaction.rollback()
