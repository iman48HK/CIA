export interface Me {
  id: number
  email: string
  role: 'admin' | 'user'
  is_active: boolean
  display_name?: string | null
  avatar_url?: string | null
}

export function useAuth() {
  const { apiFetch, token } = useApi()
  const me = useState<Me | null>('auth-me', () => null)

  async function loadMe() {
    if (!token.value) {
      me.value = null
      return null
    }
    try {
      me.value = await apiFetch<Me>('/users/me')
      return me.value
    } catch {
      token.value = null
      me.value = null
      return null
    }
  }

  function logout() {
    token.value = null
    me.value = null
    navigateTo('/login')
  }

  return { me, token, loadMe, logout }
}
