
def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_evidence_upload_approve_and_twin_events(client):
    engineer = _login(client, "a.okonkwo@visc.org", "honor123")
    files = {"file": ("shot1.txt", b"hello world", "text/plain")}
    data = {"component_uid": "BLD-NGR-LH1/L3/S1/SLAB/004", "description": "Upload test"}
    upload = client.post("/api/v1/evidence/upload", headers=engineer, files=files, data=data)
    assert upload.status_code == 200
    evidence_assets = client.get(f"/api/v1/evidence/{upload.json()['evidence_id']}/assets", headers=engineer)
    assert evidence_assets.status_code == 200
    inspector = _login(client, "m.rodrigues@visc.org", "honor123")
    approve = client.patch(f"/api/v1/evidence/{upload.json()['evidence_id']}", headers=inspector, data={"status_text": "approved"})
    assert approve.status_code == 200
    twin = client.get("/api/v1/twin/projects/BLD-NGR-LH1-2026/events", headers=engineer)
    assert twin.status_code == 200
    types = [x["event_type"] for x in twin.json()["items"]]
    assert "BUILD.EVIDENCE_SUBMITTED" in types
    assert "BUILD.EVIDENCE_APPROVED" in types
