export default defineNuxtRouteMiddleware(() => {
  const token = useCookie('cia_token')
  if (token.value) {
    return navigateTo('/')
  }
})
