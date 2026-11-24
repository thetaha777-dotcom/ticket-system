import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { api, hasToken, setToken } from '@/lib/api'
import type { User } from '@/types'

/** Who is signed in. The token lives in localStorage so a page reload keeps the session. */
export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const ready = ref(false) // true once we know whether a saved session is still valid

  const isSignedIn = computed(() => user.value !== null)
  const isOrganizer = computed(() => user.value?.role === 'organizer' || user.value?.role === 'platform_admin')
  const isAdmin = computed(() => user.value?.role === 'platform_admin')

  async function restore(): Promise<void> {
    if (hasToken()) {
      try {
        user.value = await api.get<User>('/auth/me')
      } catch {
        setToken(null)
      }
    }
    ready.value = true
  }

  async function login(email: string, password: string): Promise<User> {
    const result = await api.post<{ access_token: string; user: User }>('/auth/login', { email, password })
    setToken(result.access_token)
    user.value = result.user
    return result.user
  }

  async function refresh(): Promise<void> {
    user.value = await api.get<User>('/auth/me')
  }

  function logout(): void {
    setToken(null)
    user.value = null
  }

  return { user, ready, isSignedIn, isOrganizer, isAdmin, restore, login, refresh, logout }
})
