import pytest
import os
from app import app, db


@pytest.fixture
def client():
    print(os.getenv("MONGODB_HOST", "mongodb://database/flask"))
    print(app.extensions['mongoengine'][db])
    return app.test_client()
