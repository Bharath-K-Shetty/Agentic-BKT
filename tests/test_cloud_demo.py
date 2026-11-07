import pytest
from fastapi.testclient import TestClient
from webapp.backend import cloud
from webapp.backend.prospective import StudyStore
from webapp.backend.live_history import snapshot_path


def test_cloud_login_covers_pages_and_apis(monkeypatch):
    monkeypatch.setenv('HOMIE_DEMO_USER', 'evaluator')
    monkeypatch.setenv('HOMIE_DEMO_PASSWORD', 'demo5')
    monkeypatch.setattr(cloud, 'artifacts', lambda: None)
    monkeypatch.setattr(cloud, 'bundle', lambda: None)
    client = TestClient(cloud.create_app())
    assert client.get('/healthz').status_code == 200
    for path in ['/', '/api/study', '/api/model/examples', '/docs']:
        assert client.get(path).status_code == 401
    assert client.get('/', auth=('evaluator', 'wrong')).status_code == 401
    assert client.get('/', headers={'Authorization': 'Basic !!!!'}).status_code == 401
    assert client.get('/', auth=('evaluator', 'demo5')).status_code == 200


def test_cloud_requires_credentials(monkeypatch):
    monkeypatch.delenv('HOMIE_DEMO_PASSWORD', raising=False)
    with pytest.raises(RuntimeError, match='HOMIE_DEMO_PASSWORD'):
        cloud.create_app()


def test_state_survives_store_reopen_in_configured_volume(monkeypatch, tmp_path):
    monkeypatch.setenv('HOMIE_STATE_DIR', str(tmp_path))
    first = StudyStore()
    result = first.record({'network': 'devnet', 'check': 'test'})
    reopened = StudyStore()
    assert reopened.path == tmp_path/'prospective.sqlite3'
    assert reopened.decision(result['decision_id'])[0]['check'] == 'test'
    assert snapshot_path('devnet') == tmp_path/'live_history_devnet.json'


@pytest.mark.parametrize('password', ['', '1234'])
def test_cloud_rejects_passwords_below_five(monkeypatch, password):
    monkeypatch.setenv('HOMIE_DEMO_USER', 'homie')
    monkeypatch.setenv('HOMIE_DEMO_PASSWORD', password)
    with pytest.raises(RuntimeError, match='at least 5'):
        cloud.create_app()
