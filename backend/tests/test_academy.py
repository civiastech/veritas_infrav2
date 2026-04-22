
def _login(client, email, password):
    res = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert res.status_code == 200
    return {'Authorization': f"Bearer {res.json()['access_token']}"}


def test_academy_enrollment_completion_and_summary(client):
    headers = _login(client, 'a.okonkwo@visc.org', 'honor123')
    enrolled = client.post('/api/v1/academy/enrollments', headers=headers, json={'course_code': 'COURSE-SHI-FOUND'})
    assert enrolled.status_code == 200
    completed = client.post(f"/api/v1/academy/enrollments/{enrolled.json()['id']}/complete", headers=headers, json={'score': 93})
    assert completed.status_code == 200
    summary = client.get('/api/v1/academy/advancement/me', headers=headers)
    assert summary.status_code == 200
    assert summary.json()['completed_courses'] >= 1
