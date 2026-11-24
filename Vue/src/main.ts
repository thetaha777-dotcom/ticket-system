import './styles.css'

import { createPinia } from 'pinia'
import { createApp } from 'vue'

import App from './App.vue'
import { i18n } from './i18n'
import { setUnauthorizedHandler } from './lib/api'
import { router } from './router'
import { useAuthStore } from './stores/auth'

const app = createApp(App)
app.use(createPinia())
app.use(i18n)
app.use(router)

// When the server rejects the saved token (expired, account suspended), sign out and ask to sign in again.
setUnauthorizedHandler(() => {
  const auth = useAuthStore()
  if (auth.isSignedIn) {
    auth.logout()
    void router.push({ name: 'login', query: { next: router.currentRoute.value.fullPath } })
  }
})

app.mount('#app')
