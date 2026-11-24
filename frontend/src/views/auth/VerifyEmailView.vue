<script setup lang="ts">
/** Landing page of the link in the verification email: /verify-email?token=... */
import { onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const state = ref<'working' | 'done' | 'failed'>('working')
const problem = ref('')

onMounted(async () => {
  try {
    await api.post('/auth/verify-email', { token: String(route.query.token ?? '') })
    if (auth.isSignedIn) await auth.refresh()
    state.value = 'done'
  } catch (error) {
    problem.value = errorText(error)
    state.value = 'failed'
  }
})
</script>

<template>
  <div class="page-narrow">
    <h1 class="mb-6">{{ $t('auth.verifyTitle') }}</h1>
    <p v-if="state === 'working'" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <div v-else-if="state === 'done'" class="notice notice-ok" role="status">
      <p class="font-semibold">{{ $t('auth.verified') }}</p>
      <RouterLink class="btn btn-primary btn-sm mt-3" :to="auth.isSignedIn ? { name: 'home' } : { name: 'login' }">{{ $t('common.continue') }}</RouterLink>
    </div>
    <p v-else class="notice notice-bad" role="alert">{{ problem }}</p>
  </div>
</template>
