import os

from dotenv import load_dotenv
load_dotenv()

# These must be set before anything from `app` is imported.
os.environ["DATABASE_URL"] = os.getenv("TEST_DATABASE_URL", "sqlite://")
os.environ["ENVIRONMENT"] = "test"
os.environ["EMAIL_BACKEND"] = "memory"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-long-enough-for-hs256"
os.environ["MEDIA_DIR"] = "/tmp/biletflow-test-media"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


import app.models  # noqa: E402, F401
from app.core.database import Base, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.shared import mailer  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture(autouse=True)
def _clean():
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
    mailer.outbox.clear()
    yield


@pytest.fixture
def client():
    with TestClient(fastapi_app) as test_client:
        yield test_client
