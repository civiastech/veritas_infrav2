
def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_contractor_cannot_create_project(client):
    headers = _login(client, "o.adeyemi@visc.org", "stable123")
    res = client.post("/api/v1/projects", json={"uid": "TEST-1", "name": "Forbidden Project"}, headers=headers)
    assert res.status_code == 403

def test_admin_can_create_project(client):
    headers = _login(client, "admin@visc.org", "admin123")
    payload = {"uid": "TEST-ALLOW-1", "name": "Allowed Project"}
    res = client.post("/api/v1/projects", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["uid"] == "TEST-ALLOW-1"
