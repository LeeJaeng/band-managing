# 데이터 모델

## 테이블 관계도

```
songs (곡)
 ├── song_references (레퍼런스, 복수)
 │    └── crawl_channels (사역팀 채널) 연결
 ├── song_sheets (악보, 복수)
 │    └── song_references 연결 (어떤 편곡 기준인지)
 └── conti_items (콘티 항목)
      └── contis (콘티)

crawl_channels (크롤링 대상 채널)
 └── song_references (수집된 레퍼런스)

contis (콘티)
 └── conti_items (콘티 항목, 순서)
      └── songs (곡) 연결
```

## 테이블 상세

### songs (곡)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| title | String | 곡 제목 |
| artist | String (nullable) | 원곡자/작곡자 |
| default_key | String (nullable) | 기본 키 |
| lyrics | Text (nullable) | 가사 |
| created_at | DateTime | |
| updated_at | DateTime | |

### song_references (레퍼런스)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| song_id | UUID (FK) | songs.id |
| channel_id | UUID (FK, nullable) | crawl_channels.id |
| youtube_url | String | 유튜브 URL |
| youtube_video_id | String (unique) | 유튜브 영상 ID |
| title | String | 영상 제목 |
| thumbnail_url | String (nullable) | 썸네일 |
| key | String (nullable) | 해당 버전의 키 |
| trust_level | String | "HIGH" / "MEDIUM" / "LOW" (채널 기반) |
| source | String | "CRAWL" / "MANUAL" |
| created_at | DateTime | |

### song_sheets (악보)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| song_id | UUID (FK) | songs.id |
| reference_id | UUID (FK, nullable) | song_references.id (어떤 편곡용) |
| file_url | String | 파일 경로/URL |
| file_type | String | "PDF" / "IMAGE" |
| uploaded_by | String (nullable) | 업로드자 |
| created_at | DateTime | |

### contis (콘티)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| date | Date | 예배 날짜 |
| service_name | String | 예배명 ("청년예배", "주일 2부" 등) |
| author | String | 작성자 |
| status | String | "DRAFT" / "CONFIRMED" |
| created_at | DateTime | |
| updated_at | DateTime | |

### conti_items (콘티 항목)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| conti_id | UUID (FK) | contis.id |
| song_id | UUID (FK) | songs.id |
| order_num | Integer | 순서 |
| slot_label | String | 슬롯 라벨 ("1번곡", "기도곡", "헌금송" 등) |
| use_key | String (nullable) | 사용할 키 (원키와 다를 수 있음) |
| reference_id | UUID (FK, nullable) | 선택한 레퍼런스 |
| memo | Text (nullable) | 메모 |
| created_at | DateTime | |

### crawl_channels (크롤링 대상 채널)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| name | String | 사역팀/채널 이름 |
| youtube_channel_url | String | 유튜브 채널 URL |
| youtube_channel_id | String (unique) | 유튜브 채널 ID |
| trust_level | String | "HIGH" / "MEDIUM" / "LOW" |
| is_active | Boolean | 활성화 여부 |
| last_crawled_at | DateTime (nullable) | 마지막 크롤링 시각 |
| created_at | DateTime | |

### crawl_logs (크롤링 로그)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| channel_id | UUID (FK) | crawl_channels.id |
| status | String | "SUCCESS" / "FAILED" / "PARTIAL" |
| videos_found | Integer | 발견 영상 수 |
| songs_added | Integer | 신규 등록 곡 수 |
| refs_added | Integer | 신규 레퍼런스 수 |
| error_message | Text (nullable) | 에러 메시지 |
| started_at | DateTime | |
| finished_at | DateTime | |

### review_queue (검증 큐)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | UUID (PK) | |
| youtube_video_id | String | 영상 ID |
| youtube_url | String | |
| video_title | String | 영상 제목 |
| channel_id | UUID (FK) | crawl_channels.id |
| parsed_song_title | String (nullable) | 파싱된 곡 제목 |
| suggested_song_id | UUID (FK, nullable) | 매칭 후보 곡 |
| status | String | "PENDING" / "APPROVED" / "REJECTED" |
| created_at | DateTime | |
| reviewed_at | DateTime (nullable) | |
