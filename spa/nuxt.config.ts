// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  ssr: false,
  nitro: {
    static: true,
    prerender: {
        crawlLinks: true,
    },
  },
  app: {
    baseURL: '/spa/',
    buildAssetsDir: '/assets/',
  },
  $production: {
    app: {
        cdnURL: '/assets/tweaks/spa/'
    },
    nitro: {
        output: {
            publicDir: '../tweaks/public/spa',
        }
    }
  },
  experimental: {
    appManifest: false,
    payloadExtraction: false,
  }
})
