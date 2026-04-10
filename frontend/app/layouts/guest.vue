<template>
  <div class="guest-wrap">
    <div class="guest-card card">
      <div class="guest-brand">
        <div class="logo-mark" aria-hidden="true" />
        <div>
          <strong>CIA</strong>
          <div class="sub">Construction Insight Agent</div>
        </div>
      </div>
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
}

.guest-card {
  width: 100%;
  max-width: 400px;
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
  border-radius: 10px;
  background: linear-gradient(135deg, #10b981, #059669);
}

.sub {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.15rem;
}
</style>
