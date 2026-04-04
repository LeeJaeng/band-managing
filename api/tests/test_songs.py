"""곡 CRUD + 레퍼런스 + 악보 테스트."""


def _h(headers):
    """인증 헤더를 TestClient 호출에 맞는 형태로."""
    return headers


def test_create_song(client, member_headers):
    resp = client.post("/api/songs", json={"title": "주만 바라볼찌라", "artist": "마커스", "default_key": "G"}, headers=member_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "주만 바라볼찌라"
    assert "id" in data


def test_create_song_requires_auth(client):
    resp = client.post("/api/songs", json={"title": "곡"})
    assert resp.status_code == 401


def test_list_songs(client, member_headers):
    client.post("/api/songs", json={"title": "곡A"}, headers=member_headers)
    client.post("/api/songs", json={"title": "곡B"}, headers=member_headers)
    resp = client.get("/api/songs")
    assert resp.status_code == 200
    assert resp.json()["total"] == 2


def test_search_songs(client, member_headers):
    client.post("/api/songs", json={"title": "은혜", "lyrics": "놀라운 은혜"}, headers=member_headers)
    client.post("/api/songs", json={"title": "감사"}, headers=member_headers)

    resp = client.get("/api/songs?q=은혜")
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["title"] == "은혜"


def test_get_song_detail(client, member_headers):
    create = client.post("/api/songs", json={"title": "테스트곡", "lyrics": "가사 내용"}, headers=member_headers)
    song_id = create.json()["id"]

    resp = client.get(f"/api/songs/{song_id}")
    assert resp.status_code == 200
    assert resp.json()["title"] == "테스트곡"
    assert resp.json()["lyrics"] == "가사 내용"


def test_update_song(client, member_headers):
    create = client.post("/api/songs", json={"title": "원래제목"}, headers=member_headers)
    song_id = create.json()["id"]

    resp = client.put(f"/api/songs/{song_id}", json={"title": "수정제목"}, headers=member_headers)
    assert resp.status_code == 200
    assert resp.json()["title"] == "수정제목"


def test_delete_song(client, member_headers):
    create = client.post("/api/songs", json={"title": "삭제할곡"}, headers=member_headers)
    song_id = create.json()["id"]

    resp = client.delete(f"/api/songs/{song_id}", headers=member_headers)
    assert resp.json()["ok"] is True

    resp = client.get(f"/api/songs/{song_id}")
    assert resp.status_code == 404


def test_song_not_found(client):
    resp = client.get("/api/songs/nonexistent")
    assert resp.status_code == 404


# ── References ─────────────────────────────────────────

def test_add_reference(client, member_headers):
    create = client.post("/api/songs", json={"title": "테스트"}, headers=member_headers)
    song_id = create.json()["id"]

    resp = client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=abc123",
        "youtube_video_id": "abc123",
        "title": "마커스 - 테스트",
        "key": "G",
    }, headers=member_headers)
    assert resp.status_code == 201
    assert "id" in resp.json()


def test_list_references(client, member_headers):
    create = client.post("/api/songs", json={"title": "테스트"}, headers=member_headers)
    song_id = create.json()["id"]

    client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=vid1",
        "youtube_video_id": "vid1",
        "title": "버전1",
    }, headers=member_headers)
    client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=vid2",
        "youtube_video_id": "vid2",
        "title": "버전2",
    }, headers=member_headers)

    resp = client.get(f"/api/songs/{song_id}/references")
    assert len(resp.json()) == 2


def test_delete_reference(client, member_headers):
    create = client.post("/api/songs", json={"title": "테스트"}, headers=member_headers)
    song_id = create.json()["id"]

    ref = client.post(f"/api/songs/{song_id}/references", json={
        "youtube_url": "https://youtube.com/watch?v=del1",
        "youtube_video_id": "del1",
        "title": "삭제할 레퍼런스",
    }, headers=member_headers)
    ref_id = ref.json()["id"]

    resp = client.delete(f"/api/songs/references/{ref_id}", headers=member_headers)
    assert resp.json()["ok"] is True


# ── Sheets ─────────────────────────────────────────────

def test_upload_sheet(client, member_headers):
    create = client.post("/api/songs", json={"title": "테스트"}, headers=member_headers)
    song_id = create.json()["id"]

    resp = client.post(f"/api/songs/{song_id}/sheets", json={
        "file_url": "/uploads/test.pdf",
        "file_type": "PDF",
    }, headers=member_headers)
    assert resp.status_code == 201


def test_list_sheets(client, member_headers):
    create = client.post("/api/songs", json={"title": "테스트"}, headers=member_headers)
    song_id = create.json()["id"]

    client.post(f"/api/songs/{song_id}/sheets", json={
        "file_url": "/uploads/a.pdf",
        "file_type": "PDF",
    }, headers=member_headers)

    resp = client.get(f"/api/songs/{song_id}/sheets")
    assert len(resp.json()) == 1


# ── Merge ──────────────────────────────────────────────

def test_merge_songs(client, member_headers):
    s1 = client.post("/api/songs", json={"title": "곡 원본"}, headers=member_headers).json()
    s2 = client.post("/api/songs", json={"title": "곡 중복"}, headers=member_headers).json()

    client.post(f"/api/songs/{s2['id']}/references", json={
        "youtube_url": "https://youtube.com/watch?v=merge1",
        "youtube_video_id": "merge1",
        "title": "중복 레퍼런스",
    }, headers=member_headers)

    resp = client.post(f"/api/songs/merge?source_id={s2['id']}&target_id={s1['id']}", headers=member_headers)
    assert resp.json()["ok"] is True

    # source 삭제됨
    assert client.get(f"/api/songs/{s2['id']}").status_code == 404

    # target에 레퍼런스 이동됨
    refs = client.get(f"/api/songs/{s1['id']}/references").json()
    assert len(refs) == 1


# ── Source ────────────────────────────────────────────

def test_member_creates_song_with_user_source(client, member_headers):
    resp = client.post("/api/songs", json={"title": "유저곡"}, headers=member_headers)
    song_id = resp.json()["id"]
    detail = client.get(f"/api/songs/{song_id}").json()
    assert detail["source"] == "USER"


def test_admin_creates_song_with_manual_source(client, admin_headers):
    resp = client.post("/api/songs", json={"title": "관리자곡"}, headers=admin_headers)
    song_id = resp.json()["id"]
    detail = client.get(f"/api/songs/{song_id}").json()
    assert detail["source"] == "MANUAL"


def test_filter_songs_by_source(client, member_headers, admin_headers):
    client.post("/api/songs", json={"title": "유저곡A"}, headers=member_headers)
    client.post("/api/songs", json={"title": "관리자곡A"}, headers=admin_headers)

    user_songs = client.get("/api/songs?source=USER").json()
    assert user_songs["total"] == 1
    assert user_songs["items"][0]["title"] == "유저곡A"

    manual_songs = client.get("/api/songs?source=MANUAL").json()
    assert manual_songs["total"] == 1
    assert manual_songs["items"][0]["title"] == "관리자곡A"
