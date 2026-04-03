# API 엔드포인트

모든 엔드포인트는 `api/main.py`에 정의되어 있습니다.

## 헬스 체크

```
GET /health
→ { "ok": true, "service": "band-managing-api" }
```

## 팀

```
POST /teams
Body: { "name": string }
→ { "id": string, "name": string }
```

## 세션

```
POST /sessions
Body: { "team_id": string, "title": string, "parts"?: string[] }
→ { "id": string, "team_id": string, "title": string, "status": "ACTIVE", "parts": string[] }

GET /sessions/{session_id}
→ 세션 상세 정보 (parts 포함)

POST /sessions/{session_id}/join
Body: { "user_name": string, "part"?: string }
→ { "participant": { "id": string, "user_name": string, "part": string, "role": "LEADER"|"MEMBER" } }
  * 첫 번째 참가자는 자동으로 LEADER

GET /sessions/{session_id}/participants
→ SessionParticipant[]
```

## 권한

```
POST /sessions/{session_id}/broadcast-permissions
Body: { "participant_id": string, "can_broadcast": boolean }
→ { "ok": true }
  * WebSocket으로 PERMISSION_UPDATED 브로드캐스트

GET /sessions/{session_id}/broadcast-permissions
→ [{ "participant_id": string, "can_broadcast": boolean }]
```

## 프리셋

```
GET /teams/{team_id}/presets
→ [{ "id": string, "title": string, "payload": { "text"?: string } }]

POST /teams/{team_id}/presets
Body: { "team_id": string, "title": string, "text"?: string }
→ { "id": string, "title": string, "payload": {...} }
  * title: 40자 제한, text: 120자 제한

PUT /presets/{preset_id}
Body: { "title"?: string, "text"?: string }
→ 수정된 프리셋

DELETE /presets/{preset_id}
→ { "ok": true }
  * WebSocket으로 PRESETS_UPDATED 브로드캐스트
```

## 브로드캐스트

```
POST /broadcasts
Body: {
  "session_id": string,
  "sender_id": string,
  "target": { "all": true },
  "type": "TEXT",
  "payload": { "text": string }
}
→ { "id": string, "created_at": string }
  * LEADER: 항상 가능
  * MEMBER: grants 테이블에서 can_broadcast=true인 경우만 가능 (아니면 403)
  * WebSocket으로 BROADCAST 이벤트 전송
```

## WebSocket

```
WS /ws

클라이언트 → 서버:
  { "type": "JOIN_SESSION", "session_id": string, "user": { "id": string, "name": string, "part"?: string } }

서버 → 클라이언트:
  { "type": "JOINED" }                          — 입장 확인
  { "type": "USER_JOINED", "data": {...} }      — 다른 유저 입장 알림
  { "type": "BROADCAST", "data": {...} }         — 브로드캐스트 수신
  { "type": "PERMISSION_UPDATED", "data": {...} } — 권한 변경 알림
  { "type": "PRESETS_UPDATED", "data": {...} }   — 프리셋 변경 알림
  { "type": "ERROR", "message": string }         — 에러
```
