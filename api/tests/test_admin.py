"""관리자 기능 테스트 — 채널 관리, 검증 큐."""


def test_create_channel(client, admin_headers):
    resp = client.post("/api/admin/channels", json={
        "name": "마커스워십",
        "youtube_channel_url": "https://youtube.com/@markusworship",
        "youtube_channel_id": "UC_markus",
        "trust_level": "HIGH",
    }, headers=admin_headers)
    assert resp.status_code == 201
    assert resp.json()["name"] == "마커스워십"


def test_admin_requires_auth(client):
    resp = client.get("/api/admin/channels")
    assert resp.status_code == 401


def test_admin_requires_admin_role(client, member_headers):
    resp = client.get("/api/admin/channels", headers=member_headers)
    assert resp.status_code == 403


def test_list_channels(client, admin_headers):
    client.post("/api/admin/channels", json={
        "name": "마커스워십",
        "youtube_channel_url": "https://youtube.com/@markus",
        "youtube_channel_id": "UC_markus",
    }, headers=admin_headers)
    client.post("/api/admin/channels", json={
        "name": "어노인팅",
        "youtube_channel_url": "https://youtube.com/@anointing",
        "youtube_channel_id": "UC_anointing",
    }, headers=admin_headers)

    resp = client.get("/api/admin/channels", headers=admin_headers)
    assert len(resp.json()) == 2


def test_duplicate_channel(client, admin_headers):
    client.post("/api/admin/channels", json={
        "name": "마커스",
        "youtube_channel_url": "https://youtube.com/@markus",
        "youtube_channel_id": "UC_dup",
    }, headers=admin_headers)

    resp = client.post("/api/admin/channels", json={
        "name": "마커스2",
        "youtube_channel_url": "https://youtube.com/@markus2",
        "youtube_channel_id": "UC_dup",
    }, headers=admin_headers)
    assert resp.status_code == 409


def test_update_channel(client, admin_headers):
    ch = client.post("/api/admin/channels", json={
        "name": "테스트채널",
        "youtube_channel_url": "https://youtube.com/@test",
        "youtube_channel_id": "UC_test",
    }, headers=admin_headers).json()

    resp = client.put(f"/api/admin/channels/{ch['id']}", json={
        "is_active": False,
    }, headers=admin_headers)
    assert resp.json()["ok"] is True


def test_delete_channel(client, admin_headers):
    ch = client.post("/api/admin/channels", json={
        "name": "삭제채널",
        "youtube_channel_url": "https://youtube.com/@del",
        "youtube_channel_id": "UC_del",
    }, headers=admin_headers).json()

    resp = client.delete(f"/api/admin/channels/{ch['id']}", headers=admin_headers)
    assert resp.json()["ok"] is True


# ── Review Queue ───────────────────────────────────────

def test_review_queue_approve_new_song(client, admin_headers, db):
    """검증 큐 항목 승인 → 새 곡 생성."""
    from models import ReviewQueue, CrawlChannel

    ch = CrawlChannel(
        name="테스트채널",
        youtube_channel_url="https://youtube.com/@test",
        youtube_channel_id="UC_review_test",
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    rq = ReviewQueue(
        youtube_video_id="review_vid1",
        youtube_url="https://youtube.com/watch?v=review_vid1",
        video_title="마커스 - 은혜 (Live)",
        channel_id=ch.id,
        parsed_song_title="은혜",
    )
    db.add(rq)
    db.commit()
    db.refresh(rq)

    resp = client.post(f"/api/admin/review/{rq.id}/approve", json={
        "song_title": "은혜",
    }, headers=admin_headers)
    assert resp.json()["ok"] is True
    assert "song_id" in resp.json()


def test_review_queue_approve_existing_song(client, admin_headers, db):
    """검증 큐 항목 승인 → 기존 곡에 레퍼런스 추가."""
    from models import ReviewQueue, CrawlChannel, Song

    ch = CrawlChannel(
        name="채널",
        youtube_channel_url="https://youtube.com/@ch",
        youtube_channel_id="UC_exist_test",
    )
    db.add(ch)
    song = Song(title="감사")
    db.add(song)
    db.commit()
    db.refresh(ch)
    db.refresh(song)

    rq = ReviewQueue(
        youtube_video_id="exist_vid1",
        youtube_url="https://youtube.com/watch?v=exist_vid1",
        video_title="감사 - 어노인팅",
        channel_id=ch.id,
        parsed_song_title="감사",
        suggested_song_id=song.id,
    )
    db.add(rq)
    db.commit()
    db.refresh(rq)

    resp = client.post(f"/api/admin/review/{rq.id}/approve", json={
        "song_id": song.id,
    }, headers=admin_headers)
    assert resp.json()["ok"] is True
    assert resp.json()["song_id"] == song.id


def test_review_queue_reject(client, admin_headers, db):
    from models import ReviewQueue, CrawlChannel

    ch = CrawlChannel(
        name="채널",
        youtube_channel_url="https://youtube.com/@ch",
        youtube_channel_id="UC_reject_test",
    )
    db.add(ch)
    db.commit()
    db.refresh(ch)

    rq = ReviewQueue(
        youtube_video_id="reject_vid1",
        youtube_url="https://youtube.com/watch?v=reject_vid1",
        video_title="관련없는 영상",
        channel_id=ch.id,
    )
    db.add(rq)
    db.commit()
    db.refresh(rq)

    resp = client.post(f"/api/admin/review/{rq.id}/reject", headers=admin_headers)
    assert resp.json()["ok"] is True


def test_crawl_logs_empty(client, admin_headers):
    resp = client.get("/api/admin/crawl/logs", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_update_song_source(client, admin_headers, member_headers):
    # 일반 유저가 곡 등록 → source=USER
    resp = client.post("/api/songs", json={"title": "유저곡"}, headers=member_headers)
    song_id = resp.json()["id"]
    assert client.get(f"/api/songs/{song_id}").json()["source"] == "USER"

    # 관리자가 승인 → source=MANUAL
    resp = client.put(f"/api/admin/songs/{song_id}/source", json={"source": "MANUAL"}, headers=admin_headers)
    assert resp.json()["ok"] is True
    assert client.get(f"/api/songs/{song_id}").json()["source"] == "MANUAL"


def test_update_song_source_requires_admin(client, member_headers):
    resp = client.post("/api/songs", json={"title": "곡"}, headers=member_headers)
    song_id = resp.json()["id"]
    resp = client.put(f"/api/admin/songs/{song_id}/source", json={"source": "MANUAL"}, headers=member_headers)
    assert resp.status_code == 403
