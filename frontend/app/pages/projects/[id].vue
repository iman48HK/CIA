<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const id = computed(() => Number(route.params.id))
const { apiFetch } = useApi()

interface Project {
  id: number
  name: string
  folder_count: number
  drawing_count: number
  file_count: number
}

interface Folder {
  id: number
  name: string
}

const project = ref<Project | null>(null)
const folders = ref<Folder[]>([])
const folderName = ref('')
const drawingTitle = ref('')
const fileName = ref('')
const err = ref('')

async function load() {
  err.value = ''
  try {
    project.value = await apiFetch<Project>(`/projects/${id.value}`)
    folders.value = await apiFetch<Folder[]>(`/projects/${id.value}/folders`)
  } catch {
    err.value = 'Project not found'
    project.value = null
  }
}

onMounted(load)
watch(id, load)

async function addFolder() {
  if (!folderName.value.trim()) return
  await apiFetch(`/projects/${id.value}/folders`, {
    method: 'POST',
    body: JSON.stringify({ name: folderName.value.trim() }),
  })
  folderName.value = ''
  await load()
}

async function addDrawing() {
  if (!drawingTitle.value.trim()) return
  await apiFetch(`/projects/${id.value}/drawings`, {
    method: 'POST',
    body: JSON.stringify({ title: drawingTitle.value.trim() }),
  })
  drawingTitle.value = ''
  await load()
}

async function addFile() {
  if (!fileName.value.trim()) return
  await apiFetch(`/projects/${id.value}/files`, {
    method: 'POST',
    body: JSON.stringify({ filename: fileName.value.trim() }),
  })
  fileName.value = ''
  await load()
}

async function removeProject() {
  if (!confirm('Delete this project and all related data?')) return
  await apiFetch(`/projects/${id.value}`, { method: 'DELETE' })
  await navigateTo('/projects')
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
            {{ project.folder_count }} folders · {{ project.drawing_count }} drawings ·
            {{ project.file_count }} files
          </p>
        </div>
        <button type="button" class="btn btn-ghost danger" @click="removeProject">Delete project</button>
      </header>

      <div class="cols">
        <section class="card block">
          <h2>Folders</h2>
          <ul class="list">
            <li v-for="f in folders" :key="f.id">{{ f.name }}</li>
            <li v-if="!folders.length" class="muted">No folders yet</li>
          </ul>
          <div class="inline">
            <input v-model="folderName" class="input" placeholder="Folder name" @keyup.enter="addFolder" />
            <button type="button" class="btn btn-primary" @click="addFolder">Add</button>
          </div>
        </section>

        <section class="card block">
          <h2>Drawings</h2>
          <p class="muted small">Register drawing records for this project.</p>
          <div class="inline">
            <input v-model="drawingTitle" class="input" placeholder="Drawing title" @keyup.enter="addDrawing" />
            <button type="button" class="btn btn-primary" @click="addDrawing">Add</button>
          </div>
        </section>

        <section class="card block">
          <h2>Uploaded files</h2>
          <p class="muted small">Track file names linked to this project.</p>
          <div class="inline">
            <input v-model="fileName" class="input" placeholder="File name" @keyup.enter="addFile" />
            <button type="button" class="btn btn-primary" @click="addFile">Add</button>
          </div>
        </section>
      </div>
    </template>

    <p v-else-if="err" class="err">{{ err }}</p>
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

.inline .input {
  flex: 1;
}

.err {
  color: #dc2626;
}
</style>
