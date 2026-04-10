<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Folder {
  id: number
  code: string
  name: string
  file_count: number
}

const { apiFetch } = useApi()
const folders = ref<Folder[]>([])

onMounted(async () => {
  folders.value = await apiFetch<Folder[]>('/ordinance/folders')
})
</script>

<template>
  <div>
    <header class="page-head">
      <h1>Ordinance Documents</h1>
      <p class="muted">Browse available regulatory documents</p>
    </header>

    <div class="grid">
      <NuxtLink
        v-for="f in folders"
        :key="f.id"
        :to="`/ordinance/${f.id}`"
        class="card folder-card"
      >
        <strong>{{ f.code }}</strong>
        <span class="count">({{ f.file_count }} files)</span>
        <span class="chev">→</span>
      </NuxtLink>
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
