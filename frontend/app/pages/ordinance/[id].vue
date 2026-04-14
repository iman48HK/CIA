<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const folderId = computed(() => Number(route.params.id))
const { apiFetch, base, token } = useApi()
const { me, loadMe } = useAuth()

interface FileRow {
  id: number
  title: string
  content_type?: string | null
  size_bytes?: number | null
  created_at: string
}

const files = ref<FileRow[]>([])
const uploadInput = ref<HTMLInputElement | null>(null)
const err = ref('')
const previewUrl = ref('')
const previewType = ref('')
const previewName = ref('')

async function load() {
  err.value = ''
  try {
    files.value = await apiFetch<FileRow[]>(`/ordinance/folders/${folderId.value}/files`)
  } catch (e: unknown) {
    err.value =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail || 'Failed to load ordinance files')
        : 'Failed to load ordinance files'
  }
}

onMounted(async () => {
  await loadMe()
  await load()
})

watch(folderId, load)

async function uploadFiles() {
  const picked = uploadInput.value?.files
  if (!picked?.length) return
  err.value = ''
  const fd = new FormData()
  for (const file of Array.from(picked)) {
    fd.append('files', file)
  }
  try {
    await apiFetch(`/ordinance/folders/${folderId.value}/upload`, {
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

async function openPreview(file: FileRow) {
  err.value = ''
  try {
    const res = await fetch(`${base()}/ordinance/files/${file.id}/content`, {
      headers: token.value ? { Authorization: `Bearer ${token.value}` } : {},
    })
    if (!res.ok) throw new Error('preview failed')
    const blob = await res.blob()
    if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
    previewUrl.value = URL.createObjectURL(blob)
    previewType.value = file.content_type || blob.type || 'application/octet-stream'
    previewName.value = file.title
  } catch {
    err.value = 'Failed to preview ordinance file'
  }
}

function closePreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  previewType.value = ''
  previewName.value = ''
}
</script>

<template>
  <div>
    <NuxtLink to="/ordinance" class="back">← Ordinance</NuxtLink>
    <h1>Ordinance Folder</h1>
    <p class="muted">Files in this folder</p>

    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="me?.role === 'admin'" class="card admin-add">
      <div class="inline">
        <input ref="uploadInput" type="file" class="input" multiple />
        <button type="button" class="btn btn-primary" @click="uploadFiles">Upload file(s)</button>
      </div>
    </div>

    <div v-if="!files.length" class="card empty">No files in this folder</div>
    <ul v-else class="list">
      <li v-for="f in files" :key="f.id" class="card file-row">
        <button type="button" class="linkish" @click="openPreview(f)">
          {{ f.title }}
          <small v-if="f.size_bytes" class="meta">({{ (f.size_bytes / 1024 / 1024).toFixed(2) }} MB)</small>
        </button>
        <button v-if="me?.role === 'admin'" type="button" class="btn btn-ghost danger" @click="removeFile(f.id)">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
          </svg>
        </button>
      </li>
    </ul>

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
.back {
  display: inline-block;
  margin-bottom: 1rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

h1 {
  margin: 0 0 0.35rem;
  font-size: 1.35rem;
}

.muted {
  color: var(--text-muted);
  margin: 0 0 1.25rem;
}

.admin-add {
  margin-bottom: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.inline {
  display: flex;
  gap: 0.5rem;
}

.inline .input {
  flex: 1;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.file-row {
  padding: 0.85rem 1rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}
.danger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.empty {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}

.err {
  color: #dc2626;
}
.linkish {
  border: none;
  background: transparent;
  color: var(--accent);
  text-align: left;
  cursor: pointer;
  padding: 0;
  font-size: 1rem;
  font-weight: 500;
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
