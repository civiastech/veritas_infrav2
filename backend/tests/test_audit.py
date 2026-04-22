
def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_audit_log_visible_to_admin(client):
    headers = _login(client, "admin@visc.org", "admin123")
    res = client.get("/api/v1/audit", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1
