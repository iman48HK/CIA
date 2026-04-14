<script setup lang="ts">
definePageMeta({ layout: 'guest', middleware: 'guest' })

import { apiErrorMessage } from '~/utils/apiError'

const { apiFetch, token } = useApi()
const email = ref('admin@abc.com')
const password = ref('123456')
const error = ref('')
const loading = ref(false)
const showPassword = ref(false)
const rememberMe = ref(true)

const features = [
  {
    title: 'Unified project data',
    text: 'Drawings, specs, and reports in one searchable workspace.',
  },
  {
    title: 'AI-powered analysis',
    text: 'Ask questions and get answers grounded in your project files.',
  },
  {
    title: 'Built for delivery',
    text: 'Exports and reporting stakeholders can rely on.',
  },
]

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
    error.value = apiErrorMessage(e, 'Login failed')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-split">
    <aside class="login-aside" aria-label="Product overview">
      <div class="aside-brand">
        <img src="/cia-icon.svg" alt="" class="aside-logo" width="36" height="36" />
        <span class="aside-brand-name">CIA</span>
      </div>
      <h1 class="aside-headline">
        Autonomous <span class="aside-accent">Construction</span> Intelligence
      </h1>
      <ul class="aside-features">
        <li v-for="(f, i) in features" :key="i" class="aside-feature">
          <span class="aside-feature-icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
            </svg>
          </span>
          <div>
            <strong class="aside-feature-title">{{ f.title }}</strong>
            <p class="aside-feature-text">{{ f.text }}</p>
          </div>
        </li>
      </ul>
      <p class="aside-foot">© 2026 CIA. Construction Insight Agent.</p>
    </aside>

    <main class="login-main">
      <h2 class="login-title">Welcome Back</h2>
      <p class="login-lead">Sign in to your account to continue</p>

      <form class="form" @submit.prevent="submit">
        <div class="field">
          <label class="field-label" for="login-email">Email Address</label>
          <div class="input-shell">
            <span class="input-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </span>
            <input
              id="login-email"
              v-model="email"
              type="email"
              class="input input-iconed"
              placeholder="name@company.com"
              required
              autocomplete="username"
            />
          </div>
        </div>

        <div class="field">
          <div class="field-label-row">
            <label class="field-label" for="login-password">Password</label>
            <button type="button" class="link-quiet">Forgot password?</button>
          </div>
          <div class="input-shell">
            <span class="input-icon" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
              </svg>
            </span>
            <input
              id="login-password"
              v-model="password"
              :type="showPassword ? 'text' : 'password'"
              class="input input-iconed input-with-toggle"
              required
              autocomplete="current-password"
            />
            <button
              type="button"
              class="toggle-visibility"
              :aria-pressed="showPassword"
              :aria-label="showPassword ? 'Hide password' : 'Show password'"
              @click="showPassword = !showPassword"
            >
              <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                <path d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
              </svg>
              <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
              </svg>
            </button>
          </div>
        </div>

        <label class="remember">
          <input v-model="rememberMe" type="checkbox" />
          <span>Keep me signed in</span>
        </label>

        <p v-if="error" class="err">{{ error }}</p>

        <button type="submit" class="btn btn-primary btn-signin" :disabled="loading">
          {{ loading ? 'Signing in…' : 'Sign In' }}
        </button>
      </form>

      <p class="foot">
        Don't have an account?
        <NuxtLink to="/signup">Create an account</NuxtLink>
      </p>
    </main>
  </div>
</template>

<style scoped>
.login-split {
  display: flex;
  align-items: stretch;
  min-height: 28rem;
}

.login-aside {
  flex: 0 1 42%;
  min-width: 17rem;
  padding: 2.25rem 2rem 1.75rem;
  background: linear-gradient(165deg, #0f2922 0%, #0a1f1a 48%, #051a16 100%);
  color: #f8fafc;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.aside-brand {
  display: flex;
  align-items: center;
  gap: 0.65rem;
}

.aside-logo {
  border-radius: 0.5rem;
}

.aside-brand-name {
  font-weight: 700;
  font-size: 1.125rem;
  letter-spacing: -0.02em;
}

.aside-headline {
  margin: 0;
  font-size: clamp(1.35rem, 2.5vw, 1.65rem);
  font-weight: 700;
  line-height: 1.25;
  letter-spacing: -0.03em;
}

.aside-accent {
  color: var(--accent);
}

.aside-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.aside-feature {
  display: flex;
  gap: 0.85rem;
  align-items: flex-start;
}

.aside-feature-icon {
  flex-shrink: 0;
  width: 1.35rem;
  height: 1.35rem;
  color: var(--accent);
  margin-top: 0.1rem;
}

.aside-feature-icon svg {
  display: block;
  width: 100%;
  height: 100%;
}

.aside-feature-title {
  display: block;
  font-size: 0.9rem;
  font-weight: 600;
  color: #f8fafc;
  margin-bottom: 0.2rem;
}

.aside-feature-text {
  margin: 0;
  font-size: 0.8125rem;
  line-height: 1.45;
  color: rgba(148, 189, 180, 0.95);
}

.aside-foot {
  margin: auto 0 0;
  padding-top: 1rem;
  font-size: 0.7rem;
  color: rgba(148, 163, 184, 0.55);
}

.login-main {
  flex: 1 1 58%;
  padding: 2.25rem 2.25rem 2rem;
  background: var(--card-bg);
  border-left: 1px solid var(--border);
}

.login-title {
  margin: 0 0 0.35rem;
  font-size: 1.5rem;
  font-weight: 700;
  letter-spacing: -0.03em;
  color: var(--text);
}

.login-lead {
  margin: 0 0 1.75rem;
  font-size: 0.9rem;
  color: var(--text-muted);
}

.form {
  display: flex;
  flex-direction: column;
  gap: 1.1rem;
}

.field-label {
  display: block;
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 0.4rem;
}

.field-label-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.4rem;
}

.field-label-row .field-label {
  margin-bottom: 0;
}

.link-quiet {
  border: none;
  background: none;
  padding: 0;
  font: inherit;
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--accent);
  cursor: pointer;
}

.link-quiet:hover {
  text-decoration: underline;
}

.input-shell {
  position: relative;
  display: flex;
  align-items: center;
}

.input-icon {
  position: absolute;
  left: 0.85rem;
  width: 1.1rem;
  height: 1.1rem;
  color: var(--text-muted);
  pointer-events: none;
  z-index: 1;
}

.input-icon svg {
  display: block;
  width: 100%;
  height: 100%;
}

.input-iconed {
  padding-left: 2.65rem;
  background: #f8fafc;
  border-color: #e2e8f0;
}

html.dark .input-iconed {
  background: #0c1017;
  border-color: var(--border);
}

.input-with-toggle {
  padding-right: 2.75rem;
}

.toggle-visibility {
  position: absolute;
  right: 0.5rem;
  top: 50%;
  transform: translateY(-50%);
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.25rem;
  height: 2.25rem;
  border: none;
  border-radius: 0.375rem;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
}

.toggle-visibility:hover {
  color: var(--text);
  background: rgba(148, 163, 184, 0.15);
}

html.dark .toggle-visibility:hover {
  background: rgba(148, 163, 184, 0.12);
}

.toggle-visibility svg {
  width: 1.15rem;
  height: 1.15rem;
}

.remember {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--text-muted);
  cursor: pointer;
  user-select: none;
}

.remember input {
  width: 1rem;
  height: 1rem;
  accent-color: var(--accent);
}

.err {
  color: #dc2626;
  font-size: 0.875rem;
  margin: 0;
}

.btn-signin {
  width: 100%;
  padding: 0.7rem 1rem;
  margin-top: 0.15rem;
  border-radius: 0.5rem;
  font-size: 0.9375rem;
}

.foot {
  margin: 1.75rem 0 0;
  text-align: center;
  font-size: 0.875rem;
  color: var(--text-muted);
}

.foot a {
  font-weight: 600;
}

@media (max-width: 52rem) {
  .login-split {
    flex-direction: column;
    min-height: unset;
  }

  .login-main {
    border-left: none;
    border-top: 1px solid var(--border);
  }

  .login-aside {
    flex: none;
    min-width: unset;
    padding: 1.75rem 1.5rem 1.5rem;
  }

  .aside-foot {
    margin-top: 0.5rem;
    padding-top: 0;
  }

  .login-main {
    padding: 1.75rem 1.5rem 2rem;
  }
}
</style>
