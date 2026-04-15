<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Project {
  id: number
  name: string
  folder_count: number
  drawing_count: number
  file_count: number
  workspace_folder_id?: number | null
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
const folderSortAsc = ref(true)

const sortedProjects = computed(() => {
  const rows = [...projects.value]
  rows.sort((a, b) => {
    const fa = (a.workspace_folder_name || '\uffff').toLowerCase()
    const fb = (b.workspace_folder_name || '\uffff').toLowerCase()
    const cmp = fa.localeCompare(fb)
    if (cmp !== 0) return folderSortAsc.value ? cmp : -cmp
    return b.id - a.id
  })
  return rows
})

function toggleFolderColumnSort() {
  folderSortAsc.value = !folderSortAsc.value
}

async function load() {
  try {
    workspaceFolders.value = await apiFetch<WorkspaceFolder[]>('/projects/workspaces/folders')
    projects.value = await apiFetch<Project[]>('/projects')
    if (!selectedWorkspaceFolderId.value && workspaceFolders.value.length) {
      selectedWorkspaceFolderId.value = workspaceFolders.value[0].id
    }
  } catch {
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

    <p class="hint">Use the table to open a project or jump straight to folder, drawings, files, or ordinance selection.</p>

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
        <div class="folder-modal-head">
          <h3>Manage Folders</h3>
          <button type="button" class="icon-btn" title="Close" @click="showFolderManager = false">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18.3 5.71L12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.7 2.88 18.29 9.17 12 2.88 5.71 4.29 4.3l6.3 6.29 6.29-6.29z" />
            </svg>
          </button>
        </div>
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
              <input v-model="editingFolderName" class="input" @keydown.enter.prevent="saveEditFolder(wf.id)" />
              <button type="button" class="icon-btn confirm" title="Save folder name" @click="saveEditFolder(wf.id)">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9 16.2l-3.5-3.5L4 14.2l5 5L20 8.2 18.5 6.8z" />
                </svg>
              </button>
              <button type="button" class="icon-btn" title="Cancel edit" @click="cancelEditFolder">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M18.3 5.71L12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.7 2.88 18.29 9.17 12 2.88 5.71 4.29 4.3l6.3 6.29 6.29-6.29z" />
                </svg>
              </button>
            </template>
            <template v-else>
              <span>{{ wf.name }} <small class="meta">({{ wf.project_count }} projects)</small></span>
              <div class="row">
                <button type="button" class="icon-btn" title="Edit folder name" @click="startEditFolder(wf)">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M3 17.25V21h3.75l11-11-3.75-3.75-11 11zM20.71 7.04a1 1 0 000-1.41L18.37 3.29a1 1 0 00-1.41 0L15.13 5.12l3.75 3.75 1.83-1.83z" />
                  </svg>
                </button>
                <button type="button" class="icon-btn danger" title="Delete folder" @click="deleteFolder(wf.id)">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                  </svg>
                </button>
              </div>
            </template>
          </li>
        </ul>
      </div>
    </div>

    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="!projects.length" class="card empty">
      <p>No projects found</p>
      <p class="muted">Create a new project to get started</p>
    </div>

    <div v-else class="card table-card">
      <table class="proj-table">
        <thead>
          <tr>
            <th>Project</th>
            <th>
              <button type="button" class="th-sort" @click="toggleFolderColumnSort">
                Folder
                <span class="sort-hint">{{ folderSortAsc ? 'A–Z' : 'Z–A' }}</span>
              </button>
            </th>
            <th>Drawings</th>
            <th>Project files</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in sortedProjects" :key="p.id">
            <td>
              <NuxtLink :to="`/projects/${p.id}`" class="proj-name">{{ p.name }}</NuxtLink>
            </td>
            <td>{{ p.workspace_folder_name || '—' }}</td>
            <td>{{ p.drawing_count }}</td>
            <td>{{ p.file_count }}</td>
          </tr>
        </tbody>
      </table>
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

.folder-modal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
}

.folder-list {
  list-style: none;
  padding: 0;
  margin: 0;
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

.icon-btn.confirm:hover {
  color: #16a34a;
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.1);
}

.icon-btn.danger:hover {
  color: #dc2626;
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
}

.empty {
  text-align: center;
  padding: 2rem;
}

.empty p {
  margin: 0 0 0.35rem;
}

.table-card {
  padding: 0;
  overflow: auto;
}

.proj-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.proj-table th,
.proj-table td {
  border-top: 1px solid var(--border);
  padding: 0.65rem 0.75rem;
  text-align: left;
  vertical-align: middle;
}

.proj-table th {
  border-top: none;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  font-weight: 600;
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

.proj-name {
  font-weight: 600;
  color: var(--accent);
  text-decoration: none;
}

.proj-name:hover {
  text-decoration: underline;
}

.meta {
  font-size: 0.8125rem;
  color: var(--text-muted);
}
</style>
