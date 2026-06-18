import { createApp } from 'vue'
import { pinia } from './store'
import router from './router'
import App from './App.vue'
import './style.css'
import './styles/dark-mode.css'

const startupStartedAt = performance.now()
let firstRouteLogged = false

router.afterEach(() => {
  if (!firstRouteLogged) {
    firstRouteLogged = true
    console.info(`[startup] first_route_mounted=${Math.round(performance.now() - startupStartedAt)}ms`)
  }
})

async function notifyFrontendReady() {
  try {
    const { emit } = await import('@tauri-apps/api/event')
    await emit('frontend_ready')
  } catch {
    // Browser/dev preview mode does not expose the Tauri event bridge.
  }
}

console.info('[startup] main_ts_start=0ms')

const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')

console.info(`[startup] vue_mounted=${Math.round(performance.now() - startupStartedAt)}ms`)
requestAnimationFrame(() => {
  console.info(`[startup] first_paint_ready=${Math.round(performance.now() - startupStartedAt)}ms`)
  void notifyFrontendReady()
})
