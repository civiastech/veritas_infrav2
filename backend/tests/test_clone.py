def _login(client, email, password):
    res = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['access_token']}"}


def test_clone_rollout_summary_and_country_create(client):
    headers = _login(client, 'admin@visc.org', 'admin123')
    res = client.get('/api/v1/clone/rollout/summary', headers=headers)
    assert res.status_code == 200
    assert res.json()['total_countries'] >= 1
    created = client.post('/api/v1/clone/countries', headers=headers, json={'code': 'KE', 'name': 'Kenya', 'region': 'East Africa', 'launch_stage': 'pipeline', 'readiness_score': 70, 'regulator_appetite': 'medium', 'status': 'active'})
    assert created.status_code == 200
    assert created.json()['code'] == 'KE'
