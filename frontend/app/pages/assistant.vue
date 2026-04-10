<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { apiFetch, base, token } = useApi()
const message = ref('')
const loading = ref(false)
const error = ref('')
const projects = ref<{ id: number; name: string }[]>([])
const selectedProjectId = ref<number | null>(null)
type ReportResult = {
  report_type: string
  report_id: string
  payload: Record<string, unknown>
  downloads: Record<string, string>
}
const reportResult = ref<ReportResult | null>(null)
const projectReady = ref(false)
const readinessHint = ref('Choose a project before asking.')
const showPrompts = ref(true)
type ChatItem = { role: 'user' | 'assistant'; text: string; created_at: string }
const chatHistory = ref<ChatItem[]>([])

const suggestions = [
  'Space detection, room labels, dimensions, symbols, materials',
  'Gross Floor Area (GFA) vs Usable/Net Area calculation',
  'Space-type summary table with efficiency ratio and floor-wise breakdown',
  'Statistical dashboard: Total GFA, usable area, pie chart data',
  'Compliance engine check with exact citations',
  'Missing data and doubt_score list requiring manual re-inspection',
  'Suggestions for corrective actions on flagged compliance issues',
  'Conversational agent flow using retrieve/check/summary/area/doubt tools',
]

onMounted(async () => {
  projects.value = await apiFetch<{ id: number; name: string }[]>('/projects')
  if (projects.value.length) {
    selectedProjectId.value = projects.value[0].id
    loadChatHistory(selectedProjectId.value)
    await refreshReadiness()
  }
})

watch(selectedProjectId, async (projectId) => {
  loadChatHistory(projectId)
  await refreshReadiness()
})

function storageKey(projectId: number | null): string | null {
  return projectId ? `cia_chat_history_${projectId}` : null
}

function loadChatHistory(projectId: number | null) {
  if (!import.meta.client) return
  const key = storageKey(projectId)
  if (!key) {
    chatHistory.value = []
    return
  }
  const raw = localStorage.getItem(key)
  chatHistory.value = raw ? (JSON.parse(raw) as ChatItem[]) : []
}

function persistChatHistory(projectId: number | null) {
  if (!import.meta.client) return
  const key = storageKey(projectId)
  if (!key) return
  localStorage.setItem(key, JSON.stringify(chatHistory.value.slice(-200)))
}

function fullDownloadUrl(path: string): string {
  return `${base()}${path.replace('/api', '')}`
}

async function downloadReport(path: string, key: string) {
  error.value = ''
  try {
    const url = fullDownloadUrl(path)
    const res = await fetch(url, {
      headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
    })
    if (!res.ok) {
      throw new Error(`Download failed (${res.status})`)
    }
    const blob = await res.blob()
    const objUrl = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = objUrl
    a.download = `report-${reportResult.value?.report_id || 'result'}.${key === 'excel' ? 'xlsx' : key === 'word' ? 'docx' : key}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(objUrl)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Report download failed'
  }
}

async function refreshReadiness() {
  projectReady.value = false
  if (!selectedProjectId.value) {
    readinessHint.value = 'Choose a project before asking.'
    return
  }
  try {
    const [drawings, selectedOrdinance, projectFiles] = await Promise.all([
      apiFetch<Array<{ id: number; filename: string }>>(`/projects/by-id/${selectedProjectId.value}/drawings`),
      apiFetch<number[]>(`/projects/by-id/${selectedProjectId.value}/ordinance-selections`),
      apiFetch<Array<{ id: number; filename: string }>>(`/projects/by-id/${selectedProjectId.value}/project-files`),
    ])
    if (!drawings.length) {
      readinessHint.value = 'Upload at least one drawing in this project before asking.'
      return
    }
    if (!selectedOrdinance.length) {
      readinessHint.value = 'Select at least one ordinance document in this project before asking.'
      return
    }
    projectReady.value = true
    readinessHint.value = `Ready: ${drawings.length} drawing(s), ${selectedOrdinance.length} ordinance doc(s), ${projectFiles.length} optional file(s).`
  } catch {
    readinessHint.value = 'Unable to verify project readiness.'
  }
}

async function send() {
  const text = message.value.trim()
  if (!text || loading.value || !selectedProjectId.value || !projectReady.value) return
  error.value = ''
  loading.value = true
  chatHistory.value.push({ role: 'user', text, created_at: new Date().toISOString() })
  persistChatHistory(selectedProjectId.value)
  try {
    const res = await apiFetch<{ reply: string }>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: text, project_id: selectedProjectId.value }),
    })
    chatHistory.value.push({
      role: 'assistant',
      text: res.reply || '(no content)',
      created_at: new Date().toISOString(),
    })
    persistChatHistory(selectedProjectId.value)
    message.value = ''
  } catch (e: unknown) {
    const msg =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail)
        : 'Request failed'
    error.value = msg || 'Request failed'
  } finally {
    loading.value = false
  }
}

function useSuggestion(s: string) {
  message.value = s
  send()
}

function clearChatHistory() {
  chatHistory.value = []
  persistChatHistory(selectedProjectId.value)
}

async function generateStandardReport() {
  if (!selectedProjectId.value) return
  reportResult.value = await apiFetch<ReportResult>('/ai/reports/standard', {
    method: 'POST',
    body: JSON.stringify({ project_id: selectedProjectId.value, user_prompts: [] }),
  })
}

async function generateConsolidatedReport() {
  if (!selectedProjectId.value) return
  const prompts = message.value.trim() ? [message.value.trim()] : []
  reportResult.value = await apiFetch<ReportResult>('/ai/reports/consolidated', {
    method: 'POST',
    body: JSON.stringify({ project_id: selectedProjectId.value, user_prompts: prompts }),
  })
}
</script>

<template>
  <div class="assistant">
    <header class="page-head">
      <h1>AI Assistant</h1>
      <p class="muted">AI-assisted construction intelligence with citations, confidence, and doubt flags.</p>
    </header>

    <div class="panel card">
      <label class="field">
        <span>Project (required before asking)</span>
        <select v-model.number="selectedProjectId" class="input">
          <option :value="null" disabled>Select project</option>
          <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
        </select>
      </label>
      <p class="muted status">{{ readinessHint }}</p>

      <section class="prompt-box">
        <button type="button" class="prompt-toggle" @click="showPrompts = !showPrompts">
          <strong>How can we help on site today?</strong>
          <span>{{ showPrompts ? 'Hide' : 'Show' }}</span>
        </button>
        <div v-if="showPrompts" class="empty-state">
          <p class="muted">Choose a predefined prompt or type your own project question.</p>
          <div class="suggestions">
            <button
              v-for="(s, i) in suggestions"
              :key="i"
              type="button"
              class="suggestion"
              @click="useSuggestion(s)"
            >
              {{ s }}
            </button>
          </div>
        </div>
      </section>

      <div v-if="chatHistory.length || loading" class="output">
        <div v-if="loading" class="muted">Thinking…</div>
        <div v-else class="chat-list">
          <article v-for="(item, idx) in chatHistory" :key="idx" class="chat-item" :class="item.role">
            <div class="chat-role">
              {{ item.role === 'user' ? 'You' : 'AI Assistant' }} · {{ new Date(item.created_at).toLocaleString() }}
            </div>
            <pre class="reply">{{ item.text }}</pre>
          </article>
        </div>
      </div>

      <p v-if="error" class="err">{{ error }}</p>

      <div class="composer">
        <textarea
          v-model="message"
          class="input area"
          rows="3"
          placeholder="Ask about drawings, ordinances, schedules, or risks…"
          @keydown.enter.exact.prevent="send"
        />
        <button
          type="button"
          class="btn btn-primary send"
          :disabled="loading || !selectedProjectId || !projectReady"
          @click="send"
        >
          Send
        </button>
      </div>
      <div class="report-actions">
        <button type="button" class="btn btn-primary" :disabled="!selectedProjectId" @click="generateStandardReport">
          Generate Standard Report
        </button>
        <button type="button" class="btn btn-outline" :disabled="!selectedProjectId" @click="generateConsolidatedReport">
          Consolidated Report
        </button>
        <button type="button" class="btn btn-ghost" :disabled="!selectedProjectId" @click="clearChatHistory">
          Clear Chat History
        </button>
      </div>
      <div v-if="reportResult" class="card report-box">
        <strong>Report Ready: {{ reportResult.report_type }} ({{ reportResult.report_id }})</strong>
        <div class="download-links">
          <button
            v-for="(path, key) in reportResult.downloads"
            :key="key"
            type="button"
            class="btn btn-outline"
            @click="downloadReport(path, key)"
          >
            Download {{ key.toUpperCase() }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-head h1 {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
}

.muted {
  color: var(--text-muted);
  margin: 0 0 1.25rem;
}
.muted.status {
  margin-top: -0.75rem;
}

.panel {
  max-width: 720px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state h2 {
  margin: 0 0 0.5rem;
  font-size: 1.15rem;
}
.prompt-box {
  border: 1px solid var(--border);
  border-radius: 0.65rem;
  padding: 0.75rem;
}

.prompt-toggle {
  width: 100%;
  border: none;
  background: transparent;
  color: inherit;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  text-align: left;
  padding: 0;
}

.suggestions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.65rem;
  margin-top: 1rem;
}

.suggestion {
  text-align: left;
  padding: 0.85rem 1rem;
  border-radius: 0.65rem;
  border: 1px solid var(--border);
  background: var(--main-bg);
  color: var(--text);
  font-family: inherit;
  font-size: 0.8125rem;
  line-height: 1.35;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.suggestion:hover {
  border-color: var(--accent);
  background: var(--accent-dim);
}

.output {
  min-height: 120px;
}
.chat-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.chat-item {
  border: 1px solid var(--border);
  border-radius: 0.65rem;
  padding: 0.75rem;
  background: var(--main-bg);
}
.chat-item.user {
  border-color: var(--accent);
}
.chat-role {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-bottom: 0.35rem;
}

.reply {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 0.9375rem;
  line-height: 1.55;
}

.err {
  color: #dc2626;
  font-size: 0.875rem;
  margin: 0;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.875rem;
}

.report-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.report-box {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.download-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.area {
  resize: vertical;
  min-height: 80px;
}

.send {
  align-self: flex-end;
}
</style>
