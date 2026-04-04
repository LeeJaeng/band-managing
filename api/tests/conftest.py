"""테스트용 SQLite in-memory DB + FastAPI TestClient 설정."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from db import Base, get_db
from main import app

TEST_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestSession = sessionmaker(bind=engine)


def override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """각 테스트 전에 테이블을 생성하고 후에 삭제."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def admin_user(db):
    """테스트용 관리자 유저 생성."""
    from models import User
    from auth import hash_password
    user = User(
        username="testadmin",
        password_hash=hash_password("adminpass"),
        display_name="테스트관리자",
        role="ADMIN",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def member_user(db):
    """테스트용 일반 유저 생성."""
    from models import User
    from auth import hash_password
    user = User(
        username="testmember",
        password_hash=hash_password("memberpass"),
        display_name="테스트멤버",
        role="MEMBER",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def admin_headers(client, admin_user):
    """관리자 인증 헤더."""
    res = client.post("/api/auth/login", json={"username": "testadmin", "password": "adminpass"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def member_headers(client, member_user):
    """일반 유저 인증 헤더."""
    res = client.post("/api/auth/login", json={"username": "testmember", "password": "memberpass"})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
