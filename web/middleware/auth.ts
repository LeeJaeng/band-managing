export default defineNuxtRouteMiddleware(async () => {
  const { isLoggedIn, fetchUser, user } = useAuth()

  if (!isLoggedIn.value) {
    return navigateTo('/login')
  }

  // 유저 정보가 없으면 가져오기
  if (!user.value) {
    await fetchUser()
    if (!user.value) {
      return navigateTo('/login')
    }
  }
})
