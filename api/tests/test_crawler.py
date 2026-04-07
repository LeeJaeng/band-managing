"""크롤러 단위 테스트 — 제목 파싱, 키 감지, 세트리스트/가사/악보 파싱."""

from types import SimpleNamespace

from crawler import (
    parse_song_title,
    detect_key,
    should_skip_video,
    parse_setlist_description,
    parse_lyrics_from_description,
    parse_sheet_urls,
    _augment_song_keys,
    _ts_to_seconds,
)


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


# ── 팀 이름 제거 ──

def test_parse_remove_team_name_dash():
    result = parse_song_title("거룩 영원히 (Holy Forever) - 마커스워십 𝑳𝒊𝒗𝒆 𝑪𝒍𝒊𝒑")
    assert "마커스" not in result
    assert "거룩 영원히" in result


def test_parse_remove_team_name():
    result = parse_song_title("주만 바라볼찌라 마커스워십")
    assert "마커스" not in result
    assert "주만 바라볼찌라" in result


def test_parse_remove_anointing():
    result = parse_song_title("은혜 - 어노인팅")
    assert "어노인팅" not in result
    assert "은혜" in result


# ── 합쳐진 곡 필터 ──

def test_skip_plus_songs():
    assert should_skip_video("찬양A + 찬양B") is True


def test_skip_medley():
    assert should_skip_video("찬양 메들리 2024") is True


def test_skip_worship_set():
    assert should_skip_video("Worship Set - Sunday") is True


def test_not_skip_normal():
    assert should_skip_video("은혜 (Grace)") is False


# ── 강화된 detect_key (한국어 / 장조) ──

def test_detect_key_korean_label():
    assert detect_key("키: G") == "G"


def test_detect_key_jangjo():
    assert detect_key("이 곡은 G장조입니다") == "G"


def test_detect_key_unicode_flat():
    assert detect_key("Key: B\u266d") == "Bb"


# ── 세트리스트 파싱 ──

def test_setlist_basic_parens_key():
    desc = "00:00 주님 찾아오셨네 (Key: G)\n05:30 당신은 나의 왕 (Key: Am)"
    items = parse_setlist_description(desc)
    assert len(items) == 2
    assert items[0]["title"] == "주님 찾아오셨네"
    assert items[0]["key"] == "G"
    assert items[0]["ts_seconds"] == 0
    assert items[1]["key"] == "Am"
    assert items[1]["ts_seconds"] == 330


def test_setlist_hms_timestamp():
    desc = "1:23:45 곡명 - Am"
    items = parse_setlist_description(desc)
    assert len(items) == 1
    assert items[0]["ts_seconds"] == 5025
    assert items[0]["key"] == "Am"


def test_setlist_pipe_key():
    desc = "10:00 주 영광 받으소서 | key Bb"
    items = parse_setlist_description(desc)
    assert len(items) == 1
    assert items[0]["key"] == "Bb"
    assert "주 영광 받으소서" in items[0]["title"]


def test_setlist_jangjo():
    desc = "20:00 하나님 한 분만으로 G장조"
    items = parse_setlist_description(desc)
    assert len(items) == 1
    assert items[0]["key"] == "G"


def test_setlist_skip_keyless_lines():
    desc = "00:00 인트로\n02:00 곡명 (G)\n03:00 멘트"
    items = parse_setlist_description(desc)
    assert len(items) == 1
    assert items[0]["title"] == "곡명"


def test_setlist_dedup():
    desc = "00:00 곡 A (G)\n10:00 곡 A (G)"
    items = parse_setlist_description(desc)
    assert len(items) == 1


def test_ts_to_seconds():
    assert _ts_to_seconds("00:00") == 0
    assert _ts_to_seconds("05:30") == 330
    assert _ts_to_seconds("1:02:03") == 3723


# ── _augment_song_keys ──

def _make_song(default_key=None, keys=None):
    return SimpleNamespace(default_key=default_key, keys=keys)


def test_augment_keys_first_set():
    song = _make_song()
    assert _augment_song_keys(song, "G") is True
    assert song.default_key == "G"
    assert song.keys == ["G"]


def test_augment_keys_no_duplicate():
    song = _make_song(default_key="G", keys=["G"])
    assert _augment_song_keys(song, "G") is False
    assert song.keys == ["G"]


def test_augment_keys_keeps_default():
    song = _make_song(default_key="G", keys=["G"])
    assert _augment_song_keys(song, "Am") is True
    assert song.default_key == "G"  # 보존
    assert "Am" in song.keys


# ── 가사 파싱 ──

def test_lyrics_explicit_marker():
    desc = (
        "곡 소개\n\n"
        "가사:\n"
        "주님의 사랑이\n"
        "내 안에 가득 차고\n"
        "찬양으로 영광을\n"
        "주께 올려드리네\n"
        "할렐루야 주를 찬양\n"
        "거룩하신 주님\n\n"
        "https://example.com"
    )
    lyrics = parse_lyrics_from_description(desc)
    assert lyrics is not None
    assert "주님의 사랑이" in lyrics
    assert "https" not in lyrics


def test_lyrics_heuristic_korean_block():
    desc = (
        "찬양 영상입니다\n"
        "주님 한 분 만으로 충분해\n"
        "내 영혼이 주를 찬양해\n"
        "거룩하신 주의 이름\n"
        "온 땅이 주를 경배해\n"
        "영원히 주를 사랑해\n"
        "할렐루야 아멘\n"
    )
    lyrics = parse_lyrics_from_description(desc)
    assert lyrics is not None
    assert "주님 한 분" in lyrics


def test_lyrics_url_only_returns_none():
    desc = "https://youtube.com/watch?v=abc\nhttps://instagram.com/foo"
    assert parse_lyrics_from_description(desc) is None


def test_lyrics_too_short_returns_none():
    desc = "가사:\n짧은\n가사"
    assert parse_lyrics_from_description(desc) is None


# ── 악보 링크 파싱 ──

def test_sheet_pdf_url():
    desc = "악보 다운로드: https://example.com/sheet/song.pdf"
    urls = parse_sheet_urls(desc)
    assert "https://example.com/sheet/song.pdf" in urls


def test_sheet_drive_with_keyword():
    desc = "악보: https://drive.google.com/file/d/abcd/view"
    urls = parse_sheet_urls(desc)
    assert len(urls) == 1


def test_sheet_drive_without_keyword_skipped():
    desc = "참고 영상: https://drive.google.com/file/d/abcd/view"
    urls = parse_sheet_urls(desc)
    assert urls == []


def test_sheet_skip_normal_urls():
    desc = "https://instagram.com/team\nhttps://youtube.com/@team"
    assert parse_sheet_urls(desc) == []


def test_sheet_hint_in_path():
    desc = "https://mssaint.com/song/123"
    urls = parse_sheet_urls(desc)
    assert len(urls) == 1


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
