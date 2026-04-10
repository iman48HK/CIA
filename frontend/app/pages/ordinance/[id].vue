<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const route = useRoute()
const folderId = computed(() => Number(route.params.id))
const { apiFetch } = useApi()
const { me, loadMe } = useAuth()

interface FileRow {
  id: number
  title: string
  created_at: string
}

const files = ref<FileRow[]>([])
const newTitle = ref('')
const err = ref('')

async function load() {
  files.value = await apiFetch<FileRow[]>(`/ordinance/folders/${folderId.value}/files`)
}

onMounted(async () => {
  await loadMe()
  await load()
})

watch(folderId, load)

async function addFile() {
  if (!newTitle.value.trim()) return
  err.value = ''
  try {
    await apiFetch(`/ordinance/folders/${folderId.value}/files`, {
      method: 'POST',
      body: JSON.stringify({ title: newTitle.value.trim() }),
    })
    newTitle.value = ''
    await load()
  } catch {
    err.value = 'Only admins can add ordinance documents.'
  }
}
</script>

<template>
  <div>
    <NuxtLink to="/ordinance" class="back">← Ordinance</NuxtLink>
    <h1>Folder</h1>
    <p class="muted">Files in this folder</p>

    <p v-if="err" class="err">{{ err }}</p>

    <div v-if="me?.role === 'admin'" class="card admin-add">
      <strong>Add document (admin)</strong>
      <div class="inline">
        <input v-model="newTitle" class="input" placeholder="Document title" @keyup.enter="addFile" />
        <button type="button" class="btn btn-primary" @click="addFile">Add</button>
      </div>
    </div>

    <div v-if="!files.length" class="card empty">No files in this folder</div>
    <ul v-else class="list">
      <li v-for="f in files" :key="f.id" class="card file-row">
        {{ f.title }}
      </li>
    </ul>
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
}

.empty {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}

.err {
  color: #dc2626;
}
</style>
