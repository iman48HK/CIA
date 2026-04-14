<script setup lang="ts">
const route = useRoute()
const isAuthPage = computed(() => route.path === '/login' || route.path === '/signup')
</script>

<template>
  <div class="guest-wrap" :class="{ 'guest-wrap--login': isAuthPage }">
    <div class="guest-card card" :class="{ 'guest-card--login': isAuthPage }">
      <template v-if="!isAuthPage">
        <div class="guest-brand">
          <img src="/cia-icon.svg" alt="CIA" class="logo-mark" />
          <div>
            <strong>CIA</strong>
            <div class="sub">Construction Insight Agent</div>
          </div>
        </div>
      </template>
      <slot />
    </div>
  </div>
</template>

<style scoped>
.guest-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: var(--main-bg);
  position: relative;
  overflow: hidden;
}

.guest-wrap--login {
  background: radial-gradient(ellipse 130% 90% at 50% -15%, #d1fae5 0%, #ecfdf5 18%, #f8fafc 52%, #e2e8f0 100%);
}

html.dark .guest-wrap--login {
  background: radial-gradient(ellipse 130% 90% at 50% -15%, #064e3b 0%, #0f172a 42%, #0b1220 100%);
}

.guest-card {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 400px;
}

.guest-card.card.guest-card--login {
  max-width: 56rem;
  padding: 0;
  overflow: hidden;
  border-radius: 1rem;
  box-shadow:
    0 25px 50px -12px rgba(15, 23, 42, 0.14),
    0 0 0 1px rgba(15, 23, 42, 0.06);
}

html.dark .guest-card--login {
  box-shadow:
    0 25px 50px -12px rgba(0, 0, 0, 0.55),
    0 0 0 1px rgba(255, 255, 255, 0.06);
}

.guest-brand {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.logo-mark {
  width: 40px;
  height: 40px;
}

.sub {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.15rem;
}
</style>
