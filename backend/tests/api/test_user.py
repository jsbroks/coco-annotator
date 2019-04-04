import json
import pytest

from database import UserModel


@pytest.mark.second
class TestUser:

    @classmethod
    def setup_class(cls):
        UserModel.objects.delete()

    def test_create_first_user(self, client):
        response = client.post("/api/user/register", json={
            "username": "user",
            "password": "pass"
        })
        data = json.loads(response.data)
        assert data.get("success")

        user = data.get("user")
        assert user.get("is_admin")
