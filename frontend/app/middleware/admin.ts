export default defineNuxtRouteMiddleware(async () => {
  const token = useCookie('cia_token')
  if (!token.value) {
    return navigateTo('/login')
  }
  const { loadMe, me } = useAuth()
  await loadMe()
  if (me.value?.role !== 'admin') {
    return navigateTo('/')
  }
})
