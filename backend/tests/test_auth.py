from app.seed import DEMO_PASSWORD
from tests.conftest import auth_header, login


def test_login_success(client):
    data = login(client, "admin")
    assert data["token_type"] == "bearer"
    assert data["role"] == "admin"
    assert data["access_token"]
    assert data["user"]["username"] == "admin"
    assert data["user"]["name"] == "系统管理员"


def test_login_rejects_bad_password(client):
    res = client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["code"] == "invalid_credentials"
    assert "password" not in res.text.lower() or "CampusDemo" not in res.text


def test_me_requires_token(client):
    res = client.get("/api/v1/me")
    assert res.status_code == 401


def test_me_and_roles(client):
    res = client.get("/api/v1/me", headers=auth_header(client, "stu.chen"))
    assert res.status_code == 200
    body = res.json()
    profile = body.get("user") or body
    assert profile["role"] == "student"
    assert profile["is_freshman"] is True
    assert profile["name"] == "陈晓"


def test_admin_users_forbidden_for_student(client):
    res = client.get("/api/v1/admin/users", headers=auth_header(client, "stu.lin"))
    assert res.status_code == 403
