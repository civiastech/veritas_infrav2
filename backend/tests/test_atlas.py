
def _login(client, email, password):
    res = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['access_token']}"}


def test_atlas_report_and_overview(client):
    headers = _login(client, 'admin@visc.org', 'admin123')
    overview = client.get('/api/v1/atlas/portfolio/overview', headers=headers)
    assert overview.status_code == 200
    assert overview.json()['total_projects'] >= 1
    created = client.post('/api/v1/atlas/reports', headers=headers, json={'title': 'Nigeria Portfolio', 'country_scope': 'Nigeria'})
    assert created.status_code == 200
    assert created.json()['title'] == 'Nigeria Portfolio'
