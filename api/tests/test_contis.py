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

    resp = client.get("/api/contis")
    assert resp.json()["total"] == 2


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
