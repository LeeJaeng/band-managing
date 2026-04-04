"""팀 멤버 CRUD 테스트."""


def test_create_member(client, admin_headers):
    res = client.post("/api/team/members", json={"name": "홍길동", "position": "피아노"}, headers=admin_headers)
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "홍길동"
    assert data["position"] == "피아노"
    assert "id" in data


def test_create_member_requires_admin(client, member_headers):
    res = client.post("/api/team/members", json={"name": "홍길동", "position": "피아노"}, headers=member_headers)
    assert res.status_code == 403


def test_list_members(client, admin_headers):
    client.post("/api/team/members", json={"name": "홍길동", "position": "피아노"}, headers=admin_headers)
    client.post("/api/team/members", json={"name": "김철수", "position": "드럼"}, headers=admin_headers)

    res = client.get("/api/team/members", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_members_requires_auth(client):
    res = client.get("/api/team/members")
    assert res.status_code == 401


def test_get_member(client, admin_headers):
    created = client.post("/api/team/members", json={"name": "홍길동", "position": "보컬"}, headers=admin_headers).json()

    res = client.get(f"/api/team/members/{created['id']}", headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["name"] == "홍길동"


def test_update_member(client, admin_headers):
    created = client.post("/api/team/members", json={"name": "홍길동", "position": "보컬"}, headers=admin_headers).json()

    res = client.put(f"/api/team/members/{created['id']}", json={"position": "피아노"}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["position"] == "피아노"
    assert res.json()["name"] == "홍길동"


def test_toggle_active(client, admin_headers):
    created = client.post("/api/team/members", json={"name": "홍길동", "position": "드럼"}, headers=admin_headers).json()

    res = client.put(f"/api/team/members/{created['id']}", json={"is_active": False}, headers=admin_headers)
    assert res.status_code == 200
    assert res.json()["is_active"] is False


def test_filter_active_only(client, admin_headers):
    client.post("/api/team/members", json={"name": "활성", "position": "보컬"}, headers=admin_headers)
    inactive = client.post("/api/team/members", json={"name": "비활성", "position": "드럼"}, headers=admin_headers).json()
    client.put(f"/api/team/members/{inactive['id']}", json={"is_active": False}, headers=admin_headers)

    res = client.get("/api/team/members?active_only=true", headers=admin_headers)
    data = res.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "활성"


def test_delete_member(client, admin_headers):
    created = client.post("/api/team/members", json={"name": "홍길동", "position": "기타"}, headers=admin_headers).json()

    res = client.delete(f"/api/team/members/{created['id']}", headers=admin_headers)
    assert res.status_code == 200

    res = client.get(f"/api/team/members/{created['id']}", headers=admin_headers)
    assert res.status_code == 404


def test_get_nonexistent_member(client, admin_headers):
    res = client.get("/api/team/members/nonexistent", headers=admin_headers)
    assert res.status_code == 404
