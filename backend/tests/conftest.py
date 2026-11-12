import pytest
from fastapi.testclient import TestClient

from app.config import reset_settings_cache
from app.seed import DEMO_PASSWORD


@pytest.fixture()
def client(tmp_path, monkeypatch):
    dbfile = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{dbfile}")
    monkeypatch.setenv("JWT_SECRET", "test-jwt-secret-do-not-use-32b!!")
    monkeypatch.setenv("DEMO_RESET_ENABLED", "true")
    monkeypatch.delenv("REDIS_URL", raising=False)
    reset_settings_cache()
    import app.db as dbmod
    from app.main import create_app

    application = create_app()
    with TestClient(application) as c:
        yield c
    reset_settings_cache()
    if dbmod.engine is not None:
        dbmod.engine.dispose()


def login(client: TestClient, username: str, password: str = DEMO_PASSWORD) -> dict:
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, res.text
    return res.json()


def auth_header(client: TestClient, username: str) -> dict:
    token = login(client, username)["access_token"]
    return {"Authorization": f"Bearer {token}"}
