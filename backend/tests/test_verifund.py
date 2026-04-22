
def _login(client, email, password):
    res = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['access_token']}"}


def test_verifund_application_and_evaluation(client):
    headers = _login(client, 'admin@visc.org', 'admin123')
    created = client.post('/api/v1/verifund/applications', headers=headers, json={
        'application_uid': 'UW-TEST-001',
        'project_uid': 'BLD-GHA-001-2026',
        'product_code': 'VF-INSURE-PREM',
        'applicant_name': 'Goldcoast Properties Ltd',
        'requested_amount': 5000000,
        'currency': 'USD'
    })
    assert created.status_code == 200
    decision = client.post(f"/api/v1/verifund/applications/{created.json()['id']}/evaluate", headers=headers)
    assert decision.status_code == 200
    assert decision.json()['decision']['decision'] in {'approved', 'conditional', 'review', 'declined'}
