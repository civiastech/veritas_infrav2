
def _login(client, email, password):
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return {"Authorization": f"Bearer {res.json()['access_token']}"}

def test_monitor_alert_and_lex_resolution(client):
    engineer = _login(client, "a.okonkwo@visc.org", "honor123")
    inspector = _login(client, "m.rodrigues@visc.org", "honor123")

    sensors = client.get("/api/v1/monitor/sensors", headers=engineer)
    assert sensors.status_code == 200
    sensor_id = sensors.json()["items"][0]["id"]

    reading = client.post("/api/v1/monitor/readings", headers=engineer, json={"sensor_id": sensor_id, "reading": 9.9})
    assert reading.status_code == 200
    assert reading.json()["alert"] is not None

    dispute = client.post("/api/v1/lex/disputes", headers=engineer, json={
        "uid": "LEX-NEW-001",
        "project_uid": "BLD-NGR-LH1-2026",
        "component_uid": "BLD-NGR-LH1/L1/C1/COL/001",
        "type": "Technical Execution",
        "against_party": "Contractor",
        "description": "Improper execution concern"
    })
    assert dispute.status_code == 200

    resolved = client.post(f"/api/v1/lex/disputes/{dispute.json()['id']}/resolve", headers=inspector, json={"resolution": "Corrective works accepted"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
