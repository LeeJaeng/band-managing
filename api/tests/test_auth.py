"""인증 관련 테스트."""

from auth import hash_password
from models import User


def _seed_user(db, username="testuser", password="testpass", role="MEMBER"):
    user = User(
        username=username,
        password_hash=hash_password(password),
        display_name="테스트유저",
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _login(client, username="testuser", password="testpass"):
    res = client.post("/api/auth/login", json={"username": username, "password": password})
    return res


def _auth_header(client, username="testuser", password="testpass"):
    res = _login(client, username, password)
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_login_success(client, db):
    _seed_user(db)
    res = _login(client)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["user"]["username"] == "testuser"
    assert data["user"]["role"] == "MEMBER"


def test_login_wrong_password(client, db):
    _seed_user(db)
    res = _login(client, password="wrong")
    assert res.status_code == 401


def test_login_nonexistent_user(client):
    res = _login(client, username="nobody")
    assert res.status_code == 401


def test_me_endpoint(client, db):
    _seed_user(db)
    headers = _auth_header(client)
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["username"] == "testuser"


def test_me_without_token(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_me_invalid_token(client):
    res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalidtoken"})
    assert res.status_code == 401


def test_admin_login(client, db):
    _seed_user(db, username="admin", password="adminpass", role="ADMIN")
    res = _login(client, username="admin", password="adminpass")
    assert res.status_code == 200
    assert res.json()["user"]["role"] == "ADMIN"
