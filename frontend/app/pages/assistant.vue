<script setup lang="ts">
definePageMeta({ middleware: 'auth' })
import { marked } from 'marked'

const { apiFetch, base, token } = useApi()
const { me, loadMe } = useAuth()

const message = ref('')
const loading = ref(false)
const error = ref('')
const projects = ref<{ id: number; name: string }[]>([])
const selectedProjectId = ref<number | null>(null)

type UploadRow = {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  created_at: string
}

type AnalysisFiles = {
  drawings: UploadRow[]
  project_files: UploadRow[]
  ordinances: { id: number; title: string }[]
}

const analysisFiles = ref<AnalysisFiles | null>(null)

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

const DEFAULT_PRESET_PROMPTS = [
  'Calculate Gross Floor Area (GFA) and Usable Area using geometry.',
  'Dedicated Space Types Summary with gross_m2, usable_m2, counts, percentages, floor-wise breakdown, efficiency ratio.',
  'Statistical dashboard (totals, pie charts).',
  'HK regulations parsing -> structured rules -> compliance checking with citations.',
  'Missing data detection + doubt_score (0-100) on every extraction + manual_review_reason. Prominent "Manual Re-inspection Required" dashboard.',
  'LLM-generated suggestions for fixes.',
]

const presetPrompts = ref<string[]>([...DEFAULT_PRESET_PROMPTS])
const newPresetText = ref('')

type ChatItem = { id: string; role: 'user' | 'assistant'; text: string; created_at: string }
const chatHistory = ref<ChatItem[]>([])

type CollectedItem = {
  id: string
  source: string
  label: string
  text: string
  created_at: string
}
const collectedOutputs = ref<CollectedItem[]>([])
const consolidating = ref(false)

const annotationDrawing = ref<UploadRow | null>(null)
const annotationObjectUrl = ref('')
const annotationMode = ref<'deficiency' | 'discrepancy'>('deficiency')
type AnnotationMarker = { xPct: number; yPct: number; type: 'deficiency' | 'discrepancy'; note: string }
type AnnotationAsset = {
  drawing_id: number
  filename: string
  image_data_url: string
  markers: AnnotationMarker[]
}
const annotationMarkers = ref<AnnotationMarker[]>([])
const annotationAssets = ref<AnnotationAsset[]>([])
const annotationCanvas = ref<HTMLCanvasElement | null>(null)
const annotationImg = ref<HTMLImageElement | null>(null)

function storageKeyChat(projectId: number | null): string | null {
  return projectId ? `cia_chat_history_${projectId}` : null
}

function storageKeyPresets(): string {
  const uid = me.value?.id ?? 'anon'
  return `cia_assistant_presets_${uid}`
}

function storageKeyCollected(projectId: number | null): string | null {
  return projectId ? `cia_collected_outputs_${projectId}` : null
}

function loadPresetPrompts() {
  if (!import.meta.client) return
  const raw = localStorage.getItem(storageKeyPresets())
  if (raw) {
    try {
      const parsed = JSON.parse(raw) as string[]
      if (Array.isArray(parsed) && parsed.length) {
        presetPrompts.value = parsed.filter((s) => typeof s === 'string' && s.trim())
        return
      }
    } catch {
      /* fall through */
    }
  }
  presetPrompts.value = [...DEFAULT_PRESET_PROMPTS]
}

function persistPresetPrompts() {
  if (!import.meta.client) return
  localStorage.setItem(storageKeyPresets(), JSON.stringify(presetPrompts.value))
}

function addPresetPrompt() {
  const t = newPresetText.value.trim()
  if (!t) return
  presetPrompts.value = [...presetPrompts.value, t]
  newPresetText.value = ''
  persistPresetPrompts()
}

function removePresetPrompt(index: number) {
  presetPrompts.value = presetPrompts.value.filter((_, i) => i !== index)
  persistPresetPrompts()
}

function resetPresetPrompts() {
  presetPrompts.value = [...DEFAULT_PRESET_PROMPTS]
  persistPresetPrompts()
}

function loadCollected(projectId: number | null) {
  if (!import.meta.client) return
  const key = storageKeyCollected(projectId)
  if (!key) {
    collectedOutputs.value = []
    return
  }
  const raw = localStorage.getItem(key)
  if (!raw) {
    collectedOutputs.value = []
    return
  }
  try {
    const parsed = JSON.parse(raw) as CollectedItem[]
    collectedOutputs.value = Array.isArray(parsed) ? parsed : []
  } catch {
    collectedOutputs.value = []
  }
}

function persistCollected(projectId: number | null) {
  if (!import.meta.client) return
  const key = storageKeyCollected(projectId)
  if (!key) return
  localStorage.setItem(key, JSON.stringify(collectedOutputs.value.slice(-100)))
}

function ensureChatId(item: Partial<ChatItem> & { role: 'user' | 'assistant'; text: string; created_at: string }): ChatItem {
  return {
    id: item.id || (typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now())),
    role: item.role,
    text: item.text,
    created_at: item.created_at,
  }
}

function loadChatHistory(projectId: number | null) {
  if (!import.meta.client) return
  const key = storageKeyChat(projectId)
  if (!key) {
    chatHistory.value = []
    return
  }
  const raw = localStorage.getItem(key)
  if (!raw) {
    chatHistory.value = []
    return
  }
  try {
    const parsed = JSON.parse(raw) as Partial<ChatItem>[]
    if (!Array.isArray(parsed)) {
      chatHistory.value = []
      return
    }
    let needPersist = false
    chatHistory.value = parsed.map((row) => {
      const hasId = typeof row.id === 'string' && row.id.length > 0
      if (!hasId) needPersist = true
      return ensureChatId({
        id: hasId ? row.id : undefined,
        role: row.role === 'user' ? 'user' : 'assistant',
        text: String(row.text ?? ''),
        created_at: String(row.created_at ?? ''),
      })
    })
    if (needPersist) persistChatHistory(projectId)
  } catch {
    chatHistory.value = []
  }
}

function persistChatHistory(projectId: number | null) {
  if (!import.meta.client) return
  const key = storageKeyChat(projectId)
  if (!key) return
  localStorage.setItem(key, JSON.stringify(chatHistory.value.slice(-200)))
}

onMounted(async () => {
  await loadMe()
  loadPresetPrompts()
  projects.value = await apiFetch<{ id: number; name: string }[]>('/projects')
  if (projects.value.length) {
    selectedProjectId.value = projects.value[0].id
    loadChatHistory(selectedProjectId.value)
    loadCollected(selectedProjectId.value)
    await refreshReadiness()
  }
})

watch(selectedProjectId, async (projectId) => {
  loadChatHistory(projectId)
  loadCollected(projectId)
  await refreshReadiness()
})

watch(me, () => loadPresetPrompts(), { deep: true })

const reportAuthor = computed(() => {
  const m = me.value
  if (!m) return undefined
  return (m.display_name || m.email || '').trim() || undefined
})

function fullDownloadUrl(path: string): string {
  return `${base()}${path.replace('/api', '')}`
}

function extensionForReportKey(key: string): string {
  if (key === 'excel') return 'xlsx'
  if (key === 'word') return 'docx'
  return key
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
    const ext = extensionForReportKey(key)
    a.download = `report-${reportResult.value?.report_id || 'result'}.${ext}`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(objUrl)
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : 'Report download failed'
  }
}

function downloadTextFile(filename: string, content: string, mime: string) {
  const blob = new Blob([content], { type: mime })
  const objUrl = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = objUrl
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(objUrl)
}

function buildExportHeader(title: string): string {
  const who = reportAuthor.value || 'User'
  const when = new Date().toLocaleString()
  return `Title: ${title}\nAuthor: ${who}\nGenerated: ${when}\n${'─'.repeat(48)}\n\n`
}

function downloadChatExport(item: ChatItem, format: 'txt' | 'md' | 'html') {
  const title = item.role === 'user' ? 'User message' : 'AI Assistant reply'
  const header = buildExportHeader(title)
  const roleLabel = item.role === 'user' ? 'You' : 'AI Assistant'
  const who = reportAuthor.value || 'User'
  const when = new Date().toLocaleString()
  if (format === 'txt') {
    const body = `${roleLabel} · ${item.created_at}\n\n${item.text}`
    downloadTextFile(`cia-${item.id}.txt`, header + body, 'text/plain;charset=utf-8')
    return
  }
  if (format === 'md') {
    const md =
      `# ${title}\n\n` +
      `**Author:** ${who}  \n**Generated:** ${when}  \n**Message time:** ${item.created_at}\n\n---\n\n` +
      `## ${roleLabel}\n\n${item.text}\n`
    downloadTextFile(`cia-${item.id}.md`, md, 'text/markdown;charset=utf-8')
    return
  }
  const inner =
    item.role === 'assistant'
      ? (typeof marked.parse(item.text, { gfm: true, breaks: true }) === 'string'
          ? (marked.parse(item.text, { gfm: true, breaks: true }) as string)
          : escapeHtml(item.text))
      : `<p>${escapeHtml(item.text).replaceAll('\n', '<br />')}</p>`
  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>${escapeHtml(title)}</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #0f172a; line-height: 1.55; }
    .meta { color: #64748b; font-size: 0.9rem; margin-bottom: 1.25rem; border-bottom: 1px solid #e2e8f0; padding-bottom: 0.75rem; }
    .meta strong { color: #334155; }
    table { border-collapse: collapse; width: 100%; margin: 0.75rem 0; }
    th, td { border: 1px solid #e2e8f0; padding: 0.4rem 0.5rem; }
    th { background: #f1f5f9; }
  </style>
</head>
<body>
  <h1>${escapeHtml(title)}</h1>
  <div class="meta">
    <div><strong>Author</strong> ${escapeHtml(reportAuthor.value || 'User')}</div>
    <div><strong>Message time</strong> ${escapeHtml(item.created_at)}</div>
  </div>
  <div class="body">${inner}</div>
</body>
</html>`
  downloadTextFile(`cia-${item.id}.html`, html, 'text/html;charset=utf-8')
}

function collectChatMessage(item: ChatItem) {
  const label = item.role === 'user' ? 'User message' : 'AI reply'
  collectedOutputs.value.push({
    id: typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    source: 'chat',
    label,
    text: item.text,
    created_at: item.created_at,
  })
  persistCollected(selectedProjectId.value)
}

function collectCurrentReport() {
  if (!reportResult.value) return
  const text = JSON.stringify(reportResult.value.payload, null, 2)
  collectedOutputs.value.push({
    id: typeof crypto !== 'undefined' && crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    source: `report:${reportResult.value.report_type}`,
    label: `Report ${reportResult.value.report_id}`,
    text,
    created_at: new Date().toISOString(),
  })
  persistCollected(selectedProjectId.value)
}

function removeCollected(id: string) {
  collectedOutputs.value = collectedOutputs.value.filter((c) => c.id !== id)
  persistCollected(selectedProjectId.value)
}

async function refreshReadiness() {
  projectReady.value = false
  analysisFiles.value = null
  if (!selectedProjectId.value) {
    readinessHint.value = 'Choose a project before asking.'
    return
  }
  try {
    const data = await apiFetch<AnalysisFiles>(`/projects/by-id/${selectedProjectId.value}/analysis-files`)
    analysisFiles.value = data
    const drawings = data.drawings
    const ordCount = data.ordinances.length
    const pfCount = data.project_files.length
    if (!drawings.length) {
      readinessHint.value = 'Upload at least one drawing in this project before asking.'
      return
    }
    if (!ordCount) {
      readinessHint.value = 'Select at least one ordinance document in this project before asking.'
      return
    }
    projectReady.value = true
    readinessHint.value = `Ready: ${drawings.length} drawing(s), ${ordCount} ordinance doc(s), ${pfCount} optional file(s).`
  } catch {
    readinessHint.value = 'Unable to verify project readiness.'
  }
}

async function send() {
  const text = message.value.trim()
  if (!text || loading.value || !selectedProjectId.value || !projectReady.value) return
  error.value = ''
  loading.value = true
  const userItem = ensureChatId({ role: 'user', text, created_at: new Date().toISOString() })
  chatHistory.value.push(userItem)
  persistChatHistory(selectedProjectId.value)
  try {
    const res = await apiFetch<{ reply: string }>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: text, project_id: selectedProjectId.value }),
    })
    chatHistory.value.push(
      ensureChatId({
        role: 'assistant',
        text: res.reply || '(no content)',
        created_at: new Date().toISOString(),
      })
    )
    persistChatHistory(selectedProjectId.value)
    message.value = ''
  } catch (e: unknown) {
    const msg =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail)
        : 'Request failed'
    error.value = msg || 'Request failed'
    chatHistory.value.pop()
    persistChatHistory(selectedProjectId.value)
  } finally {
    loading.value = false
  }
}

function useSuggestion(s: string) {
  message.value = s
  send()
}

function deleteChatMessage(id: string) {
  chatHistory.value = chatHistory.value.filter((m) => m.id !== id)
  persistChatHistory(selectedProjectId.value)
}

function clearChatHistory() {
  if (!confirm('Remove all messages in this project’s chat?')) return
  chatHistory.value = []
  persistChatHistory(selectedProjectId.value)
}

async function generateStandardReport() {
  if (!selectedProjectId.value) return
  const assets = annotationAssetsForReport()
  annotationAssets.value = assets
  reportResult.value = await apiFetch<ReportResult>('/ai/reports/standard', {
    method: 'POST',
    body: JSON.stringify({
      project_id: selectedProjectId.value,
      user_prompts: [],
      chat_history: chatHistory.value,
      annotation_assets: assets,
      author: reportAuthor.value,
    }),
  })
}

async function consolidateCollectedReport() {
  if (!selectedProjectId.value || !collectedOutputs.value.length) return
  const assets = annotationAssetsForReport()
  annotationAssets.value = assets
  consolidating.value = true
  error.value = ''
  try {
    reportResult.value = await apiFetch<ReportResult>('/ai/reports/consolidate-collection', {
      method: 'POST',
      body: JSON.stringify({
        project_id: selectedProjectId.value,
        author: reportAuthor.value,
        annotation_assets: assets,
        items: collectedOutputs.value.map((c) => ({
          id: c.id,
          source: c.source,
          label: c.label,
          text: c.text,
          created_at: c.created_at,
        })),
      }),
    })
  } catch (e: unknown) {
    const msg =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail)
        : 'Consolidate failed'
    error.value = msg || 'Consolidate failed'
  } finally {
    consolidating.value = false
  }
}

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;')
}

function renderChatHtml(item: ChatItem): string {
  if (item.role === 'user') {
    return `<p>${escapeHtml(item.text).replaceAll('\n', '<br />')}</p>`
  }
  const rendered = marked.parse(item.text, { gfm: true, breaks: true })
  return typeof rendered === 'string' ? rendered : item.text
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}

function isImageDrawing(row: UploadRow): boolean {
  return (row.content_type || '').startsWith('image/')
}

async function openAnnotation(d: UploadRow) {
  if (!selectedProjectId.value || !isImageDrawing(d)) return
  annotationDrawing.value = d
  const saved = annotationAssets.value.find((a) => a.drawing_id === d.id)
  annotationMarkers.value = saved ? saved.markers.map((m) => ({ ...m })) : []
  const path = `/projects/by-id/${selectedProjectId.value}/drawings/${d.id}/content`
  const res = await fetch(`${base()}${path}`, {
    headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
  })
  if (!res.ok) {
    error.value = 'Could not load drawing for annotation.'
    return
  }
  const blob = await res.blob()
  if (annotationObjectUrl.value) URL.revokeObjectURL(annotationObjectUrl.value)
  annotationObjectUrl.value = URL.createObjectURL(blob)
  await nextTick()
  redrawAnnotationCanvas()
}

function closeAnnotation() {
  annotationDrawing.value = null
  if (annotationObjectUrl.value) URL.revokeObjectURL(annotationObjectUrl.value)
  annotationObjectUrl.value = ''
  annotationMarkers.value = []
}

function buildAnnotatedImageDataUrl(): string | null {
  const img = annotationImg.value
  if (!img || !img.complete) return null
  const nw = img.naturalWidth
  const nh = img.naturalHeight
  const exportCanvas = document.createElement('canvas')
  exportCanvas.width = nw
  exportCanvas.height = nh
  const ctx = exportCanvas.getContext('2d')
  if (!ctx) return null
  ctx.drawImage(img, 0, 0, nw, nh)
  for (const m of annotationMarkers.value) {
    const x = m.xPct * nw
    const y = m.yPct * nh
    const r = Math.max(12, Math.round(nw * 0.014))
    ctx.beginPath()
    ctx.fillStyle = m.type === 'deficiency' ? 'rgba(220, 38, 38, 0.88)' : 'rgba(234, 88, 12, 0.92)'
    ctx.arc(x, y, r, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = Math.max(2, Math.round(nw * 0.002))
    ctx.stroke()
    if (m.note) {
      ctx.font = `${Math.max(14, Math.round(nw * 0.018))}px system-ui`
      ctx.fillStyle = '#0f172a'
      ctx.fillText(m.note.slice(0, 80), x + r + 4, y + 4)
    }
  }
  return exportCanvas.toDataURL('image/png')
}

function attachAnnotatedDrawingToReport() {
  if (!annotationDrawing.value || !annotationMarkers.value.length) {
    error.value = 'Add at least one marker before attaching drawing to report.'
    return
  }
  const dataUrl = buildAnnotatedImageDataUrl()
  if (!dataUrl) {
    error.value = 'Could not render annotated drawing.'
    return
  }
  const item: AnnotationAsset = {
    drawing_id: annotationDrawing.value.id,
    filename: annotationDrawing.value.filename,
    image_data_url: dataUrl,
    markers: annotationMarkers.value.map((m) => ({ ...m })),
  }
  const existingIdx = annotationAssets.value.findIndex((a) => a.drawing_id === item.drawing_id)
  if (existingIdx >= 0) {
    annotationAssets.value.splice(existingIdx, 1, item)
  } else {
    annotationAssets.value.push(item)
  }
  error.value = ''
}

function annotationAssetsForReport(): AnnotationAsset[] {
  const assets = annotationAssets.value.map((a) => ({
    drawing_id: a.drawing_id,
    filename: a.filename,
    image_data_url: a.image_data_url,
    markers: a.markers.map((m) => ({ ...m })),
  }))
  // Auto-include the drawing currently open in the annotation modal.
  if (!annotationDrawing.value || !annotationMarkers.value.length) return assets
  const dataUrl = buildAnnotatedImageDataUrl()
  if (!dataUrl) return assets
  const liveItem: AnnotationAsset = {
    drawing_id: annotationDrawing.value.id,
    filename: annotationDrawing.value.filename,
    image_data_url: dataUrl,
    markers: annotationMarkers.value.map((m) => ({ ...m })),
  }
  const idx = assets.findIndex((a) => a.drawing_id === liveItem.drawing_id)
  if (idx >= 0) assets[idx] = liveItem
  else assets.push(liveItem)
  return assets
}

function redrawAnnotationCanvas() {
  const canvas = annotationCanvas.value
  const img = annotationImg.value
  if (!canvas || !img || !img.complete || !img.naturalWidth) return
  const w = img.clientWidth
  const h = img.clientHeight
  if (!w || !h) return
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1
  canvas.width = Math.round(w * dpr)
  canvas.height = Math.round(h * dpr)
  canvas.style.width = `${w}px`
  canvas.style.height = `${h}px`
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.setTransform(1, 0, 0, 1, 0, 0)
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, w, h)
  for (const m of annotationMarkers.value) {
    const x = m.xPct * w
    const y = m.yPct * h
    ctx.beginPath()
    ctx.fillStyle = m.type === 'deficiency' ? 'rgba(220, 38, 38, 0.85)' : 'rgba(234, 88, 12, 0.9)'
    ctx.arc(x, y, 10, 0, Math.PI * 2)
    ctx.fill()
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 2
    ctx.stroke()
    if (m.note) {
      ctx.font = '600 12px system-ui'
      ctx.fillStyle = '#0f172a'
      ctx.fillText(m.note.slice(0, 60), x + 14, y - 10)
    }
  }
}

function onAnnotationImageLoad() {
  redrawAnnotationCanvas()
}

function onAnnotationCanvasClick(e: MouseEvent) {
  const canvas = annotationCanvas.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const x = e.clientX - rect.left
  const y = e.clientY - rect.top
  const w = rect.width
  const h = rect.height
  if (!w || !h) return
  const label = annotationMode.value === 'deficiency' ? 'Deficiency' : 'Discrepancy'
  annotationMarkers.value.push({
    xPct: x / w,
    yPct: y / h,
    type: annotationMode.value,
    note: `${label} ${annotationMarkers.value.length + 1}`,
  })
  redrawAnnotationCanvas()
}

function removeAnnotationMarker(index: number) {
  annotationMarkers.value = annotationMarkers.value.filter((_, i) => i !== index)
  redrawAnnotationCanvas()
}

function exportAnnotatedImage() {
  const dataUrl = buildAnnotatedImageDataUrl()
  if (!dataUrl) return
  fetch(dataUrl)
    .then((r) => r.blob())
    .then((blob) => {
    if (!blob) return
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `annotated-${annotationDrawing.value?.filename || 'drawing'}.png`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
    })
}
</script>

<template>
  <div class="assistant">
    <header class="page-head">
      <h1>AI Assistant</h1>
      <p class="muted lead-intro">
        AI-assisted construction intelligence with citations, confidence, and doubt flags. Pick a project, review files,
        then chat or run reports.
      </p>
    </header>

    <div class="layout">
      <div class="panel card main-panel">
        <label class="field">
          <span>Select a project</span>
          <select
            v-model.number="selectedProjectId"
            class="input project-select"
            :class="{ 'project-select--selected': !!selectedProjectId }"
          >
            <option :value="null" disabled>Select project</option>
            <option v-for="p in projects" :key="p.id" :value="p.id">{{ p.name }}</option>
          </select>
        </label>
        <p class="muted status">{{ readinessHint }}</p>

        <section v-if="analysisFiles" class="file-inventory card-inner">
          <h2 class="section-label">Project files for analysis</h2>
          <p class="muted small">Drawings, selected ordinance documents, and optional project files sent as context to the assistant.</p>
          <div class="file-groups">
            <div class="file-group">
              <h3>Drawings</h3>
              <ul class="file-list">
                <li v-for="f in analysisFiles.drawings" :key="'d-' + f.id" class="file-row">
                  <span class="fname">{{ f.filename }}</span>
                  <span class="fmeta">{{ formatBytes(f.size_bytes) }}</span>
                  <button
                    v-if="isImageDrawing(f)"
                    type="button"
                    class="btn btn-ghost tiny"
                    @click="openAnnotation(f)"
                  >
                    Annotate
                  </button>
                </li>
                <li v-if="!analysisFiles.drawings.length" class="muted">None</li>
              </ul>
            </div>
            <div class="file-group">
              <h3>Ordinance documents (selected)</h3>
              <ul class="file-list">
                <li v-for="o in analysisFiles.ordinances" :key="'o-' + o.id" class="file-row">
                  <span class="fname">{{ o.title }}</span>
                </li>
                <li v-if="!analysisFiles.ordinances.length" class="muted">None selected</li>
              </ul>
            </div>
            <div class="file-group">
              <h3>Project files</h3>
              <ul class="file-list">
                <li v-for="f in analysisFiles.project_files" :key="'p-' + f.id" class="file-row">
                  <span class="fname">{{ f.filename }}</span>
                  <span class="fmeta">{{ formatBytes(f.size_bytes) }}</span>
                </li>
                <li v-if="!analysisFiles.project_files.length" class="muted">None</li>
              </ul>
            </div>
          </div>
        </section>

        <section class="prompt-box">
          <button type="button" class="prompt-toggle" @click="showPrompts = !showPrompts">
            <strong>Preset prompts</strong>
            <span class="toggle-arrow" :aria-label="showPrompts ? 'Collapse preset prompts' : 'Expand preset prompts'">
              <svg
                v-if="showPrompts"
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                aria-hidden="true"
              >
                <path d="M18 15l-6-6-6 6" />
              </svg>
              <svg
                v-else
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                aria-hidden="true"
              >
                <path d="M6 9l6 6 6-6" />
              </svg>
            </span>
          </button>
          <div v-if="showPrompts" class="preset-panel">
            <p class="muted small">Manage your saved prompts — add your own or remove ones you do not need.</p>
            <div class="preset-actions">
              <button type="button" class="btn btn-outline tiny-btn" @click="resetPresetPrompts">
                Reload built-in prompts
              </button>
            </div>
            <div class="preset-list">
              <div v-for="(s, i) in presetPrompts" :key="i + s.slice(0, 12)" class="preset-row">
                <button type="button" class="suggestion" @click="useSuggestion(s)">{{ s }}</button>
                <button type="button" class="icon-btn danger" title="Delete prompt" @click="removePresetPrompt(i)">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path
                      d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                    />
                  </svg>
                </button>
              </div>
            </div>
            <div class="add-preset">
              <input v-model="newPresetText" class="input" placeholder="New preset prompt…" @keydown.enter.prevent="addPresetPrompt" />
              <button type="button" class="btn btn-outline" @click="addPresetPrompt">Add prompt</button>
            </div>
          </div>
        </section>

        <div v-if="chatHistory.length || loading" class="output">
          <div v-if="loading" class="muted">Thinking…</div>
          <div v-else class="chat-list">
            <article v-for="item in chatHistory" :key="item.id" class="chat-item" :class="item.role">
              <div class="chat-toolbar">
                <div class="chat-role">
                  {{ item.role === 'user' ? 'You' : 'AI Assistant' }} · {{ new Date(item.created_at).toLocaleString() }}
                </div>
                <div class="chat-actions">
                  <div class="download-menu" title="Download">
                    <button type="button" class="icon-btn" aria-label="Download as text" @click="downloadChatExport(item, 'txt')">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor"><path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z"/></svg>
                    </button>
                    <button type="button" class="icon-btn" aria-label="Download as Markdown" @click="downloadChatExport(item, 'md')">
                      <span class="fmt-label">MD</span>
                    </button>
                    <button type="button" class="icon-btn" aria-label="Download as HTML" @click="downloadChatExport(item, 'html')">
                      <span class="fmt-label">HTML</span>
                    </button>
                  </div>
                  <button type="button" class="icon-btn collect" title="Collect for consolidated report" @click="collectChatMessage(item)">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" />
                    </svg>
                  </button>
                  <button type="button" class="icon-btn danger" title="Delete message" @click="deleteChatMessage(item.id)">
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                    </svg>
                  </button>
                </div>
              </div>
              <div class="reply" v-html="renderChatHtml(item)" />
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
          <span v-if="annotationAssets.length" class="muted tiny attached-note">
            {{ annotationAssets.length }} annotated drawing(s) attached
          </span>
          <button type="button" class="btn btn-ghost" :disabled="!selectedProjectId" @click="clearChatHistory">
            Clear all chat
          </button>
        </div>
        <div v-if="reportResult" class="card report-box">
          <div class="report-head">
            <div>
              <strong>Report ready</strong>
              <span class="muted small">{{ reportResult.report_type }} · {{ reportResult.report_id }}</span>
            </div>
            <button type="button" class="icon-btn collect" title="Collect this report" @click="collectCurrentReport">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                <path d="M4 6h16v2H4zm0 5h16v2H4zm0 5h16v2H4z" />
              </svg>
            </button>
          </div>
          <div class="download-links">
            <button
              v-for="(path, key) in reportResult.downloads"
              :key="key"
              type="button"
              class="dl-icon-btn"
              :title="`Download ${key}`"
              @click="downloadReport(path, key)"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" />
              </svg>
              <span class="dl-key">{{ key }}</span>
            </button>
          </div>
        </div>
      </div>

      <aside class="panel card side-panel">
        <h2 class="section-label">Collected outputs</h2>
        <p class="muted small">
          Use the list icon on a message or report to add material here, then build one consolidated report with exports
          (PDF, Word, HTML, etc.).
        </p>
        <ul class="collected-list">
          <li v-for="c in collectedOutputs" :key="c.id" class="collected-item">
            <div class="collected-top">
              <strong>{{ c.label }}</strong>
              <button type="button" class="icon-btn danger tiny" title="Remove" @click="removeCollected(c.id)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                </svg>
              </button>
            </div>
            <div class="muted tiny">{{ c.source }} · {{ new Date(c.created_at).toLocaleString() }}</div>
            <pre class="collected-snippet">{{ c.text.slice(0, 280) }}{{ c.text.length > 280 ? '…' : '' }}</pre>
          </li>
        </ul>
        <p v-if="!collectedOutputs.length" class="muted small">Nothing collected yet.</p>
        <button
          type="button"
          class="btn btn-primary block-btn"
          :disabled="!selectedProjectId || !collectedOutputs.length || consolidating"
          @click="consolidateCollectedReport"
        >
          {{ consolidating ? 'Building…' : 'Consolidate report' }}
        </button>
      </aside>
    </div>

    <div v-if="annotationDrawing" class="modal-backdrop" @click.self="closeAnnotation">
      <div class="card modal-card annotate-modal">
        <div class="annotate-head">
          <h3>Drawing annotations</h3>
          <button type="button" class="btn btn-ghost" @click="closeAnnotation">Close</button>
        </div>
        <p class="muted small">
          Mark <strong class="def">deficiencies</strong> (red) or <strong class="disc">discrepancies</strong> (amber). Click the image to place a
          marker, then edit each label in the marker list.
        </p>
        <div class="annotate-tools">
          <label class="radio-pill">
            <input v-model="annotationMode" type="radio" value="deficiency" />
            Deficiency
          </label>
          <label class="radio-pill">
            <input v-model="annotationMode" type="radio" value="discrepancy" />
            Discrepancy
          </label>
          <button type="button" class="btn btn-outline" @click="annotationMarkers = []; redrawAnnotationCanvas()">Clear markers</button>
          <button type="button" class="btn btn-outline" @click="attachAnnotatedDrawingToReport">Attach to report</button>
          <button type="button" class="btn btn-primary" @click="exportAnnotatedImage">Download PNG</button>
        </div>
        <div class="annotate-canvas-wrap">
          <img
            v-if="annotationObjectUrl"
            ref="annotationImg"
            :src="annotationObjectUrl"
            alt="Drawing"
            class="annotate-img"
            @load="onAnnotationImageLoad"
          />
          <canvas
            ref="annotationCanvas"
            class="annotate-canvas"
            @click="onAnnotationCanvasClick"
          />
        </div>
        <div v-if="annotationMarkers.length" class="annotation-list">
          <div v-for="(m, idx) in annotationMarkers" :key="`m-${idx}`" class="annotation-row">
            <span class="marker-chip" :class="m.type">{{ idx + 1 }}</span>
            <input v-model="m.note" class="input marker-input" placeholder="Marker label" @input="redrawAnnotationCanvas" />
            <button type="button" class="icon-btn danger" title="Remove marker" @click="removeAnnotationMarker(idx)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
              </svg>
            </button>
          </div>
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

.lead-intro {
  max-width: 52rem;
}

.muted {
  color: var(--text-muted);
  margin: 0 0 1rem;
}
.muted.status {
  margin-top: -0.5rem;
}

.project-select--selected {
  font-weight: 700;
  background: var(--accent-dim);
  border-color: var(--accent);
}

.layout {
  display: grid;
  grid-template-columns: 1fr min(340px, 100%);
  gap: 1.25rem;
  align-items: start;
}

@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

.main-panel {
  max-width: none;
}

.panel {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.section-label {
  margin: 0 0 0.35rem;
  font-size: 1rem;
}

.card-inner {
  padding: 0.75rem 0 0;
  border: none;
  box-shadow: none;
  background: transparent;
}

.file-groups {
  display: grid;
  gap: 1rem;
  margin-top: 0.5rem;
}

@media (min-width: 720px) {
  .file-groups {
    grid-template-columns: repeat(3, 1fr);
  }
}

.file-group h3 {
  margin: 0 0 0.35rem;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.file-list {
  list-style: none;
  margin: 0;
  padding: 0;
  font-size: 0.85rem;
}

.file-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  padding: 0.35rem 0;
  border-bottom: 1px solid var(--border);
}

.fname {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.fmeta {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.small {
  font-size: 0.8125rem;
}

.tiny {
  font-size: 0.7rem;
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

.toggle-arrow {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--text-muted);
}

.preset-panel {
  margin-top: 0.75rem;
}

.preset-actions {
  margin: 0.5rem 0 0.25rem;
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin: 0.75rem 0;
}

.preset-row {
  display: flex;
  gap: 0.35rem;
  align-items: stretch;
}

.preset-row .suggestion {
  flex: 1;
}

.add-preset {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.add-preset .input {
  flex: 1;
  min-width: 200px;
}

.suggestion {
  text-align: left;
  padding: 0.65rem 0.85rem;
  border-radius: 0.55rem;
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
  min-height: 80px;
}
.chat-list {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.chat-item {
  border: 1px solid var(--border);
  border-radius: 0.65rem;
  padding: 0.65rem 0.75rem;
  background: var(--main-bg);
  position: relative;
}
.chat-item.user {
  border-color: var(--accent);
}

.chat-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.35rem;
}

.chat-role {
  font-size: 0.75rem;
  color: var(--text-muted);
}

.chat-actions {
  display: flex;
  align-items: center;
  gap: 0.15rem;
  flex-shrink: 0;
}

.download-menu {
  display: flex;
  align-items: center;
  gap: 0.1rem;
  padding-right: 0.25rem;
  border-right: 1px solid var(--border);
  margin-right: 0.15rem;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: 0.45rem;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.icon-btn:hover {
  background: var(--accent-dim);
  color: var(--accent);
}

.icon-btn.danger:hover {
  background: rgba(220, 38, 38, 0.12);
  color: #dc2626;
}

.icon-btn.collect:hover {
  color: var(--accent);
}

.fmt-label {
  font-size: 0.65rem;
  font-weight: 700;
}

.reply {
  margin: 0;
  font-size: 0.9375rem;
  line-height: 1.55;
}

.reply :deep(p) {
  margin: 0.25rem 0 0.55rem;
}

.reply :deep(ul),
.reply :deep(ol) {
  margin: 0.35rem 0 0.65rem 1.1rem;
}

.reply :deep(h1),
.reply :deep(h2),
.reply :deep(h3),
.reply :deep(h4) {
  margin: 0.45rem 0 0.3rem;
  font-size: 1rem;
}

.reply :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 0.5rem 0 0.75rem;
}

.reply :deep(th),
.reply :deep(td) {
  border: 1px solid var(--border);
  padding: 0.4rem 0.5rem;
  text-align: left;
  vertical-align: top;
}

.reply :deep(th) {
  background: var(--accent-dim);
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
  align-items: center;
}

.attached-note {
  margin: 0;
  padding: 0.2rem 0.45rem;
  border: 1px solid var(--border);
  border-radius: 999px;
}
.report-box {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding: 0.85rem;
}

.report-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.5rem;
}

.download-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.dl-icon-btn {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 0.2rem;
  padding: 0.45rem 0.55rem;
  min-width: 56px;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--main-bg);
  color: var(--text);
  cursor: pointer;
  font-size: 0.65rem;
  text-transform: uppercase;
}

.dl-icon-btn:hover {
  border-color: var(--accent);
  background: var(--accent-dim);
}

.dl-key {
  font-weight: 600;
}

.area {
  resize: vertical;
  min-height: 80px;
}

.send {
  align-self: flex-end;
}

.side-panel {
  position: sticky;
  top: 1rem;
}

.collected-list {
  list-style: none;
  margin: 0;
  padding: 0;
  max-height: 420px;
  overflow: auto;
}

.collected-item {
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  padding: 0.5rem 0.6rem;
  margin-bottom: 0.5rem;
  font-size: 0.8rem;
}

.collected-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 0.35rem;
}

.collected-snippet {
  margin: 0.35rem 0 0;
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 0.72rem;
  color: var(--text-muted);
  max-height: 5.5rem;
  overflow: hidden;
}

.block-btn {
  width: 100%;
  margin-top: 0.5rem;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.55);
  display: grid;
  place-items: center;
  z-index: 60;
  padding: 1rem;
}

.annotate-modal {
  width: min(960px, 100%);
  max-height: 92vh;
  overflow: auto;
}

.annotate-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.annotate-head h3 {
  margin: 0;
}

.annotate-tools {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin: 0.75rem 0;
}

.radio-pill {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.85rem;
  cursor: pointer;
}

.annotate-canvas-wrap {
  position: relative;
  display: inline-block;
  max-width: 100%;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  overflow: hidden;
  background: #0f172a;
}

.annotate-img {
  display: block;
  max-width: 100%;
  height: auto;
  vertical-align: middle;
}

.annotate-canvas {
  position: absolute;
  left: 0;
  top: 0;
  cursor: crosshair;
}

.def {
  color: #dc2626;
}
.disc {
  color: #ea580c;
}

.btn.tiny {
  padding: 0.2rem 0.45rem;
  font-size: 0.75rem;
}

.tiny-btn {
  padding: 0.3rem 0.55rem;
  font-size: 0.75rem;
}

.annotation-list {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.annotation-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.marker-chip {
  width: 24px;
  height: 24px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  color: #fff;
  font-size: 0.72rem;
  font-weight: 700;
}

.marker-chip.deficiency {
  background: #dc2626;
}

.marker-chip.discrepancy {
  background: #ea580c;
}

.marker-input {
  flex: 1;
}
</style>
