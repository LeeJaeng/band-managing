/**
 * API 호출 헬퍼.
 * SSR 시에는 Docker 내부 주소, 클라이언트에서는 상대 경로 사용.
 */
export function useApi() {
  const baseURL = import.meta.server ? 'http://api:8000' : ''

  async function api<T = any>(path: string, opts: RequestInit = {}): Promise<T> {
    const url = `${baseURL}${path}`
    const res = await $fetch<T>(url, {
      ...opts,
      headers: {
        'Content-Type': 'application/json',
        ...(opts.headers as Record<string, string> || {}),
      },
    } as any)
    return res
  }

  return { api }
}
