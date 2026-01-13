// web/nuxt.config.ts
export default defineNuxtConfig({
  ssr: true,

  css: [
    "@/assets/scss/main.scss"
  ],

  app: {
    head: {
      title: 'Band Managing',
      meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }]
    }
  },

  devServer: {
    port: 3000,
    host: '0.0.0.0'
  }
})