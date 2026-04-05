/**
 * 글로벌 인증 미들웨어.
 * 로그인/공유 페이지를 제외한 모든 페이지에서 인증 필수.
 */
export default defineNuxtRouteMiddleware(async (to) => {
  // 로그인 페이지와 공유 페이지는 예외
  if (to.path === '/login' || to.path === '/register' || to.path.startsWith('/conti/share/')) {
    return
  }

  const { isLoggedIn, fetchUser, user } = useAuth()

  if (!isLoggedIn.value) {
    return navigateTo('/login')
  }

  if (!user.value) {
    await fetchUser()
    if (!user.value) {
      return navigateTo('/login')
    }
  }
})
