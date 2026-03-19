#======================================================================
# [ test_health.py ]
# 작성자:     2376292 최승
# 최종 수정:  2026.03.18
#======================================================================

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with TestClient(app) as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


def test_job_object_level_auth_forbidden_other_user_same_tenant():
    with TestClient(app) as client:
        # user A creates a job
        create = client.post(
            "/jobs",
            headers={"x-user-id": "user-a", "x-tenant-id": "tenant-1", "x-role": "user"},
            json={"source_object_key": "raw/tenant-1/user-a/demo.csv"},
        )
        assert create.status_code == 201
        job_id = create.json()["job_id"]

        # user B (same tenant) must NOT read user A's job
        read = client.get(
            f"/jobs/{job_id}",
            headers={"x-user-id": "user-b", "x-tenant-id": "tenant-1", "x-role": "user"},
        )
        assert read.status_code == 403


def test_job_object_level_auth_allows_owner():
    with TestClient(app) as client:
        create = client.post(
            "/jobs",
            headers={"x-user-id": "user-c", "x-tenant-id": "tenant-2", "x-role": "user"},
            json={"source_object_key": "raw/tenant-2/user-c/demo.csv"},
        )
        assert create.status_code == 201
        job_id = create.json()["job_id"]

        read = client.get(
            f"/jobs/{job_id}",
            headers={"x-user-id": "user-c", "x-tenant-id": "tenant-2", "x-role": "user"},
        )
        assert read.status_code == 200

#======================================================================