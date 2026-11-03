import json
import pytest


@pytest.mark.order(1)
def test_api(client):
    response = client.get('/api/swagger.json')
    assert response is not None
    data = json.loads(response.data)
    endpoints = data.get('paths').keys()
    assert len(endpoints) > 0



