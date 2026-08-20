import json

from database import DatasetModel, UserModel

class TestDatasetSharing:

    @classmethod
    def setup_class(cls):
        DatasetModel.objects.delete()
        UserModel.objects.delete()

    def test_multiple_users_can_access_shared_dataset(self, client):
        # First registered user becomes admin
        response = client.post(
            "/api/user/register",
            json={
                "username": "owner",
                "password": "pass"
            }
        )
        assert response.status_code == 200

        # Create two additional users as admin
        response = client.post(
            "/api/admin/user/",
            json={
                "username": "user2",
                "password": "pass",
                "name": "User Two",
                "isAdmin": False
            }
        )
        assert response.status_code == 200

        response = client.post(
            "/api/admin/user/",
            json={
                "username": "user3",
                "password": "pass",
                "name": "User Three",
                "isAdmin": False
            }
        )
        assert response.status_code == 200

        # Owner creates a dataset
        response = client.post(
            "/api/dataset/",
            json={"name": "shared-dataset"}
        )
        assert response.status_code == 200

        # Owner shares dataset with both users
        response = client.post(
            "/api/dataset/1/share",
            json={"users": ["user2", "user3"]}
        )
        assert response.status_code == 200

        # Verify users were stored
        dataset = DatasetModel.objects(name="shared-dataset").first()
        assert dataset.users == ["user2", "user3"]

        # Verify user2 can access the dataset
        client.get("/api/user/logout")
        response = client.post(
            "/api/user/login",
            json={
                "username": "user2",
                "password": "pass"
            }
        )
        assert response.status_code == 200

        response = client.get("/api/dataset/")
        assert response.status_code == 200

        datasets = json.loads(response.data)
        assert any(dataset["name"] == "shared-dataset" for dataset in datasets)

        # Verify user3 can access the dataset
        client.get("/api/user/logout")
        response = client.post(
            "/api/user/login",
            json={
                "username": "user3",
                "password": "pass"
            }
        )
        assert response.status_code == 200

        response = client.get("/api/dataset/")
        assert response.status_code == 200

        datasets = json.loads(response.data)
        assert any(dataset["name"] == "shared-dataset" for dataset in datasets)