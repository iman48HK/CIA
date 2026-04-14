<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Folder {
  id: number
  code: string
  name: string
  file_count: number
}

const { apiFetch } = useApi()
const { me, loadMe } = useAuth()
const folders = ref<Folder[]>([])
const code = ref('')
const name = ref('')
const err = ref('')
const editingFolderId = ref<number | null>(null)
const editingFolderName = ref('')

async function load() {
  folders.value = await apiFetch<Folder[]>('/ordinance/folders')
}

onMounted(async () => {
  await loadMe()
  await load()
})

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
    await load()
  } catch {
    err.value = 'Unable to create folder'
  }
}

async function removeFolder(id: number) {
  if (!confirm('Delete this folder and all files inside it?')) return
  await apiFetch(`/ordinance/folders/${id}`, { method: 'DELETE' })
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
</script>

<template>
  <div>
    <header class="page-head">
      <h1>Ordinance Documents</h1>
      <p class="muted">Browse available regulatory documents</p>
    </header>
    <div v-if="me?.role === 'admin'" class="card admin-box">
      <strong>Add Folder (Admin)</strong>
      <div class="row">
        <input v-model="code" class="input" placeholder="Code e.g. HK-BUILD-001" />
        <input v-model="name" class="input" placeholder="Folder name" />
        <button type="button" class="btn btn-primary" @click="addFolder">Add</button>
      </div>
      <p v-if="err" class="err">{{ err }}</p>
    </div>

    <div class="grid">
      <div v-for="f in folders" :key="f.id" class="card folder-card-wrap">
        <NuxtLink :to="`/ordinance/${f.id}`" class="folder-card">
          <strong>{{ f.code }}</strong>
          <strong class="folder-name">{{ f.name }}</strong>
          <span class="count">({{ f.file_count }} files)</span>
          <span class="chev">→</span>
        </NuxtLink>
        <div v-if="me?.role === 'admin'" class="admin-actions">
          <template v-if="editingFolderId === f.id">
            <input
              v-model="editingFolderName"
              class="input"
              placeholder="Folder name"
              @click.stop
              @keydown.enter.stop.prevent="saveEditFolder(f.id)"
            />
            <button type="button" class="icon-btn confirm" title="Save name" @click.stop="saveEditFolder(f.id)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.2l-3.5-3.5L4 14.2l5 5L20 8.2 18.5 6.8z" />
              </svg>
            </button>
            <button type="button" class="icon-btn" title="Cancel edit" @click.stop="cancelEditFolder">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M18.3 5.71L12 12l6.3 6.29-1.41 1.41L10.59 13.41 4.29 19.7 2.88 18.29 9.17 12 2.88 5.71 4.29 4.3l6.3 6.29 6.29-6.29z" />
              </svg>
            </button>
          </template>
          <template v-else>
            <button type="button" class="icon-btn" title="Edit folder name" @click.stop="startEditFolder(f)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M3 17.25V21h3.75l11-11-3.75-3.75-11 11zM20.71 7.04a1 1 0 000-1.41L18.37 3.29a1 1 0 00-1.41 0L15.13 5.12l3.75 3.75 1.83-1.83z" />
              </svg>
            </button>
            <button type="button" class="icon-btn danger" title="Delete folder" @click.stop="removeFolder(f.id)">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
              </svg>
            </button>
          </template>
        </div>
      </div>
    </div>

    <p v-if="!folders.length" class="muted">No ordinance folders configured.</p>
  </div>
</template>

<style scoped>
.page-head h1 {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
}

.muted {
  margin: 0;
  color: var(--text-muted);
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}
.admin-box {
  margin-top: 1rem;
}
.row {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.5rem;
}
.folder-card-wrap {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.admin-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}
.folder-name {
  font-weight: 500;
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

.folder-card {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.35rem 0.5rem;
  padding: 1.25rem;
  text-decoration: none;
  color: inherit;
  position: relative;
}
.danger {
  color: #dc2626 !important;
}
.err {
  margin-top: 0.5rem;
  color: #dc2626;
}

.folder-card:hover {
  border-color: var(--accent);
  text-decoration: none;
}

.count {
  font-size: 0.875rem;
  color: var(--text-muted);
}

.chev {
  margin-left: auto;
  color: var(--accent);
}
</style>
