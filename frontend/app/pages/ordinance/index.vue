<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Folder {
  id: number
  code: string
  name: string
  file_count: number
}

interface FileRow {
  id: number
  folder_id: number
  title: string
  content_type?: string | null
  size_bytes?: number | null
  created_at: string
}

interface OrdinanceDocumentRow extends FileRow {
  folder_code: string
  folder_name: string
}

const { apiFetch, base, token } = useApi()
const { me, loadMe } = useAuth()
const folders = ref<Folder[]>([])
const code = ref('')
const name = ref('')
const err = ref('')
const showAddFolderModal = ref(false)
const editingFolderId = ref<number | null>(null)
const editingFolderName = ref('')
const uploadFolderId = ref<number | null>(null)
const uploadInput = ref<HTMLInputElement | null>(null)
const documents = ref<OrdinanceDocumentRow[]>([])
const previewUrl = ref('')
const previewType = ref('')
const previewName = ref('')
const previewMaximized = ref(false)
const previewModalEl = ref<HTMLElement | null>(null)
const previewWidth = ref(1920)
const previewHeight = ref(680)
const folderSortAsc = ref(true)
const folderFilterId = ref<number | null>(null)

async function load() {
  const fetchedFolders = await apiFetch<Folder[]>('/ordinance/folders')
  folders.value = fetchedFolders
  if (!uploadFolderId.value && fetchedFolders.length) {
    uploadFolderId.value = fetchedFolders[0].id
  }
  const grouped = await Promise.all(
    fetchedFolders.map(async (folder) => {
      const rows = await apiFetch<FileRow[]>(`/ordinance/folders/${folder.id}/files`)
      return rows.map((row) => ({
        ...row,
        folder_code: folder.code,
        folder_name: folder.name,
      }))
    })
  )
  documents.value = grouped.flat()
}

onMounted(async () => {
  await loadMe()
  await load()
})

const visibleDocuments = computed(() => {
  let rows = documents.value
  if (folderFilterId.value != null) {
    rows = rows.filter((d) => d.folder_id === folderFilterId.value)
  }
  return [...rows].sort((a, b) => {
    const folderCmp = a.folder_name.localeCompare(b.folder_name)
    if (folderCmp !== 0) return folderSortAsc.value ? folderCmp : -folderCmp
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
})

function toggleFolderFilter(folderId: number) {
  folderFilterId.value = folderFilterId.value === folderId ? null : folderId
}

function docHasUpload(doc: OrdinanceDocumentRow) {
  return typeof doc.size_bytes === 'number' && doc.size_bytes > 0
}

function toggleFolderColumnSort() {
  folderSortAsc.value = !folderSortAsc.value
}

function openAddFolderModal() {
  err.value = ''
  code.value = ''
  name.value = ''
  showAddFolderModal.value = true
}

function closeAddFolderModal() {
  showAddFolderModal.value = false
}

async function addFolder() {
  if (!code.value.trim() || !name.value.trim()) return
  err.value = ''
  try {
    await apiFetch('/ordinance/folders', {
      method: 'POST',
      body: JSON.stringify({ code: code.value.trim(), name: name.value.trim() }),
    })
    code.value = ''
    name.value = ''
    closeAddFolderModal()
    await load()
  } catch {
    err.value = 'Unable to create folder'
  }
}

async function removeFolder(id: number) {
  if (!confirm('Delete this folder and all files inside it?')) return
  await apiFetch(`/ordinance/folders/${id}`, { method: 'DELETE' })
  if (uploadFolderId.value === id) {
    uploadFolderId.value = folders.value.find((f) => f.id !== id)?.id ?? null
  }
  await load()
}

function startEditFolder(folder: Folder) {
  editingFolderId.value = folder.id
  editingFolderName.value = folder.name
}

function cancelEditFolder() {
  editingFolderId.value = null
  editingFolderName.value = ''
}

async function saveEditFolder(folderId: number) {
  const next = editingFolderName.value.trim()
  if (!next) return
  err.value = ''
  try {
    await apiFetch(`/ordinance/folders/${folderId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name: next }),
    })
    cancelEditFolder()
    await load()
  } catch {
    err.value = 'Unable to rename folder'
  }
}

async function uploadFiles() {
  const picked = uploadInput.value?.files
  if (!picked?.length) return
  if (!uploadFolderId.value) {
    err.value = 'Choose or create an ordinance folder before uploading files.'
    if (uploadInput.value) uploadInput.value.value = ''
    return
  }
  err.value = ''
  const fd = new FormData()
  for (const file of Array.from(picked)) {
    fd.append('files', file)
  }
  try {
    await apiFetch(`/ordinance/folders/${uploadFolderId.value}/upload`, {
      method: 'POST',
      body: fd,
    })
    if (uploadInput.value) uploadInput.value.value = ''
    await load()
  } catch (e: unknown) {
    err.value =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail || 'Failed to upload ordinance documents')
        : 'Failed to upload ordinance documents'
  }
}

function triggerUpload() {
  if (!uploadFolderId.value) {
    err.value = 'Choose or create an ordinance folder before uploading files.'
    return
  }
  uploadInput.value?.click()
}

async function removeFile(fileId: number) {
  if (!confirm('Delete this ordinance document?')) return
  try {
    await apiFetch(`/ordinance/files/${fileId}`, { method: 'DELETE' })
    await load()
  } catch (e: unknown) {
    err.value =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail || 'Failed to delete ordinance document')
        : 'Failed to delete ordinance document'
  }
}

async function openPreview(file: OrdinanceDocumentRow) {
  err.value = ''
  if (!docHasUpload(file)) {
    err.value = 'This document has no uploaded file to preview yet.'
    return
  }
  try {
    const res = await fetch(`${base()}/ordinance/files/${file.id}/content`, {
      headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
    })
    if (!res.ok) {
      let detail = `Could not load file (${res.status}).`
      try {
        const j = (await res.json()) as { detail?: unknown }
        if (typeof j.detail === 'string') detail = j.detail
      } catch {
        /* ignore */
      }
      throw new Error(detail)
    }
    const blob = await res.blob()
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = URL.createObjectURL(blob)
    previewType.value = file.content_type || blob.type || 'application/octet-stream'
    previewName.value = file.title
    previewMaximized.value = false
    previewWidth.value = Math.min(1920, Math.max(640, Math.floor(window.innerWidth * 0.9)))
    previewHeight.value = Math.min(820, Math.max(420, Math.floor(window.innerHeight * 0.82)))
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Failed to preview ordinance file'
  }
}

function togglePreviewMaximized() {
  previewMaximized.value = !previewMaximized.value
}

function startPreviewResize(e: MouseEvent) {
  if (previewMaximized.value) return
  e.preventDefault()
  const startX = e.clientX
  const startY = e.clientY
  const startW = previewWidth.value
  const startH = previewHeight.value
  const onMove = (ev: MouseEvent) => {
    const nextW = startW + (ev.clientX - startX)
    const nextH = startH + (ev.clientY - startY)
    previewWidth.value = Math.min(window.innerWidth - 32, Math.max(560, nextW))
    previewHeight.value = Math.min(window.innerHeight - 32, Math.max(380, nextH))
  }
  const onUp = () => {
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', onUp)
  }
  window.addEventListener('mousemove', onMove)
  window.addEventListener('mouseup', onUp)
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  previewType.value = ''
  previewName.value = ''
  previewMaximized.value = false
}
</script>

<template>
  <div>
    <header class="page-head">
      <div class="head-text">
        <h1>Ordinance Documents</h1>
        <p class="muted">Browse and manage all ordinance documents in one list</p>
      </div>
    </header>

    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="me?.role === 'admin'" class="card folder-strip">
      <div class="folder-strip-head">
        <span class="strip-label">Folders</span>
        <button type="button" class="icon-btn tiny" title="Add folder" @click="openAddFolderModal">
          <svg class="icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
            <line x1="12" y1="11" x2="12" y2="17" />
            <line x1="9" y1="14" x2="15" y2="14" />
          </svg>
        </button>
      </div>
      <div class="folder-chips">
        <div v-for="f in folders" :key="f.id" class="folder-chip">
          <template v-if="editingFolderId === f.id">
            <input
              v-model="editingFolderName"
              class="input chip-input"
              @keydown.enter.stop.prevent="saveEditFolder(f.id)"
            />
            <button type="button" class="icon-btn tiny" title="Save" @click="saveEditFolder(f.id)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.2l-3.5-3.5L4 14.2l5 5L20 8.2 18.5 6.8z" />
              </svg>
            </button>
            <button type="button" class="icon-btn tiny" title="Cancel" @click="cancelEditFolder">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.3 5.71L12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.7 2.88 18.29 9.17 12 2.88 5.71 4.29 4.3l6.3 6.29 6.29-6.29z" />
              </svg>
            </button>
          </template>
          <template v-else>
            <span class="chip-title">{{ f.code }} · {{ f.name }}</span>
            <span class="chip-meta">({{ f.file_count }})</span>
            <button type="button" class="icon-btn tiny" title="Rename folder" @click="startEditFolder(f)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 17.25V21h3.75l11-11-3.75-3.75-11 11zM20.71 7.04a1 1 0 000-1.41L18.37 3.29a1 1 0 00-1.41 0L15.13 5.12l3.75 3.75 1.83-1.83z" />
              </svg>
            </button>
            <button type="button" class="icon-btn tiny danger" title="Delete folder" @click="removeFolder(f.id)">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
              </svg>
            </button>
          </template>
        </div>
      </div>
      <p v-if="!folders.length" class="muted small">No folders yet. Click the folder+ button to create your first folder.</p>
    </div>

    <div class="card docs-card">
      <div class="docs-head">
        <div class="docs-head-main">
          <strong>All documents</strong>
          <p class="muted small">
            Click a document name to preview when a file is uploaded. Click a folder name to filter this list. Use the folder
            column header to change sort order.
          </p>
          <p v-if="folderFilterId != null" class="filter-banner muted small">
            Showing one folder only.
            <button type="button" class="link-btn" @click="folderFilterId = null">Show all documents</button>
          </p>
        </div>
        <div v-if="me?.role === 'admin'" class="docs-head-tools">
          <select
            v-if="folders.length > 1"
            v-model.number="uploadFolderId"
            class="input upload-folder-select"
            title="Upload target folder"
          >
            <option :value="null" disabled>Upload to…</option>
            <option v-for="f in folders" :key="`up-${f.id}`" :value="f.id">{{ f.code }} · {{ f.name }}</option>
          </select>
          <input ref="uploadInput" type="file" class="hidden-file" multiple @change="uploadFiles" />
          <button
            type="button"
            class="icon-btn head-icon"
            :disabled="!uploadFolderId"
            :title="uploadFolderId ? 'Add document(s)' : 'Create/select a folder first'"
            @click="triggerUpload"
          >
            <svg class="icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
              <polyline points="14 2 14 8 20 8" />
              <line x1="12" y1="18" x2="12" y2="12" />
              <line x1="9" y1="15" x2="15" y2="15" />
            </svg>
          </button>
        </div>
      </div>

      <div v-if="!visibleDocuments.length" class="empty">No ordinance documents found.</div>
      <table v-else class="docs-table">
        <thead>
          <tr>
            <th>Document name</th>
            <th>Upload time</th>
            <th>
              <button type="button" class="th-sort" @click="toggleFolderColumnSort">
                Folder name
                <span class="sort-hint">{{ folderSortAsc ? 'A–Z' : 'Z–A' }}</span>
              </button>
            </th>
            <th v-if="me?.role === 'admin'">Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="doc in visibleDocuments" :key="doc.id">
            <td>
              <button
                v-if="docHasUpload(doc)"
                type="button"
                class="doc-title"
                @click="openPreview(doc)"
              >
                {{ doc.title }}
              </button>
              <span v-else class="doc-title doc-title-dim" :title="'No file uploaded — preview unavailable'">{{ doc.title }}</span>
            </td>
            <td class="cell-muted">{{ new Date(doc.created_at).toLocaleString() }}</td>
            <td>
              <button
                type="button"
                class="folder-filter-link"
                :class="{ active: folderFilterId === doc.folder_id }"
                @click="toggleFolderFilter(doc.folder_id)"
              >
                {{ doc.folder_name }}
              </button>
            </td>
            <td v-if="me?.role === 'admin'">
              <div class="row-actions">
                <button type="button" class="icon-btn tiny danger" title="Delete document" @click="removeFile(doc.id)">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                  </svg>
                </button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <p v-if="!folders.length" class="muted">No ordinance folders configured.</p>

    <div v-if="showAddFolderModal" class="modal-backdrop" @click.self="closeAddFolderModal">
      <div class="card modal-card">
        <div class="modal-head">
          <h3>Add folder</h3>
          <button type="button" class="btn btn-ghost" @click="closeAddFolderModal">Close</button>
        </div>
        <label class="field">
          <span>Code</span>
          <input v-model="code" class="input" placeholder="e.g. HK-BUILD-001" @keydown.enter.prevent="addFolder" />
        </label>
        <label class="field">
          <span>Folder name</span>
          <input v-model="name" class="input" placeholder="Folder name" @keydown.enter.prevent="addFolder" />
        </label>
        <div class="modal-actions">
          <button type="button" class="btn btn-primary" @click="addFolder">Create folder</button>
          <button type="button" class="btn btn-ghost" @click="closeAddFolderModal">Cancel</button>
        </div>
      </div>
    </div>

    <div v-if="previewUrl" class="modal-backdrop" @click.self="closePreview">
      <div
        ref="previewModalEl"
        class="card modal-card preview-modal"
        :class="{ maximized: previewMaximized }"
        :style="previewMaximized ? undefined : { width: `${previewWidth}px`, height: `${previewHeight}px` }"
      >
        <div class="modal-head">
          <strong>{{ previewName }}</strong>
          <div class="preview-head-actions">
            <button type="button" class="btn btn-ghost" @click="togglePreviewMaximized">
              {{ previewMaximized ? 'Restore' : 'Maximize' }}
            </button>
            <button type="button" class="btn btn-ghost" @click="closePreview">Close</button>
          </div>
        </div>
        <img v-if="previewType.startsWith('image/')" :src="previewUrl" class="preview-media" />
        <iframe v-else-if="previewType.includes('pdf')" :src="previewUrl" class="preview-media" />
        <div v-else class="muted">Preview not supported for this file type. Use browser download/open.</div>
        <button
          v-if="!previewMaximized"
          type="button"
          class="preview-resize-handle"
          title="Drag to resize"
          aria-label="Resize preview window"
          @mousedown="startPreviewResize"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.head-text h1 {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
}

.muted {
  margin: 0;
  color: var(--text-muted);
}

.small {
  font-size: 0.8125rem;
  margin: 0.25rem 0 0;
}

.upload-folder-select {
  width: clamp(220px, 32vw, 440px);
  min-width: 220px;
  max-width: 100%;
  font-size: 0.8125rem;
  padding: 0.35rem 0.5rem;
}

.hidden-file {
  display: none;
}

.head-icon .icon-svg {
  width: 22px;
  height: 22px;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
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

.icon-btn.tiny {
  width: 30px;
  height: 30px;
}

.icon-btn.danger:hover {
  color: #dc2626;
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.err {
  color: #dc2626;
  margin: 0 0 0.75rem;
}

.folder-strip {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.folder-strip-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.strip-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.folder-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.folder-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.5rem;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  background: var(--main-bg);
  font-size: 0.8125rem;
}

.chip-title {
  font-weight: 500;
}

.chip-meta {
  color: var(--text-muted);
  font-size: 0.75rem;
}

.chip-input {
  min-width: 140px;
  padding: 0.25rem 0.4rem;
  font-size: 0.8125rem;
}

.docs-card {
  padding: 0.85rem 1rem 1rem;
}

.docs-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.docs-head-main {
  flex: 1;
  min-width: 200px;
}

.docs-head-tools {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex: 1;
  justify-content: flex-end;
  min-width: 280px;
}

.filter-banner {
  margin: 0.4rem 0 0;
}

.link-btn {
  border: none;
  background: none;
  padding: 0;
  margin-left: 0.35rem;
  font: inherit;
  font-size: inherit;
  color: var(--accent);
  cursor: pointer;
  text-decoration: underline;
  text-underline-offset: 2px;
}

.link-btn:hover {
  color: var(--text);
}

.docs-table {
  width: 100%;
  border-collapse: collapse;
}

.docs-table th,
.docs-table td {
  border-top: 1px solid var(--border);
  padding: 0.55rem 0.4rem;
  text-align: left;
  vertical-align: middle;
}

.docs-table th {
  border-top: none;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
}

.th-sort {
  border: none;
  background: transparent;
  font: inherit;
  color: inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.th-sort:hover {
  color: var(--accent);
}

.sort-hint {
  font-weight: 500;
  color: var(--accent);
  text-transform: none;
  letter-spacing: normal;
}

.doc-title {
  border: none;
  background: none;
  padding: 0;
  margin: 0;
  font: inherit;
  font-weight: 400;
  color: var(--accent);
  text-align: left;
  cursor: pointer;
  text-decoration: none;
}

.doc-title:hover {
  text-decoration: underline;
}

.doc-title-dim {
  color: var(--text-muted);
  font-weight: 400;
}

.folder-filter-link {
  border: none;
  background: none;
  padding: 0;
  margin: 0;
  font: inherit;
  font-size: inherit;
  color: var(--accent);
  cursor: pointer;
  text-align: left;
  text-decoration: none;
}

.folder-filter-link:hover {
  text-decoration: underline;
}

.folder-filter-link.active {
  font-weight: 600;
  text-decoration: underline;
}

.cell-muted {
  color: var(--text-muted);
  font-size: 0.875rem;
}

.row-actions {
  display: flex;
  gap: 0.35rem;
  align-items: center;
}

.empty {
  padding: 1.5rem 0;
  color: var(--text-muted);
  text-align: center;
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
  width: min(480px, 100%);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}

.preview-head-actions {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
}

.preview-modal {
  width: min(1920px, 95vw);
  height: min(82vh, 820px);
  overflow: auto;
  position: relative;
  min-width: 560px;
  min-height: 380px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 32px);
}

.preview-modal.maximized {
  width: 96vw;
  height: 92vh;
  max-width: 96vw;
  max-height: 92vh;
  resize: none;
}

.modal-head h3 {
  margin: 0;
  font-size: 1.1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.modal-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

.preview-media {
  width: 100%;
  height: calc(100% - 52px);
  min-height: 360px;
  border: 1px solid var(--border);
  border-radius: 0.5rem;
  object-fit: contain;
  background: #fff;
}

.preview-resize-handle {
  position: absolute;
  right: 6px;
  bottom: 6px;
  width: 18px;
  height: 18px;
  border: none;
  background:
    linear-gradient(135deg, transparent 45%, var(--text-muted) 46%, var(--text-muted) 54%, transparent 55%),
    linear-gradient(135deg, transparent 62%, var(--text-muted) 63%, var(--text-muted) 71%, transparent 72%);
  opacity: 0.7;
  cursor: nwse-resize;
  padding: 0;
}

.preview-resize-handle:hover {
  opacity: 1;
}

@media (max-width: 720px) {
  .docs-head-tools {
    width: 100%;
    justify-content: flex-end;
  }
  .upload-folder-select {
    flex: 1;
    min-width: 0;
    max-width: none;
  }
  .docs-table {
    display: block;
    overflow-x: auto;
  }
}
</style>
