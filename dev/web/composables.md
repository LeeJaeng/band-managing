# 컴포저블 (Composables)

Vue 3 Composition API 기반 재사용 로직. `web/composables/`에 위치.

## useWs(sessionId, user)

WebSocket 연결 관리.

**파라미터**
- `sessionId`: 세션 ID
- `user`: `{ id, name, part }` 사용자 정보

**반환값**
- `events: Ref<any[]>` — 수신된 이벤트 (최신 50개 유지)
- `connected: Ref<boolean>` — 연결 상태
- `lastMessageAt: Ref<number>` — 마지막 메시지 타임스탬프

**동작**
- 마운트 시 WebSocket 연결
- 연결 후 자동으로 `JOIN_SESSION` 메시지 전송
- 언마운트 시 연결 해제

## useSessionState()

localStorage 기반 세션 상태 관리.

**타입**
```typescript
interface StoredSession {
  sid: string
  pid: string
  name: string
  part?: string
  role?: string
  joinedAt: number
}
```

**반환값**
- `saveActiveSession(session)` — 세션 저장
- `loadActiveSession()` — 세션 복구 (없으면 null)
- `clearActiveSession()` — 세션 삭제
- `getOverlaySeconds()` — 오버레이 표시 시간 (초)
- `setOverlaySeconds(n)` — 오버레이 표시 시간 설정

## useClipboard()

클립보드 복사 유틸.

**반환값**
- `copyText(value: string): Promise<boolean>` — 텍스트 복사
  - Clipboard API 우선 사용
  - 미지원 시 `document.execCommand('copy')` 폴백
