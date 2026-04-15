<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const id = computed(() => Number(route.params.id))
const { apiFetch, base, token } = useApi()

interface Project {
  id: number
  name: string
  drawing_count: number
  file_count: number
  workspace_folder_id: number | null
  workspace_folder_name: string | null
}

interface WorkspaceFolder {
  id: number
  name: string
  project_count: number
}

interface UploadRow {
  id: number
  filename: string
  content_type: string
  size_bytes: number
  created_at: string
}

interface OrdinanceFolder {
  id: number
  code: string
  name: string
}

interface OrdinanceFile {
  id: number
  title: string
}

const project = ref<Project | null>(null)
const drawingUploads = ref<UploadRow[]>([])
const projectUploads = ref<UploadRow[]>([])
const ordinanceFolders = ref<OrdinanceFolder[]>([])
const workspaceFolders = ref<WorkspaceFolder[]>([])
const selectedWorkspaceFolderId = ref<number | null>(null)
const editingWorkspaceFolderName = ref('')
const ordinanceFiles = ref<OrdinanceFile[]>([])
const selectedOrdinanceFileIds = ref<number[]>([])
const drawingInput = ref<HTMLInputElement | null>(null)
const projectFileInput = ref<HTMLInputElement | null>(null)
const err = ref('')
const saveOrdinanceMessage = ref('')
const previewUrl = ref('')
const previewName = ref('')
const previewType = ref('')

async function load() {
  err.value = ''
  try {
    project.value = await apiFetch<Project>(`/projects/by-id/${id.value}`)
    workspaceFolders.value = await apiFetch<WorkspaceFolder[]>('/projects/workspaces/folders')
    selectedWorkspaceFolderId.value = project.value.workspace_folder_id
    const selectedFolder = workspaceFolders.value.find((wf) => wf.id === selectedWorkspaceFolderId.value)
    editingWorkspaceFolderName.value = selectedFolder?.name || ''
    drawingUploads.value = await apiFetch<UploadRow[]>(`/projects/by-id/${id.value}/drawings`)
    projectUploads.value = await apiFetch<UploadRow[]>(`/projects/by-id/${id.value}/project-files`)
    selectedOrdinanceFileIds.value = await apiFetch<number[]>(`/projects/by-id/${id.value}/ordinance-selections`)
    ordinanceFolders.value = await apiFetch<OrdinanceFolder[]>('/ordinance/folders')
    const allFiles: OrdinanceFile[] = []
    for (const f of ordinanceFolders.value) {
      const files = await apiFetch<OrdinanceFile[]>(`/ordinance/folders/${f.id}/files`)
      allFiles.push(...files)
    }
    ordinanceFiles.value = allFiles
    await nextTick()
    scrollToRouteHash()
  } catch {
    err.value = 'Project not found'
    project.value = null
  }
}

function scrollToRouteHash() {
  if (!import.meta.client || !route.hash) return
  nextTick(() => {
    const el = document.querySelector(route.hash)
    el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

onMounted(load)
watch(id, load)
watch(
  () => [route.hash, project.value?.id] as const,
  () => {
    if (project.value) scrollToRouteHash()
  }
)

async function saveProjectFolder() {
  if (!selectedWorkspaceFolderId.value) return
  await apiFetch(`/projects/by-id/${id.value}`, {
    method: 'PUT',
    body: JSON.stringify({ workspace_folder_id: selectedWorkspaceFolderId.value }),
  })
  await load()
}

async function saveWorkspaceFolderName() {
  if (!selectedWorkspaceFolderId.value || !editingWorkspaceFolderName.value.trim()) return
  await apiFetch(`/projects/workspaces/folders/${selectedWorkspaceFolderId.value}`, {
    method: 'PUT',
    body: JSON.stringify({ name: editingWorkspaceFolderName.value.trim() }),
  })
  await load()
}

async function uploadDrawings() {
  const files = drawingInput.value?.files
  if (!files?.length) return
  const fd = new FormData()
  for (const file of Array.from(files)) {
    fd.append('drawings', file)
  }
  await apiFetch(`/projects/by-id/${id.value}/drawings`, {
    method: 'POST',
    body: fd,
  })
  if (drawingInput.value) drawingInput.value.value = ''
  await load()
}

async function uploadProjectFiles() {
  const files = projectFileInput.value?.files
  if (!files?.length) return
  const fd = new FormData()
  for (const file of Array.from(files)) {
    fd.append('files', file)
  }
  await apiFetch(`/projects/by-id/${id.value}/files`, {
    method: 'POST',
    body: fd,
  })
  if (projectFileInput.value) projectFileInput.value.value = ''
  await load()
}

async function removeProject() {
  if (!confirm('Delete this project and all related data?')) return
  await apiFetch(`/projects/by-id/${id.value}`, { method: 'DELETE' })
  await navigateTo('/projects')
}

async function removeDrawing(uploadId: number) {
  if (!confirm('Delete this drawing file?')) return
  await apiFetch(`/projects/by-id/${id.value}/drawings/${uploadId}`, { method: 'DELETE' })
  await load()
}

async function removeProjectFile(uploadId: number) {
  if (!confirm('Delete this project file?')) return
  await apiFetch(`/projects/by-id/${id.value}/project-files/${uploadId}`, { method: 'DELETE' })
  await load()
}

function toggleOrdinance(fileId: number) {
  if (selectedOrdinanceFileIds.value.includes(fileId)) {
    selectedOrdinanceFileIds.value = selectedOrdinanceFileIds.value.filter((i) => i !== fileId)
    return
  }
  selectedOrdinanceFileIds.value = [...selectedOrdinanceFileIds.value, fileId]
}

async function saveOrdinanceSelection() {
  saveOrdinanceMessage.value = ''
  try {
    await apiFetch(`/projects/by-id/${id.value}/ordinance-selections`, {
      method: 'PUT',
      body: JSON.stringify({ ordinance_file_ids: selectedOrdinanceFileIds.value }),
    })
    saveOrdinanceMessage.value = 'Selection saved.'
  } catch {
    saveOrdinanceMessage.value = 'At least one ordinance file must remain selected.'
  }
}

async function openPreview(kind: 'drawing' | 'project-file', file: UploadRow) {
  const path =
    kind === 'drawing'
      ? `/projects/by-id/${id.value}/drawings/${file.id}/content`
      : `/projects/by-id/${id.value}/project-files/${file.id}/content`
  const res = await fetch(`${base()}${path}`, {
    headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
  })
  if (!res.ok) {
    err.value = 'Failed to preview file'
    return
  }
  const blob = await res.blob()
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = URL.createObjectURL(blob)
  previewName.value = file.filename
  previewType.value = file.content_type || blob.type || 'application/octet-stream'
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  previewName.value = ''
  previewType.value = ''
}

function fmtMb(row: UploadRow) {
  return (row.size_bytes / 1024 / 1024).toFixed(2)
}
</script>

<template>
  <div class="page">
    <NuxtLink to="/projects" class="back">← My Projects</NuxtLink>

    <template v-if="project">
      <header class="page-head">
        <div>
          <h1>{{ project.name }}</h1>
          <p class="muted meta-line">
            {{ project.drawing_count }} drawings · {{ project.file_count }} files
          </p>
        </div>
        <button type="button" class="icon-btn danger" title="Delete project" @click="removeProject">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
          </svg>
        </button>
      </header>

      <div class="workspace card">
        <section id="project-folder" class="ws-section">
          <div class="ws-section-title">Workspace folder</div>
          <div class="ws-row">
            <select v-model.number="selectedWorkspaceFolderId" class="input ws-grow">
              <option :value="null" disabled>Select folder</option>
              <option v-for="wf in workspaceFolders" :key="wf.id" :value="wf.id">
                {{ wf.name }} ({{ wf.project_count }} projects)
              </option>
            </select>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="!selectedWorkspaceFolderId || selectedWorkspaceFolderId === project.workspace_folder_id"
              @click="saveProjectFolder"
            >
              Save
            </button>
          </div>
          <div class="ws-row ws-row-tight">
            <input v-model="editingWorkspaceFolderName" class="input ws-grow" placeholder="Folder display name" />
            <button type="button" class="btn btn-outline" :disabled="!selectedWorkspaceFolderId" @click="saveWorkspaceFolderName">
              Rename folder
            </button>
          </div>
        </section>

        <section id="project-drawings" class="ws-section">
          <div class="ws-section-head">
            <div>
              <div class="ws-section-title">Drawings</div>
              <p class="muted tiny">Required for analysis. Each file up to 10 MB.</p>
            </div>
            <div class="ws-upload-inline">
              <input ref="drawingInput" type="file" class="visually-hidden" multiple />
              <button type="button" class="btn btn-outline btn-sm" @click="drawingInput?.click()">Choose files</button>
              <button type="button" class="btn btn-primary btn-sm" @click="uploadDrawings">Upload</button>
            </div>
          </div>
          <ul class="ws-list">
            <li v-for="f in drawingUploads" :key="f.id" class="ws-list-row">
              <button type="button" class="file-link" @click="openPreview('drawing', f)">{{ f.filename }}</button>
              <span class="muted tiny ws-meta">{{ fmtMb(f) }} MB</span>
              <button type="button" class="icon-btn danger tiny" title="Remove" @click="removeDrawing(f.id)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                </svg>
              </button>
            </li>
            <li v-if="!drawingUploads.length" class="ws-empty">No drawings yet — add files above.</li>
          </ul>
        </section>

        <section id="project-files" class="ws-section">
          <div class="ws-section-head">
            <div>
              <div class="ws-section-title">Project files</div>
              <p class="muted tiny">Optional supporting files (each up to 10 MB).</p>
            </div>
            <div class="ws-upload-inline">
              <input ref="projectFileInput" type="file" class="visually-hidden" multiple />
              <button type="button" class="btn btn-outline btn-sm" @click="projectFileInput?.click()">Choose files</button>
              <button type="button" class="btn btn-primary btn-sm" @click="uploadProjectFiles">Upload</button>
            </div>
          </div>
          <ul class="ws-list">
            <li v-for="f in projectUploads" :key="f.id" class="ws-list-row">
              <button type="button" class="file-link" @click="openPreview('project-file', f)">{{ f.filename }}</button>
              <span class="muted tiny ws-meta">{{ fmtMb(f) }} MB</span>
              <button type="button" class="icon-btn danger tiny" title="Remove" @click="removeProjectFile(f.id)">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                </svg>
              </button>
            </li>
            <li v-if="!projectUploads.length" class="ws-empty">No project files — upload if needed.</li>
          </ul>
        </section>

        <section id="project-ordinance" class="ws-section ws-section-last">
          <div class="ws-section-head">
            <div>
              <div class="ws-section-title">Ordinance documents</div>
              <p class="muted tiny">Select at least one document for AI and compliance context.</p>
            </div>
            <button type="button" class="btn btn-primary btn-sm" @click="saveOrdinanceSelection">Save selection</button>
          </div>
          <p v-if="saveOrdinanceMessage" class="save-hint muted tiny">{{ saveOrdinanceMessage }}</p>
          <ul class="ws-list ordinance-scroll">
            <li v-for="o in ordinanceFiles" :key="o.id" class="ws-list-row ordinance-row">
              <label class="ord-label">
                <input type="checkbox" :checked="selectedOrdinanceFileIds.includes(o.id)" @change="toggleOrdinance(o.id)" />
                <span>{{ o.title }}</span>
              </label>
            </li>
            <li v-if="!ordinanceFiles.length" class="ws-empty">No ordinance files in the library. Ask an admin to add documents.</li>
          </ul>
        </section>
      </div>
    </template>

    <p v-else-if="err" class="err">{{ err }}</p>

    <div v-if="previewUrl" class="modal-backdrop" @click.self="closePreview">
      <div class="card modal-card">
        <div class="modal-head">
          <strong>{{ previewName }}</strong>
          <button type="button" class="btn btn-ghost" @click="closePreview">Close</button>
        </div>
        <img v-if="previewType.startsWith('image/')" :src="previewUrl" class="preview-media" />
        <iframe v-else-if="previewType.includes('pdf')" :src="previewUrl" class="preview-media" />
        <div v-else class="muted">Preview not supported for this file type. Use browser download/open.</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 720px;
}

.back {
  display: inline-block;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.page-head {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.25rem;
}

.page-head h1 {
  margin: 0;
  font-size: 1.5rem;
}

.muted {
  color: var(--text-muted);
}

.meta-line {
  margin: 0.35rem 0 0;
  font-size: 0.9rem;
}

.tiny {
  font-size: 0.8125rem;
  margin: 0.2rem 0 0;
}

.workspace {
  padding: 0;
  overflow: hidden;
}

.ws-section {
  padding: 1rem 1.1rem;
  border-bottom: 1px solid var(--border);
}

.ws-section-last {
  border-bottom: none;
}

.ws-section-title {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}

.ws-section-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.65rem;
}

.ws-section-head .ws-section-title {
  margin-bottom: 0.15rem;
}

.ws-upload-inline {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
  align-items: center;
}

.ws-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
  margin-bottom: 0.5rem;
}

.ws-row:last-child {
  margin-bottom: 0;
}

.ws-row-tight {
  margin-bottom: 0;
}

.ws-grow {
  flex: 1;
  min-width: 160px;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.btn-sm {
  font-size: 0.8125rem;
  padding: 0.35rem 0.65rem;
}

.ws-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.ws-list-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.45rem 0;
  border-top: 1px solid var(--border);
}

.ws-list-row:first-child {
  border-top: none;
}

.file-link {
  flex: 1;
  min-width: 0;
  text-align: left;
  border: none;
  background: none;
  padding: 0;
  font: inherit;
  font-weight: 500;
  color: var(--accent);
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.file-link:hover {
  text-decoration: underline;
}

.ws-meta {
  flex-shrink: 0;
}

.ws-empty {
  padding: 0.65rem 0 0.15rem;
  color: var(--text-muted);
  font-size: 0.875rem;
}

.ordinance-scroll {
  max-height: 280px;
  overflow: auto;
  margin-top: 0.25rem;
  border: 1px solid var(--border);
  border-radius: 0.45rem;
  padding: 0 0.5rem;
}

.ordinance-row {
  padding-left: 0.15rem;
  padding-right: 0.15rem;
}

.ord-label {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  cursor: pointer;
  font-size: 0.9rem;
  line-height: 1.4;
  flex: 1;
}

.save-hint {
  margin: 0 0 0.35rem;
}

.err {
  color: #dc2626;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: 1px solid var(--border);
  border-radius: 0.45rem;
  background: var(--main-bg);
  color: var(--text-muted);
  cursor: pointer;
}

.icon-btn:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: var(--accent-dim);
}

.icon-btn.danger:hover {
  color: #dc2626;
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.icon-btn.tiny {
  width: 30px;
  height: 30px;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.45);
  display: grid;
  place-items: center;
  z-index: 40;
  padding: 1rem;
}

.modal-card {
  width: min(900px, 100%);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.preview-media {
  width: 100%;
  height: min(75vh, 760px);
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  object-fit: contain;
  background: #fff;
}
</style>
