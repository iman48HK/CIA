<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Project {
  id: number
  name: string
  folder_count: number
  drawing_count: number
  file_count: number
  workspace_folder_name?: string | null
}

interface WorkspaceFolder {
  id: number
  name: string
  project_count: number
}

const { apiFetch } = useApi()
const projects = ref<Project[]>([])
const newName = ref('')
const newWorkspaceName = ref('')
const selectedWorkspaceFolderId = ref<number | null>(null)
const workspaceFolders = ref<WorkspaceFolder[]>([])
const showNewProject = ref(false)
const showFolderManager = ref(false)
const err = ref('')
const editingFolderId = ref<number | null>(null)
const editingFolderName = ref('')

async function load() {
  try {
    workspaceFolders.value = await apiFetch<WorkspaceFolder[]>('/projects/workspaces/folders')
    projects.value = await apiFetch<Project[]>('/projects')
    if (!selectedWorkspaceFolderId.value && workspaceFolders.value.length) {
      selectedWorkspaceFolderId.value = workspaceFolders.value[0].id
    }
  } catch (e: unknown) {
    err.value = 'Failed to load folders/projects'
  }
}

onMounted(load)

async function createProject() {
  if (!newName.value.trim() || !selectedWorkspaceFolderId.value) return
  err.value = ''
  try {
    await apiFetch('/projects', {
      method: 'POST',
      body: JSON.stringify({
        name: newName.value.trim(),
        workspace_folder_id: selectedWorkspaceFolderId.value,
      }),
    })
    newName.value = ''
    showNewProject.value = false
    await load()
  } catch {
    err.value = 'Could not create project. Select a folder first.'
  }
}

async function createWorkspaceFolder() {
  if (!newWorkspaceName.value.trim()) return
  err.value = ''
  try {
    const created = await apiFetch<WorkspaceFolder>('/projects/workspaces/folders', {
      method: 'POST',
      body: JSON.stringify({ name: newWorkspaceName.value.trim() }),
    })
    newWorkspaceName.value = ''
    await load()
    selectedWorkspaceFolderId.value = created.id
  } catch {
    err.value = 'Could not create folder'
  }
}

function startEditFolder(folder: WorkspaceFolder) {
  editingFolderId.value = folder.id
  editingFolderName.value = folder.name
}

function cancelEditFolder() {
  editingFolderId.value = null
  editingFolderName.value = ''
}

async function saveEditFolder(folderId: number) {
  if (!editingFolderName.value.trim()) return
  err.value = ''
  try {
    await apiFetch(`/projects/workspaces/folders/${folderId}`, {
      method: 'PUT',
      body: JSON.stringify({ name: editingFolderName.value.trim() }),
    })
    cancelEditFolder()
    await load()
  } catch {
    err.value = 'Could not rename folder'
  }
}

async function deleteFolder(folderId: number) {
  if (!confirm('Delete this folder? It must not contain projects.')) return
  err.value = ''
  try {
    await apiFetch(`/projects/workspaces/folders/${folderId}`, { method: 'DELETE' })
    if (selectedWorkspaceFolderId.value === folderId) {
      selectedWorkspaceFolderId.value = workspaceFolders.value.find((f) => f.id !== folderId)?.id ?? null
    }
    await load()
  } catch (e: unknown) {
    err.value =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail || 'Could not delete folder')
        : 'Could not delete folder'
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
        <button type="button" class="btn btn-outline" @click="showFolderManager = true">
          Folders
        </button>
        <button type="button" class="btn btn-outline" @click="showNewProject = true">
          New Project
        </button>
      </div>
    </header>

    <p class="hint">Manage folders from the Folders button. Every project must be created under a folder.</p>

    <div v-if="showNewProject" class="modal-backdrop" @click.self="showNewProject = false">
      <div class="card modal-card">
        <h3>Create New Project</h3>
      <label class="field">
        <span>Project name</span>
        <input v-model="newName" class="input" placeholder="e.g. Riverside Tower" @keyup.enter="createProject" />
      </label>
      <label class="field">
        <span>Folder (required)</span>
        <select v-model.number="selectedWorkspaceFolderId" class="input">
          <option :value="null" disabled>Select folder</option>
          <option v-for="wf in workspaceFolders" :key="wf.id" :value="wf.id">
            {{ wf.name }} ({{ wf.project_count }} projects)
          </option>
        </select>
      </label>
      <div class="row">
        <button type="button" class="btn btn-primary" @click="createProject">Create Project</button>
          <button type="button" class="btn btn-ghost" @click="showNewProject = false">Cancel</button>
        </div>
      </div>
    </div>

    <div v-if="showFolderManager" class="modal-backdrop" @click.self="showFolderManager = false">
      <div class="card modal-card folder-modal">
        <h3>Manage Folders</h3>
        <label class="field">
          <span>New folder</span>
          <div class="row">
            <input
              v-model="newWorkspaceName"
              class="input"
              placeholder="e.g. Kowloon District"
              @keyup.enter="createWorkspaceFolder"
            />
            <button type="button" class="btn btn-primary" @click="createWorkspaceFolder">Create</button>
          </div>
        </label>
        <ul class="folder-list">
          <li v-for="wf in workspaceFolders" :key="wf.id" class="folder-row">
            <template v-if="editingFolderId === wf.id">
              <input v-model="editingFolderName" class="input" />
              <button type="button" class="btn btn-primary" @click="saveEditFolder(wf.id)">Save</button>
              <button type="button" class="btn btn-ghost" @click="cancelEditFolder">Cancel</button>
            </template>
            <template v-else>
              <span>{{ wf.name }} <small class="meta">({{ wf.project_count }} projects)</small></span>
              <div class="row">
                <button type="button" class="btn btn-ghost" @click="startEditFolder(wf)">Edit</button>
                <button type="button" class="btn btn-ghost danger" @click="deleteFolder(wf.id)">Delete</button>
              </div>
            </template>
          </li>
        </ul>
        <div class="row">
          <button type="button" class="btn btn-ghost" @click="showFolderManager = false">Close</button>
        </div>
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
          <span class="meta">Folder: {{ p.workspace_folder_name || 'Unassigned' }}</span>
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
  width: min(560px, 100%);
}

.folder-modal {
  max-height: 80vh;
  overflow: auto;
}

.folder-list {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.folder-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
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
.danger {
  color: #dc2626 !important;
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
