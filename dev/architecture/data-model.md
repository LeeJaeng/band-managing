# 데이터 모델

모든 모델은 `api/models.py`에 SQLAlchemy ORM으로 정의.

## 테이블 관계도

```
songs
 ├── song_references (song_id FK, 1:N)
 │    └── crawl_channels (channel_id FK)
 ├── song_sheets (song_id FK, 1:N)
 │    └── song_references (reference_id FK, nullable)
 └── conti_items (song_id FK)
      └── contis (conti_id FK)

crawl_channels
 ├── song_references (channel_id FK)
 ├── crawl_logs (channel_id FK)
 └── review_queue (channel_id FK)
```

## 테이블 상세

### songs (곡)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| title | String(200) | 곡 제목 |
| artist | String(200), nullable | 원곡자 (UI에서 미사용) |
| default_key | String(10), nullable | 기본 키 (레거시) |
| keys | JSON, nullable | 키 목록 ["A", "G", "Bb"] |
| tempo | String(10), nullable | 빠르기 (FAST/SLOW, null=미분류) |
| lyrics | Text, nullable | 가사/송폼 |
| created_at | DateTime | |
| updated_at | DateTime | |

### song_references (레퍼런스)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| song_id | UUID (FK) | songs.id, CASCADE |
| channel_id | UUID (FK), nullable | crawl_channels.id |
| youtube_url | String(500) | |
| youtube_video_id | String(20), unique | |
| title | String(500) | 영상 제목 |
| thumbnail_url | String(500), nullable | |
| key | String(10), nullable | 해당 버전의 키 |
| trust_level | String(10) | HIGH/MEDIUM/LOW |
| source | String(10) | CRAWL/MANUAL |
| created_at | DateTime | |

### song_sheets (악보)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| song_id | UUID (FK) | songs.id, CASCADE |
| reference_id | UUID (FK), nullable | 어떤 편곡 기준 |
| file_url | String(500) | |
| file_type | String(10) | PDF/IMAGE |
| uploaded_by | String(100), nullable | |
| created_at | DateTime | |

### contis (콘티)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| date | Date | 예배 날짜 |
| service_name | String(100) | 예배명 |
| author | String(100) | 작성자 |
| status | String(20) | DRAFT/CONFIRMED |
| created_at, updated_at | DateTime | |

### conti_items (콘티 항목)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| conti_id | UUID (FK) | contis.id, CASCADE |
| song_id | UUID (FK) | songs.id |
| order_num | Integer | 순서 |
| slot_label | String(50) | "1번곡", "기도곡" 등 |
| use_key | String(10), nullable | 사용할 키 |
| reference_id | UUID (FK), nullable | 선택한 레퍼런스 |
| memo | Text, nullable | |
| created_at | DateTime | |

### crawl_channels (크롤링 채널)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| name | String(200) | 사역팀 이름 |
| youtube_channel_url | String(500) | |
| youtube_channel_id | String(50), unique | UC... |
| trust_level | String(10) | HIGH/MEDIUM/LOW |
| is_active | Boolean | |
| last_crawled_at | DateTime, nullable | |
| created_at | DateTime | |

### crawl_logs (크롤링 로그)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| channel_id | UUID (FK) | |
| status | String(20) | SUCCESS/FAILED/RUNNING |
| videos_found | Integer | |
| songs_added | Integer | |
| refs_added | Integer | |
| error_message | Text, nullable | |
| started_at, finished_at | DateTime | |

### review_queue (검증 큐)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| youtube_video_id | String(20) | |
| youtube_url | String(500) | |
| video_title | String(500) | |
| channel_id | UUID (FK) | |
| parsed_song_title | String(200), nullable | 파싱된 곡 제목 |
| suggested_song_id | UUID (FK), nullable | 매칭 후보 곡 |
| status | String(20) | PENDING/APPROVED/REJECTED |
| created_at, reviewed_at | DateTime | |
