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
  } catch {
    err.value = 'Project not found'
    project.value = null
  }
}

onMounted(load)
watch(id, load)

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
    selectedOrdinanceFileIds.value = selectedOrdinanceFileIds.value.filter((id) => id !== fileId)
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
</script>

<template>
  <div>
    <NuxtLink to="/projects" class="back">← My Projects</NuxtLink>

    <template v-if="project">
      <header class="page-head">
        <div>
          <h1>{{ project.name }}</h1>
          <p class="muted">
            {{ project.drawing_count }} drawings ·
            {{ project.file_count }} files
          </p>
        </div>
        <button type="button" class="btn btn-ghost danger" @click="removeProject">Delete project</button>
      </header>

      <div class="cols">
        <section class="card block">
          <h2>Drawings</h2>
          <p class="muted small">Upload one or more drawing files (required, each <= 10MB).</p>
          <div class="inline upload">
            <input ref="drawingInput" type="file" class="input" multiple />
            <button type="button" class="btn btn-primary" @click="uploadDrawings">Upload</button>
          </div>
          <ul class="list">
            <li v-for="f in drawingUploads" :key="f.id" class="list-row">
              <button type="button" class="linkish" @click="openPreview('drawing', f)">
                {{ f.filename }} ({{ (f.size_bytes / 1024 / 1024).toFixed(2) }} MB)
              </button>
              <button type="button" class="btn btn-ghost danger" @click="removeDrawing(f.id)">Delete</button>
            </li>
            <li v-if="!drawingUploads.length" class="muted">No drawings uploaded yet</li>
          </ul>
        </section>

        <section class="card block">
          <h2>Project Files (Optional)</h2>
          <p class="muted small">Upload project files (each <= 10MB).</p>
          <div class="inline upload">
            <input ref="projectFileInput" type="file" class="input" multiple />
            <button type="button" class="btn btn-primary" @click="uploadProjectFiles">Upload</button>
          </div>
          <ul class="list">
            <li v-for="f in projectUploads" :key="f.id" class="list-row">
              <button type="button" class="linkish" @click="openPreview('project-file', f)">
                {{ f.filename }} ({{ (f.size_bytes / 1024 / 1024).toFixed(2) }} MB)
              </button>
              <button type="button" class="btn btn-ghost danger" @click="removeProjectFile(f.id)">Delete</button>
            </li>
            <li v-if="!projectUploads.length" class="muted">No project files uploaded</li>
          </ul>
        </section>

        <section class="card block">
          <h2>Selected Ordinance Files (Required)</h2>
          <p class="muted small">Select one or more ordinance files. You can unselect and save changes.</p>
          <ul class="list ordinance-list">
            <li v-for="o in ordinanceFiles" :key="o.id" class="list-row">
              <label class="check">
                <input
                  type="checkbox"
                  :checked="selectedOrdinanceFileIds.includes(o.id)"
                  @change="toggleOrdinance(o.id)"
                />
                <span>{{ o.title }}</span>
              </label>
            </li>
            <li v-if="!ordinanceFiles.length" class="muted">No ordinance files available. Ask admin to add them.</li>
          </ul>
          <div class="inline">
            <button type="button" class="btn btn-primary" @click="saveOrdinanceSelection">Save Selection</button>
            <span class="muted small">{{ saveOrdinanceMessage }}</span>
          </div>
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
  margin-bottom: 1.5rem;
}

.page-head h1 {
  margin: 0;
  font-size: 1.5rem;
}

.muted {
  color: var(--text-muted);
  margin: 0.35rem 0 0;
}

.muted.small {
  font-size: 0.875rem;
  margin: 0 0 0.75rem;
}

.danger {
  color: #dc2626 !important;
}

.cols {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 1rem;
}

.block h2 {
  margin: 0 0 0.75rem;
  font-size: 1rem;
}

.list {
  margin: 0 0 1rem;
  padding-left: 1.25rem;
}

.inline {
  display: flex;
  gap: 0.5rem;
}
.inline.upload {
  margin-bottom: 0.75rem;
}

.inline .input {
  flex: 1;
}

.list-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
  margin-bottom: 0.4rem;
}

.check {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.ordinance-list {
  max-height: 220px;
  overflow: auto;
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
