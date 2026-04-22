
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_platform_flag_roundtrip():
    payload = {
        "code": "atlas-v3",
        "name": "Atlas V3",
        "enabled": True,
        "environment": "test",
        "stability": "beta",
    }
    create = client.post('/api/v1/platform/flags', json=payload)
    assert create.status_code == 200
    read = client.get('/api/v1/platform/flags/atlas-v3?environment=test')
    assert read.status_code == 200
    assert read.json()['enabled'] is True
