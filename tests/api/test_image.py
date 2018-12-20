

def test_get(client):
    response = client.get("/api/image/1")
    assert response.status_code == 400

