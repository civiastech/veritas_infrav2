
def test_login_and_me(client):
    res = client.post("/api/v1/auth/login", json={"email": "admin@visc.org", "password": "admin123"})
    assert res.status_code == 200
    body = res.json()
    assert "refresh_token" in body
    token = body["access_token"]
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "admin@visc.org"
