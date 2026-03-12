// web/composables/useSessionState.ts
export type StoredSession = {
  sid: string;
  pid: string;
  name: string;
  part?: string;
  role?: string; // LEADER/MEMBER
  joinedAt: number;
};

const KEY = "bm_active_session_v1";
const OVERLAY_KEY = "bm_overlay_seconds_v1";

export function saveActiveSession(s: StoredSession) {
  localStorage.setItem(KEY, JSON.stringify(s));
}

export function loadActiveSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (!parsed?.sid || !parsed?.pid || !parsed?.name) return null;
    return parsed as StoredSession;
  } catch {
    return null;
  }
}

export function clearActiveSession() {
  localStorage.removeItem(KEY);
}

export function getOverlaySeconds(): number {
  const v = localStorage.getItem(OVERLAY_KEY);
  const n = v ? Number(v) : 4; // 기본 4초
  if (!Number.isFinite(n) || n < 1) return 4;
  if (n > 20) return 20;
  return Math.floor(n);
}

export function setOverlaySeconds(n: number) {
  const v = Math.max(1, Math.min(20, Math.floor(n)));
  localStorage.setItem(OVERLAY_KEY, String(v));
}