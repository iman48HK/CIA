// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: process.env.NODE_ENV !== 'production' },
  css: ['~/assets/css/main.css'],
  // Dev: browser calls same-origin `/api/*`; Vite proxies to FastAPI (avoids CORS / localhost vs 127.0.0.1 issues).
  // Set NUXT_PUBLIC_API_BASE (e.g. http://localhost:8000) only if you intentionally bypass the proxy.
  vite: {
    server: {
      proxy: {
        '/api': {
          target: 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  },
  runtimeConfig: {
    // Server-only: Docker / production SSR must call the API container directly (browser still uses /api on the gateway).
    apiInternal: process.env.NUXT_API_INTERNAL || '',
    public: {
      apiBase: process.env.NUXT_PUBLIC_API_BASE || '',
    },
  },
  app: {
    head: {
      title: 'Construction Insight Agent (CIA)',
      link: [
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
        },
      ],
    },
  },
})
