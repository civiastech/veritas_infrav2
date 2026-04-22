def _login(client, email, password):
    res = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['access_token']}"}


def test_governance_dashboard_and_resolution(client):
    headers = _login(client, 'admin@visc.org', 'admin123')
    dash = client.get('/api/v1/governance/dashboard', headers=headers)
    assert dash.status_code == 200
    assert dash.json()['active_members'] >= 1
    created = client.post('/api/v1/governance/resolutions', headers=headers, json={
        'resolution_uid': 'RES-TEST-001',
        'committee_code': 'CST-STD',
        'title': 'Test Resolution',
        'resolution_type': 'standard',
        'body_text': 'Adopt test workflow.',
        'status': 'draft'
    })
    assert created.status_code == 200
    assert created.json()['resolution_uid'] == 'RES-TEST-001'
