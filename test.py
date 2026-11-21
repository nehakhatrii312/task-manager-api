import os
import tempfile

# set environment BEFORE importing the app
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["API_KEY"] = "test-key"

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
client = TestClient(app)
HEADERS = {"X-API-Key": "test-key"}

def make_task(**overrides):
    payload = {"title": "Test task", "description": "demo", "priority": "high"}
    payload.update(overrides)
    return client.post("/tasks", json=payload, headers=HEADERS)

# ---------- health & authentication ----------
def test_health_is_public():
    res = client.get("/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

def test_missing_api_key_rejected():
    assert client.get("/tasks").status_code == 401

def test_wrong_api_key_rejected():
    res = client.get("/tasks", headers={"X-API-Key": "wrong"})
    assert res.status_code == 401

# ---------- create + validation ----------
def test_create_task():
    res = make_task()
    assert res.status_code == 201
    body = res.json()
    assert body["title"] == "Test task"
    assert body["completed"] is False
    assert "id" in body

def test_empty_title_fails_validation():
    assert make_task(title="").status_code == 422

def test_invalid_priority_fails_validation():
    assert make_task(priority="urgent").status_code == 422

# ---------- read ----------
def test_get_task_by_id():
    task_id = make_task().json()["id"]
    res = client.get(f"/tasks/{task_id}", headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["id"] == task_id

def test_get_missing_task_returns_404():
    assert client.get("/tasks/99999", headers=HEADERS).status_code == 404

def test_list_and_filter_tasks():
    make_task(priority="low")
    res = client.get("/tasks?priority=low", headers=HEADERS)
    assert res.status_code == 200
    assert len(res.json()) >= 1
    assert all(t["priority"] == "low" for t in res.json())

# ---------- update ----------
def test_put_replaces_task():
    task_id = make_task().json()["id"]
    new = {"title": "Replaced", "priority": "low", "completed": True}
    res = client.put(f"/tasks/{task_id}", json=new, headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["title"] == "Replaced"
    assert res.json()["completed"] is True

def test_patch_updates_only_sent_fields():
    task = make_task().json()
    res = client.patch(f"/tasks/{task['id']}", json={"completed": True}, headers=HEADERS)
    assert res.status_code == 200
    assert res.json()["completed"] is True
    assert res.json()["title"] == task["title"]  # unchanged

def test_patch_with_empty_body_returns_400():
    task_id = make_task().json()["id"]
    assert client.patch(f"/tasks/{task_id}", json={}, headers=HEADERS).status_code == 400

# ---------- delete ----------
def test_delete_task():
    task_id = make_task().json()["id"]
    assert client.delete(f"/tasks/{task_id}", headers=HEADERS).status_code == 204
    assert client.get(f"/tasks/{task_id}", headers=HEADERS).status_code == 404
