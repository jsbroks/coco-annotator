import json
import pytest

from database import CategoryModel

category1_id = 0
category2_id = 0
category3_id = 0


class TestCategory:

    @classmethod
    def setup_class(cls):
        CategoryModel.objects.delete()

    @pytest.mark.run(before='test_post_categories')
    def test_get_empty(self, client):
        response = client.get("/api/category/")
        data = json.loads(response.data)

        assert isinstance(data, list)
        assert len(data) == 0

    def test_post_no_data(self, client):
        response = client.post("/api/category/")
        assert response.status_code == 400

    @pytest.mark.run(after="test_get_empty")
    def test_post_categories(self, client):
        global category1_id, category2_id, category3_id
        # Category 1 Test
        data = {
            "name": "test1"
        }
        response = client.post("/api/category/", json=data)

        r = json.loads(response.data)
        assert response.status_code == 200
        assert r.get("name") == data.get("name")
        assert r.get("color") is not None
        assert r.get("id") is not None
        category1_id = r.get("id")

        # Category 2 Test
        data = {
            "name": "test2",
            "color": "white",
            "metadata": {"key1": True, "key2": 1, "key3": "value"}
        }
        response = client.post("/api/category/", json=data)

        r = json.loads(response.data)
        assert response.status_code == 200
        assert r.get("name") == data.get("name")
        assert r.get("color") == data.get("color")
        assert r.get("metadata") == data.get("metadata")
        assert r.get("id") is not None
        category2_id = r.get("id")

        # Category 3 Test
        data = {
            "name": "test3"
        }
        response = client.post("/api/category/", json=data)

        r = json.loads(response.data)
        assert response.status_code == 200
        assert r.get("name") == data.get("name")
        assert r.get("metadata") is not None
        assert r.get("id") is not None
        category3_id = r.get("id")

    def test_post_categories_invalid(self, client):
        pass

    @pytest.mark.run(after='test_post_categories')
    def test_post_already_existing_category(self, client):
        pass


class TestCategoryId:

    @pytest.mark.run(after='test_post_categories')
    def test_get(self, client):
        response = client.get("/api/category/{}".format(category2_id))

        r = json.loads(response.data)
        assert response.status_code == 200
        assert r.get("name") == "test2"
        assert r.get("color") == "white"

    def test_get_invalid_id(self, client):
        response = client.get("/api/category/1000")
        assert response.status_code == 400

    def test_delete_invalid_id(self, client):
        response = client.delete("/api/category/1000")
        assert response.status_code == 400

    @pytest.mark.run(after='test_post_categories')
    def test_get(self, client):
        response = client.delete("/api/category/{}".format(category3_id))
        assert response.status_code == 200

    @pytest.mark.run(after='test_post_categories')
    def test_put_equal(self, client):
        """ Test response when the name to update is the same as already stored """
        data = {
            "name": "test1"
        }
        response = client.put("/api/category/{}".format(category1_id), json=data)
        assert response.status_code == 200

    def test_put_invalid_id(self, client):
        """ Test response when id does not exit """
        response = client.put("/api/category/1000")
        assert response.status_code == 400

    def test_put_not_unique(self, client):
        """ Test response when the name already exits """
        data = {
            "name": "test2"
        }
        response = client.put("/api/category/{}".format(category1_id), json=data)
        assert response.status_code == 400

    def test_put_empty(self, client):
        """ Test response when category name is empty"""
        data = {
            "name": ""
        }
        response = client.put("/api/category/{}".format(category1_id), json=data)
        assert response.status_code == 400

    @pytest.mark.run(after='test_put_not_unique')
    def test_put(self, client):
        """ Test response when update is correct"""
        data = {
            "name": "test1_updated"
        }
        response = client.put("/api/category/{}".format(category1_id), json=data)
        assert response.status_code == 200

    @pytest.mark.run(after='test_put')
    def test_put_reset(self, client):
        """ Reset test after a correct update """
        data = {
            "name": "test1"
        }
        response = client.put("/api/category/{}".format(category1_id), json=data)
        assert response.status_code == 200


class TestCategoryData:

    # TODO write tests for data
    def test(self):
        pass


