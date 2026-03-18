#======================================================================
# [ test_health.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.18
#======================================================================

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

#======================================================================