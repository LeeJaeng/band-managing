"""콘티 CRUD + 항목 관리 테스트."""


def _create_song(client, headers, title="테스트곡"):
    return client.post("/api/songs", json={"title": title}, headers=headers).json()["id"]


def test_create_conti(client, member_headers):
    resp = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "청년예배",
        "author": "인도자",
    }, headers=member_headers)
    assert resp.status_code == 201
    assert resp.json()["service_name"] == "청년예배"


def test_create_conti_requires_auth(client):
    resp = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "청년예배", "author": "인도자",
    })
    assert resp.status_code == 401


def test_list_contis(client, member_headers):
    client.post("/api/contis", json={"date": "2026-04-06", "service_name": "청년예배", "author": "A"}, headers=member_headers)
    client.post("/api/contis", json={"date": "2026-04-13", "service_name": "주일2부", "author": "B"}, headers=member_headers)

    resp = client.get("/api/contis", headers=member_headers)
    assert resp.json()["total"] == 2


def test_list_contis_requires_auth(client):
    resp = client.get("/api/contis")
    assert resp.status_code == 401


def test_list_contis_only_own(client, member_headers, admin_headers):
    """다른 유저의 콘티는 보이지 않아야 함."""
    client.post("/api/contis", json={"date": "2026-04-06", "service_name": "멤버콘티", "author": "멤버"}, headers=member_headers)
    client.post("/api/contis", json={"date": "2026-04-07", "service_name": "관리자콘티", "author": "관리자"}, headers=admin_headers)

    member_list = client.get("/api/contis", headers=member_headers).json()
    assert member_list["total"] == 1
    assert member_list["items"][0]["service_name"] == "멤버콘티"

    admin_list = client.get("/api/contis", headers=admin_headers).json()
    assert admin_list["total"] == 1
    assert admin_list["items"][0]["service_name"] == "관리자콘티"


def test_get_conti_detail(client, member_headers):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "청년예배",
        "author": "인도자",
    }, headers=member_headers).json()

    resp = client.get(f"/api/contis/{conti['id']}")
    assert resp.status_code == 200
    assert resp.json()["service_name"] == "청년예배"
    assert resp.json()["items"] == []


def test_update_conti(client, member_headers):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "원래이름",
        "author": "인도자",
    }, headers=member_headers).json()

    resp = client.put(f"/api/contis/{conti['id']}", json={"service_name": "수정이름"}, headers=member_headers)
    assert resp.json()["service_name"] == "수정이름"


def test_delete_conti(client, member_headers):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "삭제할콘티",
        "author": "인도자",
    }, headers=member_headers).json()

    resp = client.delete(f"/api/contis/{conti['id']}", headers=member_headers)
    assert resp.json()["ok"] is True

    assert client.get(f"/api/contis/{conti['id']}").status_code == 404


def test_confirm_conti(client, member_headers):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "확정할콘티",
        "author": "인도자",
    }, headers=member_headers).json()

    resp = client.put(f"/api/contis/{conti['id']}/confirm", headers=member_headers)
    assert resp.json()["status"] == "CONFIRMED"


# ── Conti Items ────────────────────────────────────────

def test_add_item(client, member_headers):
    song_id = _create_song(client, member_headers)
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    resp = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id,
        "order_num": 1,
        "slot_label": "1번곡",
        "use_key": "A",
    }, headers=member_headers)
    assert resp.status_code == 201


def test_conti_with_items(client, member_headers):
    song1 = _create_song(client, member_headers, "찬양1")
    song2 = _create_song(client, member_headers, "찬양2")

    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song1, "order_num": 1, "slot_label": "1번곡",
    }, headers=member_headers)
    client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song2, "order_num": 2, "slot_label": "기도곡",
    }, headers=member_headers)

    detail = client.get(f"/api/contis/{conti['id']}").json()
    assert len(detail["items"]) == 2
    assert detail["items"][0]["song"]["title"] == "찬양1"
    assert detail["items"][1]["slot_label"] == "기도곡"


def test_update_item(client, member_headers):
    song_id = _create_song(client, member_headers)
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    item = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id, "order_num": 1, "slot_label": "1번곡",
    }, headers=member_headers).json()

    resp = client.put(f"/api/contis/items/{item['id']}", json={
        "use_key": "Bb",
        "memo": "인트로 없이",
    }, headers=member_headers)
    assert resp.json()["ok"] is True


def test_delete_item(client, member_headers):
    song_id = _create_song(client, member_headers)
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    item = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id, "order_num": 1,
    }, headers=member_headers).json()

    resp = client.delete(f"/api/contis/items/{item['id']}", headers=member_headers)
    assert resp.json()["ok"] is True

    detail = client.get(f"/api/contis/{conti['id']}").json()
    assert len(detail["items"]) == 0


# ── 직렬화 방어 (회귀 방지) ─────────────────────────

def test_get_conti_with_dangling_member(client, member_headers, db):
    """conti_member.member_id가 가리키는 team_member가 사라져도 500이 안 나야 함."""
    from models import TeamMember, Conti, ContiMember

    member = TeamMember(name="삭제될팀원", position="VOCAL")
    db.add(member)
    db.commit()

    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    client.post(f"/api/contis/{conti['id']}/members", json={
        "member_id": member.id, "position": "VOCAL",
    }, headers=member_headers)

    # FK 우회: SQLite는 PRAGMA foreign_keys=OFF가 기본 → 직접 행 삭제로 dangling 상태 만든다
    db.query(TeamMember).filter(TeamMember.id == member.id).delete()
    db.commit()

    resp = client.get(f"/api/contis/{conti['id']}")
    assert resp.status_code == 200
    members = resp.json()["members"]
    assert len(members) == 1
    assert members[0]["name"] == "(삭제된 팀원)"


def test_get_conti_with_dangling_song(client, member_headers, db):
    """conti_item.song_id가 가리키는 song이 사라져도 500이 안 나야 함."""
    from models import Song

    song_id = _create_song(client, member_headers, "사라질곡")
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()
    client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id, "order_num": 1, "slot_label": "1번곡",
    }, headers=member_headers)

    db.query(Song).filter(Song.id == song_id).delete()
    db.commit()

    resp = client.get(f"/api/contis/{conti['id']}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    # song 필드는 None이거나 placeholder여야 하고, 어쨌든 200으로 반환
    assert items[0]["song"] is None or items[0]["song"]["title"]


def test_get_conti_with_null_optional_fields(client, member_headers, db):
    """slot_label/use_key/memo가 NULL이어도 직렬화가 깨지지 않아야 함."""
    from models import ContiItem

    song_id = _create_song(client, member_headers, "null필드곡")
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    # ORM으로 직접 NULL slot_label 삽입 (POST 스키마의 default="" 우회)
    item = ContiItem(
        conti_id=conti["id"],
        song_id=song_id,
        order_num=1,
        slot_label=None,
        use_key=None,
        memo=None,
    )
    db.add(item)
    db.commit()

    resp = client.get(f"/api/contis/{conti['id']}")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) == 1
    assert items[0]["use_key"] is None


def test_get_conti_not_found(client):
    resp = client.get("/api/contis/nonexistent-uuid")
    assert resp.status_code == 404


def test_reorder_items(client, member_headers):
    song1 = _create_song(client, member_headers, "A곡")
    song2 = _create_song(client, member_headers, "B곡")

    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }, headers=member_headers).json()

    item1 = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song1, "order_num": 1,
    }, headers=member_headers).json()
    item2 = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song2, "order_num": 2,
    }, headers=member_headers).json()

    # 순서 뒤집기
    resp = client.put(f"/api/contis/{conti['id']}/reorder", json={
        "items": [
            {"id": item1["id"], "order_num": 2},
            {"id": item2["id"], "order_num": 1},
        ]
    }, headers=member_headers)
    assert resp.json()["ok"] is True
