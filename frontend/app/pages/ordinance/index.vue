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
          <span class="count">({{ f.file_count }} files)</span>
          <span class="chev">→</span>
        </NuxtLink>
        <button v-if="me?.role === 'admin'" type="button" class="btn btn-ghost danger" @click="removeFolder(f.id)">
          Delete
        </button>
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
