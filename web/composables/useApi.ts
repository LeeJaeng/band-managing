/**
 * API 호출 헬퍼.
 * SSR 시에는 Docker 내부 주소, 클라이언트에서는 상대 경로 사용.
 * 인증 토큰이 있으면 Authorization 헤더 자동 첨부.
 */
export function useApi() {
  const baseURL = import.meta.server ? 'http://api:8000' : ''
  const token = useCookie('auth_token')

  async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
    const url = `${baseURL}${path}`
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(opts.headers as Record<string, string> || {}),
    }
    if (token.value) {
      headers['Authorization'] = `Bearer ${token.value}`
    }
    const res = await $fetch<T>(url, {
      ...opts,
      headers,
    } as any)
    return res
  }

  return { api }
}
