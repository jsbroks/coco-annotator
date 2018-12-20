import json


def test_app(client):
    swagger = client.get('/api/swagger.json')
    assert swagger is not None
