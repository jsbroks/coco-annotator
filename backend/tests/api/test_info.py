import json


def test_info(client):
    response = client.get('/api/info/')
    data = json.loads(response.data)

    assert data.get("git") is not None

