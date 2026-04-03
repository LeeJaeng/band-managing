# 데이터 모델

모든 모델은 `api/models.py`에 SQLAlchemy ORM으로 정의되어 있습니다.

## 테이블 관계도

```
teams
 ├── sessions (team_id FK)
 │    ├── session_participants (session_id FK)
 │    ├── grants (session_id FK)
 │    └── broadcasts (session_id FK)
 ├── broadcast_presets (team_id FK)
 ├── invites (team_id FK)        ※ 미사용
 └── team_members (team_id FK)   ※ 미사용
```

## 테이블 상세

### teams
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| name | String | 팀 이름 |
| created_at | DateTime | 생성 시각 |

### sessions
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| team_id | String (FK) | teams.id |
| title | String | 세션 이름 |
| status | String | "ACTIVE" / "INACTIVE" |
| parts | JSON | 파트 목록 (배열) |
| created_at | DateTime | 생성 시각 |

### session_participants
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| session_id | String (FK) | sessions.id |
| user_name | String | 참가자 이름 |
| part | String | 선택한 파트 |
| role | String | "LEADER" / "MEMBER" |
| joined_at | DateTime | 참가 시각 |

### grants (권한)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| session_id | String (FK) | sessions.id |
| user_name | String (Index) | participant_id |
| can_broadcast | Boolean | 브로드캐스트 가능 여부 |
| created_at | DateTime | 생성 시각 |

### broadcast_presets (템플릿)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| team_id | String (FK) | teams.id |
| title | String | 버튼명 (40자 제한) |
| payload | JSON | `{ "text": string }` (120자 제한) |
| created_at | DateTime | 생성 시각 |

### broadcasts (로그)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| session_id | String (FK) | sessions.id |
| sender_id | String | participant_id |
| target | JSON | `{ "all": true }` |
| type | String | "TEXT" |
| payload | JSON | `{ "text": string }` |
| created_at | DateTime | 생성 시각 |

### invites (미사용)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| code | String (PK) | 초대 코드 |
| team_id | String (FK) | teams.id |
| remain | Integer | 남은 초대 횟수 |
| created_at | DateTime | 생성 시각 |

### team_members (미사용)
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | String (PK) | UUID |
| team_id | String (FK) | teams.id |
| name | String | 멤버 이름 |
| part | String | 파트 |
| created_at | DateTime | 생성 시각 |

## 기본 파트 목록

```python
DEFAULT_PARTS = ["보컬", "피아노", "신디", "기타", "베이스", "드럼", "리더", "설교자", "음향", "영상"]
```
