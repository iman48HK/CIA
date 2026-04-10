<script setup lang="ts">
definePageMeta({ middleware: ['auth', 'admin'] })

interface UserRow {
  id: number
  email: string
  role: 'admin' | 'user'
  is_active: boolean
}

const { apiFetch } = useApi()
const users = ref<UserRow[]>([])
const err = ref('')
const saving = ref<number | null>(null)

async function load() {
  try {
    users.value = await apiFetch<UserRow[]>('/users')
  } catch {
    err.value = 'Failed to load users'
  }
}

onMounted(load)

async function save(u: UserRow, patch: Partial<{ role: string; is_active: boolean }>) {
  saving.value = u.id
  err.value = ''
  try {
    await apiFetch(`/users/${u.id}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    })
    await load()
  } catch {
    err.value = 'Update failed'
  } finally {
    saving.value = null
  }
}
</script>

<template>
  <div>
    <header class="page-head">
      <h1>User Management</h1>
      <p class="muted">Admins can change roles and disable accounts.</p>
    </header>

    <p v-if="err" class="err">{{ err }}</p>

    <div class="table-wrap card">
      <table class="table">
        <thead>
          <tr>
            <th>Email</th>
            <th>Role</th>
            <th>Active</th>
            <th />
          </tr>
        </thead>
        <tbody>
          <tr v-for="u in users" :key="u.id">
            <td>{{ u.email }}</td>
            <td>
              <select
                class="input compact"
                :value="u.role"
                :disabled="saving === u.id"
                @change="
                  save(u, { role: ($event.target as HTMLSelectElement).value as 'admin' | 'user' })
                "
              >
                <option value="user">user</option>
                <option value="admin">admin</option>
              </select>
            </td>
            <td>
              <label class="check">
                <input
                  type="checkbox"
                  :checked="u.is_active"
                  :disabled="saving === u.id"
                  @change="save(u, { is_active: ($event.target as HTMLInputElement).checked })"
                />
              </label>
            </td>
            <td class="muted small">{{ saving === u.id ? 'Saving…' : '' }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.page-head h1 {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
}

.muted {
  color: var(--text-muted);
  margin: 0 0 1rem;
}

.err {
  color: #dc2626;
}

.table-wrap {
  overflow: auto;
  padding: 0;
}

.table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}

.table th,
.table td {
  padding: 0.75rem 1rem;
  text-align: left;
  border-bottom: 1px solid var(--border);
}

.table th {
  font-weight: 600;
  color: var(--text-muted);
  background: var(--main-bg);
}

.compact {
  width: auto;
  min-width: 100px;
  padding: 0.35rem 0.5rem;
}

.check {
  display: flex;
  align-items: center;
}

.small {
  font-size: 0.75rem;
}
</style>
