<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

interface Stats {
  project_count: number
  drawing_count: number
  uploaded_file_count: number
  ordinance_file_count: number
}

const { apiFetch } = useApi()
const stats = ref<Stats | null>(null)
const projects = ref<{ id: number; name: string }[]>([])
const err = ref('')

onMounted(async () => {
  try {
    stats.value = await apiFetch<Stats>('/dashboard/stats')
    const list = await apiFetch<{ id: number; name: string }[]>('/projects')
    projects.value = list.slice(0, 5)
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : 'Failed to load'
  }
})
</script>

<template>
  <div>
    <header class="page-head">
      <h1>Welcome back</h1>
      <p class="muted">Here's your construction insights overview</p>
    </header>

    <p v-if="err" class="err">{{ err }}</p>

    <div class="grid">
      <NuxtLink to="/projects" class="stat-card">
        <div>
          <div class="stat-label">My Projects</div>
          <div class="stat-num">{{ stats?.project_count ?? '—' }}</div>
          <span class="stat-link">View details →</span>
        </div>
        <div class="stat-icon mint" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="#059669">
            <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
          </svg>
        </div>
      </NuxtLink>

      <NuxtLink to="/projects" class="stat-card">
        <div>
          <div class="stat-label">Total Drawings</div>
          <div class="stat-num">{{ stats?.drawing_count ?? '—' }}</div>
          <span class="stat-link accent">View details →</span>
        </div>
        <div class="stat-icon blue" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="#2563eb">
            <path d="M14 2H6c-1.1 0-1.99.9-1.99 2L4 20c0 1.1.89 2 1.99 2H18c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z" />
          </svg>
        </div>
      </NuxtLink>

      <NuxtLink to="/projects" class="stat-card">
        <div>
          <div class="stat-label">Uploaded Files</div>
          <div class="stat-num">{{ stats?.uploaded_file_count ?? '—' }}</div>
          <span class="stat-link">View details →</span>
        </div>
        <div class="stat-icon peach" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="#ea580c">
            <path d="M3 17v2h6v-2H3zM3 5v2h10V5H3zm10 16v-2h8v-2h-8v-2h-2v6h2zM7 9v2H3v2h4v2h2V9H7zm14 4v-2H11v2h10zm-6-4h2V7h4V5h-4V3h-2v6z" />
          </svg>
        </div>
      </NuxtLink>

      <NuxtLink to="/ordinance" class="stat-card">
        <div>
          <div class="stat-label">Ordinance Docs</div>
          <div class="stat-num">{{ stats?.ordinance_file_count ?? '—' }}</div>
          <span class="stat-link">View details →</span>
        </div>
        <div class="stat-icon mint" aria-hidden="true">
          <svg width="28" height="28" viewBox="0 0 24 24" fill="#059669">
            <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" />
          </svg>
        </div>
      </NuxtLink>
    </div>

    <section class="recent">
      <div class="recent-head">
        <h2>Recent Projects</h2>
        <NuxtLink to="/projects">View all</NuxtLink>
      </div>
      <div v-if="!projects.length" class="empty card">
        <p>No projects yet. Create your first project to get started.</p>
        <NuxtLink to="/projects" class="btn btn-primary">Create Project</NuxtLink>
      </div>
      <ul v-else class="proj-list">
        <li v-for="p in projects" :key="p.id">
          <NuxtLink :to="`/projects/${p.id}`">{{ p.name }}</NuxtLink>
        </li>
      </ul>
    </section>
  </div>
</template>

<style scoped>
.page-head h1 {
  margin: 0 0 0.35rem;
  font-size: 1.75rem;
  font-weight: 700;
}

.muted {
  margin: 0;
  color: var(--text-muted);
  font-size: 1rem;
}

.err {
  color: #dc2626;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
  margin-top: 1.75rem;
}

.stat-card {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 0.75rem;
  padding: 1.25rem;
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s;
}

.stat-card:hover {
  box-shadow: 0 4px 20px rgba(15, 23, 42, 0.08);
  text-decoration: none;
}

.stat-label {
  font-size: 0.875rem;
  color: var(--text-muted);
  margin-bottom: 0.35rem;
}

.stat-num {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.stat-link {
  font-size: 0.8125rem;
  color: var(--text-muted);
}

.stat-link.accent {
  color: var(--accent);
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 0.65rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-icon.mint {
  background: var(--icon-mint);
}

.stat-icon.blue {
  background: var(--icon-blue);
}

.stat-icon.peach {
  background: var(--icon-peach);
}

.recent {
  margin-top: 2.5rem;
}

.recent-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1rem;
}

.recent-head h2 {
  margin: 0;
  font-size: 1.125rem;
  font-weight: 600;
}

.empty {
  text-align: center;
  padding: 2rem;
}

.empty p {
  color: var(--text-muted);
  margin: 0 0 1rem;
}

.proj-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.proj-list li {
  padding: 0.65rem 0;
  border-bottom: 1px solid var(--border);
}
</style>
