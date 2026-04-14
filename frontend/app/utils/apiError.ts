/** Best-effort message from $fetch / ofetch errors (network, CORS, 4xx/5xx). */
export function apiErrorMessage(e: unknown, fallback: string): string {
  if (!e || typeof e !== 'object') return fallback
  const err = e as Record<string, unknown>
  const data = err.data
  if (data && typeof data === 'object') {
    const d = data as Record<string, unknown>
    if (typeof d.detail === 'string' && d.detail.trim()) return d.detail
    if (Array.isArray(d.detail) && d.detail.length) {
      const first = d.detail[0] as Record<string, unknown> | undefined
      if (first && typeof first.msg === 'string' && first.msg.trim()) return first.msg
    }
    if (typeof d.message === 'string' && d.message.trim()) return d.message
  }
  if (typeof err.message === 'string' && err.message.trim()) return err.message
  if (typeof err.statusMessage === 'string' && err.statusMessage.trim()) return err.statusMessage
  return fallback
}
