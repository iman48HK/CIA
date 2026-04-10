<script setup lang="ts">
const route = useRoute()
const { me, loadMe, logout } = useAuth()
const { apiFetch } = useApi()

const collapsed = ref(false)
const dark = ref(false)
const showProfile = ref(false)
const savingProfile = ref(false)
const profileErr = ref('')
const showCamera = ref(false)
const cameraError = ref('')
const cameraVideo = ref<HTMLVideoElement | null>(null)
const cameraStream = ref<MediaStream | null>(null)
const initialProfile = reactive({
  display_name: '',
  email: '',
  avatar_url: '',
})
const profileForm = reactive({
  display_name: '',
  email: '',
  avatar_url: '',
  current_password: '',
  new_password: '',
  retype_new_password: '',
})

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

watch(
  () => me.value,
  (v) => {
    profileForm.display_name = v?.display_name || ''
    profileForm.email = v?.email || ''
    profileForm.avatar_url = v?.avatar_url || ''
    initialProfile.display_name = v?.display_name || ''
    initialProfile.email = v?.email || ''
    initialProfile.avatar_url = v?.avatar_url || ''
    profileForm.current_password = ''
    profileForm.new_password = ''
    profileForm.retype_new_password = ''
  },
  { immediate: true }
)

async function onAvatarFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  if (!file.type.startsWith('image/')) {
    profileErr.value = 'Please choose an image file.'
    return
  }
  if (file.size > 10 * 1024 * 1024) {
    profileErr.value = 'Avatar image must be 10 MB or less.'
    return
  }
  profileErr.value = ''
  const dataUrl = await toCompressedDataUrl(file)
  profileForm.avatar_url = dataUrl
  input.value = ''
}

async function toCompressedDataUrl(file: File): Promise<string> {
  const srcDataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result || ''))
    reader.onerror = () => reject(new Error('Failed to read image'))
    reader.readAsDataURL(file)
  })
  const img = await new Promise<HTMLImageElement>((resolve, reject) => {
    const el = new Image()
    el.onload = () => resolve(el)
    el.onerror = () => reject(new Error('Failed to decode image'))
    el.src = srcDataUrl
  })
  const maxSide = 1024
  const scale = Math.min(1, maxSide / Math.max(img.width, img.height))
  const w = Math.max(1, Math.round(img.width * scale))
  const h = Math.max(1, Math.round(img.height * scale))
  const canvas = document.createElement('canvas')
  canvas.width = w
  canvas.height = h
  const ctx = canvas.getContext('2d')
  if (!ctx) return srcDataUrl
  ctx.drawImage(img, 0, 0, w, h)
  return canvas.toDataURL('image/jpeg', 0.85)
}

async function startCamera() {
  cameraError.value = ''
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true })
    cameraStream.value = stream
    showCamera.value = true
    await nextTick()
    if (cameraVideo.value) {
      cameraVideo.value.srcObject = stream
      await cameraVideo.value.play()
    }
  } catch {
    cameraError.value = 'Unable to access camera. Please allow camera permission or upload an image.'
  }
}

function stopCamera() {
  const stream = cameraStream.value
  if (stream) {
    stream.getTracks().forEach((t) => t.stop())
  }
  cameraStream.value = null
  showCamera.value = false
}

function captureFromCamera() {
  if (!cameraVideo.value) return
  const video = cameraVideo.value
  const maxSide = 1024
  const vw = video.videoWidth || 640
  const vh = video.videoHeight || 480
  const scale = Math.min(1, maxSide / Math.max(vw, vh))
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(vw * scale))
  canvas.height = Math.max(1, Math.round(vh * scale))
  const ctx = canvas.getContext('2d')
  if (!ctx) {
    cameraError.value = 'Unable to capture image from camera.'
    return
  }
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
  profileForm.avatar_url = canvas.toDataURL('image/jpeg', 0.85)
  stopCamera()
}

watch(showProfile, (open) => {
  if (!open) {
    stopCamera()
  }
})

function toErrorMessage(err: unknown): string {
  if (!err || typeof err !== 'object') return 'Failed to update profile'
  if (!('data' in err)) return 'Failed to update profile'
  const data = (err as { data?: unknown }).data
  if (!data || typeof data !== 'object') return 'Failed to update profile'
  const detail = (data as { detail?: unknown }).detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    const first = detail[0]
    if (typeof first === 'string') return first
    if (first && typeof first === 'object') {
      const msg = (first as { msg?: unknown }).msg
      if (typeof msg === 'string') return msg
    }
    return 'Validation failed while updating profile'
  }
  if (detail && typeof detail === 'object') {
    const message = (detail as { message?: unknown }).message
    if (typeof message === 'string') return message
    return 'Profile update failed with server validation error'
  }
  return 'Failed to update profile'
}

async function saveProfile() {
  if (profileForm.new_password && profileForm.new_password !== profileForm.retype_new_password) {
    profileErr.value = 'New password and retype password do not match.'
    return
  }
  savingProfile.value = true
  profileErr.value = ''
  try {
    const payload: Record<string, string> = {}
    if (profileForm.display_name !== initialProfile.display_name) {
      payload.display_name = profileForm.display_name
    }
    if (profileForm.email && profileForm.email !== initialProfile.email) {
      payload.email = profileForm.email
    }
    if (profileForm.avatar_url !== initialProfile.avatar_url) {
      payload.avatar_url = profileForm.avatar_url
    }
    if (profileForm.new_password) {
      payload.current_password = profileForm.current_password
      payload.new_password = profileForm.new_password
    }
    if (!Object.keys(payload).length) {
      showProfile.value = false
      return
    }
    await apiFetch('/users/me/profile', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
    await loadMe()
    showProfile.value = false
  } catch (e: unknown) {
    profileErr.value = toErrorMessage(e)
  } finally {
    savingProfile.value = false
  }
}

const nav = computed(() => {
  const items = [
    { to: '/', label: 'Dashboard', icon: 'home' },
    { to: '/projects', label: 'My Projects', icon: 'folder' },
    { to: '/ordinance', label: 'Ordinance', icon: 'book' },
    { to: '/assistant', label: 'AI Assistant', icon: 'spark' },
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
          <img src="/cia-icon.svg" alt="CIA" width="28" height="28" />
        </div>
        <div v-if="!collapsed" class="brand-text">
          <div class="brand-title-row">
            <div class="brand-title">CIA</div>
            <button type="button" class="collapse-top-btn" @click="toggleCollapse">
              {{ collapsed ? '>' : '<' }}
            </button>
          </div>
          <div class="brand-sub">Construction Insight Agent</div>
        </div>
        <button v-else type="button" class="collapse-top-btn icon-only" @click="toggleCollapse">></button>
      </div>

      <div class="top-controls">
        <button type="button" class="footer-btn" @click="toggleDark">
          <span class="nav-icon" aria-hidden="true">
            <svg v-if="dark" width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 3c-4.97 0-9 4.03-9 9s4.03 9 9 9 9-4.03 9-9c0-.46-.04-.92-.1-1.36-.98 1.37-2.58 2.26-4.4 2.26-2.98 0-5.4-2.42-5.4-5.4 0-1.81.89-3.42 2.26-4.4-.44-.06-.9-.1-1.36-.1z" />
            </svg>
            <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 7c-2.76 0-5 2.24-5 5s2.24 5 5 5 5-2.24 5-5-2.24-5-5-5zM2 13h2c.55 0 1-.45 1-1s-.45-1-1-1H2c-.55 0-1 .45-1 1s.45 1 1 1zm18 0h2c.55 0 1-.45 1-1s-.45-1-1-1h-2c-.55 0-1 .45-1 1s.45 1 1 1zM11 2v2c0 .55.45 1 1 1s1-.45 1-1V2c0-.55-.45-1-1-1s-1 .45-1 1zm0 18v2c0 .55.45 1 1 1s1-.45 1-1v-2c0-.55-.45-1-1-1s-1 .45-1 1z" />
            </svg>
          </span>
          <span v-if="!collapsed">{{ dark ? 'Light' : 'Dark' }} Mode</span>
        </button>
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
        <button type="button" class="profile-btn" @click="showProfile = true">
          <img v-if="me?.avatar_url" :src="me.avatar_url" alt="avatar" class="avatar" />
          <div v-else class="avatar placeholder">{{ (me?.display_name || me?.email || 'U').slice(0, 1).toUpperCase() }}</div>
          <div v-if="!collapsed" class="profile-text">
            <strong>{{ me?.display_name || 'User' }}</strong>
            <span>{{ me?.email }}</span>
          </div>
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

    <div v-if="showProfile" class="modal-backdrop" @click.self="showProfile = false">
      <div class="card modal-card">
        <h3>Edit Profile</h3>
        <div class="avatar-preview-wrap">
          <img v-if="profileForm.avatar_url" :src="profileForm.avatar_url" alt="Avatar preview" class="avatar-preview" />
          <div v-else class="avatar-preview placeholder">
            {{ (profileForm.display_name || profileForm.email || 'U').slice(0, 1).toUpperCase() }}
          </div>
        </div>
        <label class="field">
          <span>Avatar URL / Data URL</span>
          <input v-model="profileForm.avatar_url" class="input" placeholder="https://... or data:image/...base64" />
        </label>
        <div class="field">
          <span>Or upload avatar image</span>
          <input type="file" accept="image/*" class="input" @change="onAvatarFileChange" />
        </div>
        <div class="camera-actions">
          <button v-if="!showCamera" type="button" class="btn btn-outline" @click="startCamera">Use Camera</button>
          <template v-else>
            <button type="button" class="btn btn-primary" @click="captureFromCamera">Capture</button>
            <button type="button" class="btn btn-ghost" @click="stopCamera">Cancel Camera</button>
          </template>
        </div>
        <p v-if="cameraError" class="err">{{ cameraError }}</p>
        <video v-if="showCamera" ref="cameraVideo" class="camera-preview" autoplay playsinline muted />
        <label class="field">
          <span>Name</span>
          <input v-model="profileForm.display_name" class="input" />
        </label>
        <label class="field">
          <span>Email</span>
          <input v-model="profileForm.email" type="email" class="input" />
        </label>
        <label class="field">
          <span>Current Password (required to change password)</span>
          <input v-model="profileForm.current_password" type="password" class="input" />
        </label>
        <label class="field">
          <span>New Password</span>
          <input v-model="profileForm.new_password" type="password" class="input" />
        </label>
        <label class="field">
          <span>Retype New Password</span>
          <input v-model="profileForm.retype_new_password" type="password" class="input" />
        </label>
        <p v-if="profileErr" class="err">{{ profileErr }}</p>
        <div class="actions">
          <button type="button" class="btn btn-primary" :disabled="savingProfile" @click="saveProfile">Save</button>
          <button type="button" class="btn btn-ghost" @click="showProfile = false">Cancel</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

.sidebar {
  width: 260px;
  height: 100vh;
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
.brand-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.5rem;
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
.collapse-top-btn {
  border: 1px solid rgba(148, 163, 184, 0.35);
  background: transparent;
  color: var(--text-on-dark);
  border-radius: 0.4rem;
  padding: 0.15rem 0.4rem;
  cursor: pointer;
}

.collapse-top-btn.icon-only {
  margin-left: auto;
}

.top-controls {
  padding: 0.5rem;
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
.profile-btn {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  width: 100%;
  padding: 0.5rem;
  border: none;
  border-radius: 0.5rem;
  background: transparent;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.profile-btn:hover {
  background: var(--sidebar-hover);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar.placeholder {
  display: grid;
  place-items: center;
  background: rgba(16, 185, 129, 0.25);
  font-weight: 700;
}

.profile-text {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.profile-text span {
  font-size: 0.75rem;
  color: var(--text-muted-dark);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  height: 100vh;
  padding: 2rem;
  overflow: auto;
}

.collapsed .nav-link {
  justify-content: center;
}

.collapsed .footer-btn {
  justify-content: center;
}
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(2, 6, 23, 0.45);
  display: grid;
  place-items: center;
  z-index: 50;
  padding: 1rem;
}

.modal-card {
  width: min(520px, 100%);
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
  margin-bottom: 0.65rem;
}

.actions {
  display: flex;
  gap: 0.5rem;
}

.camera-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.camera-preview {
  width: 100%;
  max-height: 300px;
  border-radius: 0.5rem;
  border: 1px solid var(--border);
  background: #000;
  margin-bottom: 0.5rem;
}

.avatar-preview-wrap {
  display: flex;
  justify-content: center;
  margin-bottom: 0.8rem;
}

.avatar-preview {
  width: 96px;
  height: 96px;
  border-radius: 999px;
  object-fit: cover;
  border: 1px solid var(--border);
}

.avatar-preview.placeholder {
  display: grid;
  place-items: center;
  background: rgba(16, 185, 129, 0.2);
  font-size: 1.75rem;
  font-weight: 700;
  color: #065f46;
}

.err {
  color: #dc2626;
}
</style>
