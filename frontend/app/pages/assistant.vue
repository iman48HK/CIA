<script setup lang="ts">
definePageMeta({ middleware: 'auth' })

const { apiFetch } = useApi()
const message = ref('')
const reply = ref('')
const loading = ref(false)
const error = ref('')

const suggestions = [
  'Analyze a construction contract for potential risks.',
  'Summarize key safety checks before concrete pour.',
  'Compare steel vs timber framing for a mid-rise residential project.',
  'Draft a one-week lookahead schedule for interior fit-out.',
]

async function send() {
  const text = message.value.trim()
  if (!text || loading.value) return
  error.value = ''
  loading.value = true
  reply.value = ''
  try {
    const res = await apiFetch<{ reply: string }>('/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ message: text }),
    })
    reply.value = res.reply
  } catch (e: unknown) {
    const msg =
      e && typeof e === 'object' && 'data' in e
        ? String((e as { data?: { detail?: string } }).data?.detail)
        : 'Request failed'
    error.value = msg || 'Request failed'
  } finally {
    loading.value = false
  }
}

function useSuggestion(s: string) {
  message.value = s
  send()
}
</script>

<template>
  <div class="assistant">
    <header class="page-head">
      <h1>CIA Assistant</h1>
      <p class="muted">Powered by OpenRouter — ask about construction insight, regulations, and planning.</p>
    </header>

    <div class="panel card">
      <div v-if="!reply && !loading" class="empty-state">
        <h2>How can we help on site today?</h2>
        <p class="muted">Choose a prompt or type your own question.</p>
        <div class="suggestions">
          <button
            v-for="(s, i) in suggestions"
            :key="i"
            type="button"
            class="suggestion"
            @click="useSuggestion(s)"
          >
            {{ s }}
          </button>
        </div>
      </div>

      <div v-else class="output">
        <div v-if="loading" class="muted">Thinking…</div>
        <pre v-else class="reply">{{ reply }}</pre>
      </div>

      <p v-if="error" class="err">{{ error }}</p>

      <div class="composer">
        <textarea
          v-model="message"
          class="input area"
          rows="3"
          placeholder="Ask about drawings, ordinances, schedules, or risks…"
          @keydown.enter.exact.prevent="send"
        />
        <button type="button" class="btn btn-primary send" :disabled="loading" @click="send">
          Send
        </button>
      </div>
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
  margin: 0 0 1.25rem;
}

.panel {
  max-width: 720px;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.empty-state h2 {
  margin: 0 0 0.5rem;
  font-size: 1.15rem;
}

.suggestions {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 0.65rem;
  margin-top: 1rem;
}

.suggestion {
  text-align: left;
  padding: 0.85rem 1rem;
  border-radius: 0.65rem;
  border: 1px solid var(--border);
  background: var(--main-bg);
  color: var(--text);
  font-family: inherit;
  font-size: 0.8125rem;
  line-height: 1.35;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}

.suggestion:hover {
  border-color: var(--accent);
  background: var(--accent-dim);
}

.output {
  min-height: 120px;
}

.reply {
  margin: 0;
  white-space: pre-wrap;
  font-family: inherit;
  font-size: 0.9375rem;
  line-height: 1.55;
}

.err {
  color: #dc2626;
  font-size: 0.875rem;
  margin: 0;
}

.composer {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border);
}

.area {
  resize: vertical;
  min-height: 80px;
}

.send {
  align-self: flex-end;
}
</style>
