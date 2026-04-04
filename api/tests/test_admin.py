"""관리자 기능 테스트 — 채널 관리, 검증 큐."""


def test_create_channel(client):
    resp = client.post("/api/admin/channels", json={
        "name": "마커스워십",
        "youtube_channel_url": "https://youtube.com/@markusworship",
        "youtube_channel_id": "UC_markus",
        "trust_level": "HIGH",
    })
    assert resp.status_code == 201
    assert resp.json()["name"] == "마커스워십"


def test_list_channels(client):
    client.post("/api/admin/channels", json={
        "name": "마커스워십",
        "youtube_channel_url": "https://youtube.com/@markus",
        "youtube_channel_id": "UC_markus",
    })
    client.post("/api/admin/channels", json={
        "name": "어노인팅",
        "youtube_channel_url": "https://youtube.com/@anointing",
        "youtube_channel_id": "UC_anointing",
    })

    resp = client.get("/api/admin/channels")
    assert len(resp.json()) == 2


def test_duplicate_channel(client):
    client.post("/api/admin/channels", json={
        "name": "마커스",
        "youtube_channel_url": "https://youtube.com/@markus",
        "youtube_channel_id": "UC_dup",
    })

    resp = client.post("/api/admin/channels", json={
        "name": "마커스2",
        "youtube_channel_url": "https://youtube.com/@markus2",
        "youtube_channel_id": "UC_dup",
    })
    assert resp.status_code == 409


def test_update_channel(client):
    ch = client.post("/api/admin/channels", json={
        "name": "테스트채널",
        "youtube_channel_url": "https://youtube.com/@test",
        "youtube_channel_id": "UC_test",
    }).json()

    resp = client.put(f"/api/admin/channels/{ch['id']}", json={
        "is_active": False,
    })
    assert resp.json()["ok"] is True


def test_delete_channel(client):
    ch = client.post("/api/admin/channels", json={
        "name": "삭제채널",
        "youtube_channel_url": "https://youtube.com/@del",
        "youtube_channel_id": "UC_del",
    }).json()

    resp = client.delete(f"/api/admin/channels/{ch['id']}")
    assert resp.json()["ok"] is True


# ── Review Queue ───────────────────────────────────────

def test_review_queue_approve_new_song(client, db):
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
    })
    assert resp.json()["ok"] is True
    assert "song_id" in resp.json()


def test_review_queue_approve_existing_song(client, db):
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
    })
    assert resp.json()["ok"] is True
    assert resp.json()["song_id"] == song.id


def test_review_queue_reject(client, db):
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

    resp = client.post(f"/api/admin/review/{rq.id}/reject")
    assert resp.json()["ok"] is True


def test_crawl_logs_empty(client):
    resp = client.get("/api/admin/crawl/logs")
    assert resp.status_code == 200
    assert resp.json() == []
