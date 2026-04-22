def _login(client, email, password):
    res = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['access_token']}"}


def test_regulatory_readiness_and_consultation(client):
    headers = _login(client, 'admin@visc.org', 'admin123')
    readiness = client.get('/api/v1/regulatory/readiness', headers=headers)
    assert readiness.status_code == 200
    assert readiness.json()['tracked_countries'] >= 1
    created = client.post('/api/v1/regulatory/consultations', headers=headers, json={
        'consultation_uid': 'CONS-TEST-001',
        'country_code': 'NG',
        'title': 'Test Consultation',
        'consultation_type': 'regulatory',
        'status': 'open',
        'opened_at_label': '2026-04-17'
    })
    assert created.status_code == 200
    assert created.json()['consultation_uid'] == 'CONS-TEST-001'
