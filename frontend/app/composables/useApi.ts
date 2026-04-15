export function useApi() {
  const config = useRuntimeConfig()
  const token = useCookie<string | null>('cia_token', {
    maxAge: 60 * 60 * 24 * 7,
    sameSite: 'lax',
    path: '/',
  })

  const normalizeApiRoot = (raw: string) => {
    const trimmed = String(raw || '').trim().replace(/\/$/, '')
    return trimmed.replace(/\/api$/i, '')
  }

  const base = () => {
    if (import.meta.server) {
      const internal = normalizeApiRoot(String(config.apiInternal || ''))
      if (internal) {
        return `${internal}/api`
      }
    }
    const root = normalizeApiRoot(String(config.public.apiBase || ''))
    return root ? `${root}/api` : '/api'
  }

  async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
    const headers: Record<string, string> = {
      ...(options.headers as Record<string, string>),
    }
    if (token.value) {
      headers.Authorization = `Bearer ${token.value}`
    }
    const body = options.body
    if (body && typeof body === 'string' && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json'
    }
    return $fetch<T>(`${base()}${path}`, {
      ...options,
      headers,
    })
  }

  return { apiFetch, token, base }
}
