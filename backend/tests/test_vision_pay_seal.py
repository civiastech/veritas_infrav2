
def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_inspection_payment_and_certificate_flow(client):
    engineer = _login(client, "a.okonkwo@visc.org", "honor123")
    inspector = _login(client, "m.rodrigues@visc.org", "honor123")

    # upload and approve evidence for blocked component
    files = {"file": ("beam.txt", b"reinforcement evidence", "text/plain")}
    data = {"component_uid": "BLD-NGR-LH1/L3/S1/SLAB/004", "description": "Ready for inspection"}
    upload = client.post("/api/v1/evidence/upload", headers=engineer, files=files, data=data)
    evidence_id = upload.json()["evidence_id"]
    approve = client.patch(f"/api/v1/evidence/{evidence_id}", headers=inspector, data={"status_text": "approved"})
    assert approve.status_code == 200

    inspection = client.post("/api/v1/vision/inspections", headers=inspector, json={
        "component_uid": "BLD-NGR-LH1/L3/S1/SLAB/004",
        "material_score": 92,
        "assembly_score": 90,
        "env_score": 88,
        "supervision_score": 94,
        "reason_tag": "Good installation"
    })
    assert inspection.status_code == 200
    assert inspection.json()["shi"] >= 90

    gate = client.post("/api/v1/pay/milestones/2/evaluate", headers=engineer)
    assert gate.status_code == 200
    release = client.post("/api/v1/pay/milestones/2/release", headers=engineer)
    assert release.status_code == 200
    assert release.json()["status"] in {"completed", "blocked"}

    eligibility = client.get("/api/v1/seal/projects/BLD-GHA-001-2026/eligibility", headers=engineer)
    assert eligibility.status_code == 200
    if eligibility.json()["eligible"]:
        issued = client.post("/api/v1/seal/issue", headers=engineer, json={"project_uid": "BLD-GHA-001-2026"})
        assert issued.status_code == 200
        public = client.get("/api/v1/public/seal/BLD-GHA-001-2026")
        assert public.status_code == 200
