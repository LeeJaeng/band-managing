"""곡 CRUD + 레퍼런스 + 악보 테스트."""


def test_create_song(client):
    resp = client.post("/api/songs", json={"title": "주만 바라볼찌라", "artist": "마커스", "default_key": "G"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "주만 바라볼찌라"
    assert "id" in data


def test_list_songs(client):
    client.post("/api/songs", json={"title": "곡A"})
    client.post("/api/songs", json={"title": "곡B"})
    resp = client.get("/api/songs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_search_songs(client):
    client.post("/api/songs", json={"title": "은혜", "lyrics": "놀라운 은혜"})
    client.post("/api/songs", json={"title": "감사"})

    resp = client.get("/api/songs?q=은혜")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "은혜"


def test_get_song_detail(client):
    create = client.post("/api/songs", json={"title": "테스트곡", "lyrics": "가사 내용"})
    song_id = create.json()["id"]

    resp = client.get(f"/api/songs/{song_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "테스트곡"
    assert resp.json()["lyrics"] == "가사 내용"


def test_update_song(client):
    create = client.post("/api/songs", json={"title": "원래제목"})
    song_id = create.json()["id"]

    resp = client.put(f"/api/songs/{song_id}", json={"title": "수정제목"})
    assert resp.status_code == 200
    assert resp.json()["title"] == "수정제목"


def test_delete_song(client):
    create = client.post("/api/songs", json={"title": "삭제할곡"})
    song_id = create.json()["id"]

    resp = client.delete(f"/api/songs/{song_id}")
    assert resp.json()["ok"] is True

    resp = client.get(f"/api/songs/{song_id}")
    assert resp.status_code == 404


def test_song_not_found(client):
    resp = client.get("/api/songs/nonexistent")
    assert resp.status_code == 404


# ── References ─────────────────────────────────────────

def test_add_reference(client):
    create = client.post("/api/songs", json={"title": "테스트"})
    song_id = create.json()["id"]

    resp = client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=abc123",
        "youtube_video_id": "abc123",
        "title": "마커스 - 테스트",
        "key": "G",
    })
    assert resp.status_code == 201
    assert "id" in resp.json()


def test_list_references(client):
    create = client.post("/api/songs", json={"title": "테스트"})
    song_id = create.json()["id"]

    client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=vid1",
        "youtube_video_id": "vid1",
        "title": "버전1",
    })
    client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=vid2",
        "youtube_video_id": "vid2",
        "title": "버전2",
    })

    resp = client.get(f"/api/songs/{song_id}/references")
    assert len(resp.json()) == 2


def test_delete_reference(client):
    create = client.post("/api/songs", json={"title": "테스트"})
    song_id = create.json()["id"]

    ref = client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=del1",
        "youtube_video_id": "del1",
        "title": "삭제할 레퍼런스",
    })
    ref_id = ref.json()["id"]

    resp = client.delete(f"/api/songs/references/{ref_id}")
    assert resp.json()["ok"] is True


# ── Sheets ─────────────────────────────────────────────

def test_upload_sheet(client):
    create = client.post("/api/songs", json={"title": "테스트"})
    song_id = create.json()["id"]

    resp = client.post(f"/api/songs/{song_id}/sheets", json={
        "file_url": "/uploads/test.pdf",
        "file_type": "PDF",
    })
    assert resp.status_code == 201


def test_list_sheets(client):
    create = client.post("/api/songs", json={"title": "테스트"})
    song_id = create.json()["id"]

    client.post(f"/api/songs/{song_id}/sheets", json={
        "file_url": "/uploads/a.pdf",
        "file_type": "PDF",
    })

    resp = client.get(f"/api/songs/{song_id}/sheets")
    assert len(resp.json()) == 1


# ── Merge ──────────────────────────────────────────────

def test_merge_songs(client):
    s1 = client.post("/api/songs", json={"title": "곡 원본"}).json()
    s2 = client.post("/api/songs", json={"title": "곡 중복"}).json()

    client.post(f"/api/songs/{s2['id']}/references", json={
        "youtube_url": "https://youtube.com/watch?v=merge1",
        "youtube_video_id": "merge1",
        "title": "중복 레퍼런스",
    })

    resp = client.post(f"/api/songs/merge?source_id={s2['id']}&target_id={s1['id']}")
    assert resp.json()["ok"] is True

    # source 삭제됨
    assert client.get(f"/api/songs/{s2['id']}").status_code == 404

    # target에 레퍼런스 이동됨
    refs = client.get(f"/api/songs/{s1['id']}/references").json()
    assert len(refs) == 1
