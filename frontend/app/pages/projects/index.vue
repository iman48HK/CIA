<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Project {
  id: number
  name: string
  folder_count: number
  drawing_count: number
  file_count: number
}

const { apiFetch } = useApi()
const projects = ref<Project[]>([])
const newName = ref('')
const showNew = ref(false)
const err = ref('')

async function load() {
  try {
    projects.value = await apiFetch<Project[]>('/projects')
  } catch (e: unknown) {
    err.value = 'Failed to load projects'
  }
}

onMounted(load)

async function createProject() {
  if (!newName.value.trim()) return
  err.value = ''
  try {
    await apiFetch('/projects', {
      method: 'POST',
      body: JSON.stringify({ name: newName.value.trim() }),
    })
    newName.value = ''
    showNew.value = false
    await load()
  } catch {
    err.value = 'Could not create project'
  }
}
</script>

<template>
  <div>
    <header class="page-head">
      <div>
        <h1>My Projects</h1>
        <p class="muted">{{ projects.length }} projects</p>
      </div>
      <div class="actions">
        <button type="button" class="btn btn-outline" @click="showNew = !showNew">
          New Project
        </button>
      </div>
    </header>

    <p class="hint">Use <strong>New Project</strong> to create a workspace, then open it to manage folders, drawings, and files.</p>

    <div v-if="showNew" class="card new-box">
      <label class="field">
        <span>Project name</span>
        <input v-model="newName" class="input" placeholder="e.g. Riverside Tower" @keyup.enter="createProject" />
      </label>
      <div class="row">
        <button type="button" class="btn btn-primary" @click="createProject">Create</button>
        <button type="button" class="btn btn-ghost" @click="showNew = false">Cancel</button>
      </div>
    </div>

    <p v-if="err" class="err">{{ err }}</p>

    <div class="section-title">All Folders</div>

    <div v-if="!projects.length" class="card empty">
      <p>No projects found</p>
      <p class="muted">Create a new project to get started</p>
    </div>

    <ul v-else class="proj-grid">
      <li v-for="p in projects" :key="p.id" class="card proj-item">
        <NuxtLink :to="`/projects/${p.id}`" class="proj-link">
          <strong>{{ p.name }}</strong>
          <span class="meta">{{ p.folder_count }} folders · {{ p.drawing_count }} drawings · {{ p.file_count }} files</span>
        </NuxtLink>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.page-head {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.page-head h1 {
  margin: 0;
  font-size: 1.5rem;
}

.muted {
  margin: 0.25rem 0 0;
  color: var(--text-muted);
  font-size: 0.9rem;
}

.hint {
  color: var(--text-muted);
  font-size: 0.9rem;
  margin: 0 0 1.25rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.new-box {
  margin-bottom: 1.5rem;
  max-width: 420px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.75rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.row {
  display: flex;
  gap: 0.5rem;
}

.err {
  color: #dc2626;
}

.section-title {
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: var(--text-muted);
  font-size: 0.875rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.empty {
  text-align: center;
  padding: 2rem;
}

.empty p {
  margin: 0 0 0.35rem;
}

.proj-grid {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.proj-item {
  padding: 0;
  overflow: hidden;
}

.proj-link {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  padding: 1.25rem;
  color: inherit;
  text-decoration: none;
}

.proj-link:hover {
  background: var(--accent-dim);
  text-decoration: none;
}

.meta {
  font-size: 0.8125rem;
  color: var(--text-muted);
}
</style>
