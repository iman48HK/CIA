<script setup lang="ts">
const route = useRoute()
const { me, loadMe, logout } = useAuth()

const collapsed = ref(false)
const dark = ref(false)

onMounted(() => {
  collapsed.value = localStorage.getItem('cia_sidebar_collapsed') === '1'
  dark.value = localStorage.getItem('cia_dark') === '1'
  if (dark.value) {
    document.documentElement.classList.add('dark')
  }
  loadMe()
})

watch(collapsed, (v) => {
  if (import.meta.client) {
    localStorage.setItem('cia_sidebar_collapsed', v ? '1' : '0')
  }
})

function toggleDark() {
  dark.value = !dark.value
  if (import.meta.client) {
    localStorage.setItem('cia_dark', dark.value ? '1' : '0')
    document.documentElement.classList.toggle('dark', dark.value)
  }
}

function toggleCollapse() {
  collapsed.value = !collapsed.value
}

const nav = computed(() => {
  const items = [
    { to: '/', label: 'Dashboard', icon: 'home' },
    { to: '/projects', label: 'My Projects', icon: 'folder' },
    { to: '/ordinance', label: 'Ordinance', icon: 'book' },
    { to: '/assistant', label: 'CIA Assistant', icon: 'spark' },
  ]
  if (me.value?.role === 'admin') {
    items.push({ to: '/admin/users', label: 'User Management', icon: 'users' })
  }
  return items
})
</script>

<template>
  <div class="shell">
    <aside class="sidebar" :class="{ collapsed }">
      <div class="brand">
        <div class="logo" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="28" height="28" fill="none">
            <path
              fill="#10b981"
              d="M6 26V10l10-6 10 6v16l-10 6-10-6zm10-20.5L8.5 11v12L16 28l7.5-5V11L16 5.5z"
            />
            <path fill="#34d399" d="M16 8l6 3.5v9L16 24l-6-3.5v-9L16 8z" opacity=".85" />
          </svg>
        </div>
        <div v-if="!collapsed" class="brand-text">
          <div class="brand-title">CIA</div>
          <div class="brand-sub">Construction Insight Agent</div>
        </div>
      </div>

      <nav class="nav">
        <NuxtLink
          v-for="item in nav"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ active: route.path === item.to || (item.to !== '/' && route.path.startsWith(item.to)) }"
        >
          <span class="nav-icon" aria-hidden="true">
            <svg v-if="item.icon === 'home'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8h5z" />
            </svg>
            <svg v-else-if="item.icon === 'folder'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M10 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z" />
            </svg>
            <svg v-else-if="item.icon === 'book'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z" />
            </svg>
            <svg v-else-if="item.icon === 'spark'" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M7 14l-3 7 7-3 5-5-5-5-4 6zm9-9l-2 2 2 2 2-2-2-2z" />
            </svg>
            <svg v-else width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
              <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z" />
            </svg>
          </span>
          <span v-if="!collapsed" class="nav-label">{{ item.label }}</span>
        </NuxtLink>
      </nav>

      <div class="sidebar-footer">
        <button type="button" class="footer-btn" @click="toggleDark">
          <span class="nav-icon" aria-hidden="true">
            <svg v-if="dark" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z" />
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1zM5.99 4.58a.996.996 0 00-1.41 0 .996.996 0 000 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41L5.99 4.58zm12.37 12.37a.996.996 0 00-1.41 0 .996.996 0 000 1.41l1.06 1.06c.39.39 1.03.39 1.41 0s.39-1.03 0-1.41l-1.06-1.06zM4.58 18.01a.996.996 0 000-1.41.996.996 0 00-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06zM19.42 5.99a.996.996 0 000-1.41.996.996 0 00-1.41 0l-1.06 1.06c-.39.39-.39 1.03 0 1.41s1.03.39 1.41 0l1.06-1.06z" />
            </svg>
          </span>
          <span v-if="!collapsed">{{ dark ? 'Light' : 'Dark' }} Mode</span>
        </button>
        <button type="button" class="footer-btn" @click="toggleCollapse">
          <span class="nav-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" />
            </svg>
          </span>
          <span v-if="!collapsed">Collapse</span>
        </button>
        <button type="button" class="footer-btn logout" @click="logout">
          <span class="nav-icon" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z" />
            </svg>
          </span>
          <span v-if="!collapsed">Logout</span>
        </button>
      </div>
    </aside>

    <main class="main">
      <slot />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}

.sidebar {
  width: 260px;
  flex-shrink: 0;
  background: var(--sidebar);
  color: var(--text-on-dark);
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.sidebar.collapsed {
  width: 72px;
}

.brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1.25rem 1rem;
  border-bottom: 1px solid rgba(148, 163, 184, 0.15);
}

.brand-text {
  min-width: 0;
}

.brand-title {
  font-weight: 700;
  font-size: 1.25rem;
  letter-spacing: -0.02em;
}

.brand-sub {
  font-size: 0.65rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--text-muted-dark);
  line-height: 1.2;
  margin-top: 0.15rem;
}

.nav {
  flex: 1;
  padding: 0.75rem 0.5rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.65rem 0.85rem;
  border-radius: 0.5rem;
  color: var(--text-muted-dark);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
}

.nav-link:hover {
  background: var(--sidebar-hover);
  color: var(--text-on-dark);
  text-decoration: none;
}

.nav-link.active {
  background: var(--sidebar-active);
  color: var(--accent);
}

.nav-link.router-link-active {
  text-decoration: none;
}

.nav-icon {
  display: flex;
  opacity: 0.9;
}

.sidebar-footer {
  padding: 0.5rem;
  border-top: 1px solid rgba(148, 163, 184, 0.15);
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.footer-btn {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  width: 100%;
  padding: 0.55rem 0.75rem;
  border: none;
  border-radius: 0.5rem;
  background: transparent;
  color: var(--text-muted-dark);
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
  text-align: left;
}

.footer-btn:hover {
  background: var(--sidebar-hover);
  color: var(--text-on-dark);
}

.footer-btn.logout:hover {
  color: #fca5a5;
}

.main {
  flex: 1;
  min-width: 0;
  padding: 2rem;
  overflow: auto;
}

.collapsed .nav-link {
  justify-content: center;
}

.collapsed .footer-btn {
  justify-content: center;
}
</style>
