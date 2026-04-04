export default defineNuxtRouteMiddleware(async () => {
  const { isLoggedIn, isAdmin, fetchUser, user } = useAuth()

  if (!isLoggedIn.value) {
    return navigateTo('/login')
  }

  if (!user.value) {
    await fetchUser()
    if (!user.value) {
      return navigateTo('/login')
    }
  }

  if (!isAdmin.value) {
    return navigateTo('/')
  }
})
