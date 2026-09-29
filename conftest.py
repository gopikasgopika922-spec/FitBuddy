import os

os.environ["DATABASE_URL"] = "sqlite:///./test_fitbuddy.db"
os.environ["DEMO_MODE"] = "true"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ADMIN_PASSWORD"] = "test-password"

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    get_settings.cache_clear()
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
