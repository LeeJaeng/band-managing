"""크롤러 단위 테스트 — 제목 파싱, 키 감지."""

from crawler import parse_song_title, detect_key


def test_parse_simple():
    assert parse_song_title("주만 바라볼찌라") == "주만 바라볼찌라"


def test_parse_with_brackets():
    assert parse_song_title("[마커스 4집] 주만 바라볼찌라") == "주만 바라볼찌라"


def test_parse_with_pipe():
    assert parse_song_title("주만 바라볼찌라 | 마커스워십") == "주만 바라볼찌라"


def test_parse_with_official():
    assert parse_song_title("은혜 (Official Video)") == "은혜"


def test_parse_with_live():
    result = parse_song_title("감사 (Live Worship)")
    assert "감사" in result


def test_parse_with_dash_year():
    result = parse_song_title("찬양 - 2024 마커스워십 라이브")
    # "- 2024" 이후 제거됨
    assert "찬양" in result


def test_detect_key_colon():
    assert detect_key("Key: G") == "G"


def test_detect_key_in_title():
    assert detect_key("주만 바라볼찌라 | Keys: Am") == "Am"


def test_detect_key_sharp():
    assert detect_key("key: F#m") == "F#m"


def test_detect_key_flat():
    assert detect_key("Key Bb") == "Bb"


def test_detect_key_none():
    assert detect_key("찬양곡 영상") is None


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
