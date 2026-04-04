"""콘티 CRUD + 항목 관리 테스트."""


def _create_song(client, title="테스트곡"):
    return client.post("/api/songs", json={"title": title}).json()["id"]


def test_create_conti(client):
    resp = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "청년예배",
        "author": "인도자",
    })
    assert resp.status_code == 201
    assert resp.json()["service_name"] == "청년예배"


def test_list_contis(client):
    client.post("/api/contis", json={"date": "2026-04-06", "service_name": "청년예배", "author": "A"})
    client.post("/api/contis", json={"date": "2026-04-13", "service_name": "주일2부", "author": "B"})

    resp = client.get("/api/contis")
    assert resp.json()["total"] == 2


def test_get_conti_detail(client):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "청년예배",
        "author": "인도자",
    }).json()

    resp = client.get(f"/api/contis/{conti['id']}")
    assert resp.status_code == 200
    assert resp.json()["service_name"] == "청년예배"
    assert resp.json()["items"] == []


def test_update_conti(client):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "원래이름",
        "author": "인도자",
    }).json()

    resp = client.put(f"/api/contis/{conti['id']}", json={"service_name": "수정이름"})
    assert resp.json()["service_name"] == "수정이름"


def test_delete_conti(client):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "삭제할콘티",
        "author": "인도자",
    }).json()

    resp = client.delete(f"/api/contis/{conti['id']}")
    assert resp.json()["ok"] is True

    assert client.get(f"/api/contis/{conti['id']}").status_code == 404


def test_confirm_conti(client):
    conti = client.post("/api/contis", json={
        "date": "2026-04-06",
        "service_name": "확정할콘티",
        "author": "인도자",
    }).json()

    resp = client.put(f"/api/contis/{conti['id']}/confirm")
    assert resp.json()["status"] == "CONFIRMED"


# ── Conti Items ────────────────────────────────────────

def test_add_item(client):
    song_id = _create_song(client)
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }).json()

    resp = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id,
        "order_num": 1,
        "slot_label": "1번곡",
        "use_key": "A",
    })
    assert resp.status_code == 201


def test_conti_with_items(client):
    song1 = _create_song(client, "찬양1")
    song2 = _create_song(client, "찬양2")

    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }).json()

    client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song1, "order_num": 1, "slot_label": "1번곡",
    })
    client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song2, "order_num": 2, "slot_label": "기도곡",
    })

    detail = client.get(f"/api/contis/{conti['id']}").json()
    assert len(detail["items"]) == 2
    assert detail["items"][0]["song"]["title"] == "찬양1"
    assert detail["items"][1]["slot_label"] == "기도곡"


def test_update_item(client):
    song_id = _create_song(client)
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }).json()

    item = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id, "order_num": 1, "slot_label": "1번곡",
    }).json()

    resp = client.put(f"/api/contis/items/{item['id']}", json={
        "use_key": "Bb",
        "memo": "인트로 없이",
    })
    assert resp.json()["ok"] is True


def test_delete_item(client):
    song_id = _create_song(client)
    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }).json()

    item = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song_id, "order_num": 1,
    }).json()

    resp = client.delete(f"/api/contis/items/{item['id']}")
    assert resp.json()["ok"] is True

    detail = client.get(f"/api/contis/{conti['id']}").json()
    assert len(detail["items"]) == 0


def test_reorder_items(client):
    song1 = _create_song(client, "A곡")
    song2 = _create_song(client, "B곡")

    conti = client.post("/api/contis", json={
        "date": "2026-04-06", "service_name": "테스트", "author": "A",
    }).json()

    item1 = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song1, "order_num": 1,
    }).json()
    item2 = client.post(f"/api/contis/{conti['id']}/items", json={
        "song_id": song2, "order_num": 2,
    }).json()

    # 순서 뒤집기
    resp = client.put(f"/api/contis/{conti['id']}/reorder", json={
        "items": [
            {"id": item1["id"], "order_num": 2},
            {"id": item2["id"], "order_num": 1},
        ]
    })
    assert resp.json()["ok"] is True
