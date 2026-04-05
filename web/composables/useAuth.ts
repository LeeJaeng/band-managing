/**
 * 인증 상태 관리.
 * useCookie로 토큰을 저장하여 SSR/CSR 모두 동작.
 */
export function useAuth() {
  const token = useCookie('auth_token', { maxAge: 60 * 60 * 24 }) // 24시간
  const user = useState<any>('auth_user', () => null)

  const isLoggedIn = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'ADMIN')

  const { api } = useApi()

  async function login(username: string, password: string) {
    const data = await api<any>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    })
    token.value = data.access_token
    user.value = data.user
    return data.user
  }

  async function register(username: string, password: string, displayName: string) {
    const data = await api<any>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ username, password, display_name: displayName }),
    })
    token.value = data.access_token
    user.value = data.user
    return data.user
  }

  function logout() {
    token.value = null
    user.value = null
    navigateTo('/login')
  }

  async function fetchUser() {
    if (!token.value) {
      user.value = null
      return
    }
    try {
      user.value = await api<any>('/api/auth/me')
    } catch {
      // 토큰 만료 등
      token.value = null
      user.value = null
    }
  }

  return { token, user, isLoggedIn, isAdmin, login, register, logout, fetchUser }
}
