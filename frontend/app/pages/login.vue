<script setup lang="ts">
definePageMeta({ layout: 'guest', middleware: 'guest' })

const { apiFetch, token } = useApi()
const email = ref('admin@abc.com')
const password = ref('123456')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    const res = await apiFetch<{ access_token: string }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: email.value, password: password.value }),
    })
    token.value = res.access_token
    await navigateTo('/')
  } catch (e: unknown) {
    const msg =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail)
        : 'Login failed'
    error.value = msg || 'Login failed'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <h2 style="margin: 0 0 1rem; font-size: 1.25rem">Sign in</h2>
    <form class="form" @submit.prevent="submit">
      <label class="field">
        <span>Email</span>
        <input v-model="email" type="email" class="input" required autocomplete="username" />
      </label>
      <label class="field">
        <span>Password</span>
        <input
          v-model="password"
          type="password"
          class="input"
          required
          autocomplete="current-password"
        />
      </label>
      <p v-if="error" class="err">{{ error }}</p>
      <button type="submit" class="btn btn-primary full" :disabled="loading">
        {{ loading ? 'Signing in…' : 'Sign in' }}
      </button>
    </form>
    <p class="foot">
      No account?
      <NuxtLink to="/signup">Sign up</NuxtLink>
    </p>
  </div>
</template>

<style scoped>
.form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.err {
  color: #dc2626;
  font-size: 0.875rem;
  margin: 0;
}

.full {
  width: 100%;
  margin-top: 0.25rem;
}

.foot {
  margin: 1.25rem 0 0;
  text-align: center;
  font-size: 0.875rem;
  color: var(--text-muted);
}
</style>
