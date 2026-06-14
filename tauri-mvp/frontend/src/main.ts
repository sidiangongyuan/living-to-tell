import { createApp } from 'vue'
import { pinia } from './store'
import router from './router'
import App from './App.vue'
import './style.css'
import './styles/dark-mode.css'

const app = createApp(App)
app.use(pinia)
app.use(router)
app.mount('#app')
