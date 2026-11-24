<script setup lang="ts">
import { reactive, ref } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { errorText } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const form = reactive({ email: '', password: '' })
const problem = ref('')
const busy = ref(false)

async function submit(): Promise<void> {
  busy.value = true
  problem.value = ''
  try {
    const user = await auth.login(form.email, form.password)
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : null
    await router.push(next ?? (user.role === 'platform_admin' ? '/admin' : user.role === 'organizer' ? '/organizer' : '/'))
  } catch (error) {
    problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page-narrow">
    <h1 class="mb-6">{{ $t('auth.signIn') }}</h1>
    <form class="card space-y-4" @submit.prevent="submit">
      <div><label class="label" for="login-email">{{ $t('auth.email') }}</label><input id="login-email" v-model="form.email" type="email" class="input" required autocomplete="email" /></div>
      <div><label class="label" for="login-password">{{ $t('auth.password') }}</label><input id="login-password" v-model="form.password" type="password" class="input" required autocomplete="current-password" /></div>
      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <button type="submit" class="btn btn-primary w-full" :disabled="busy">{{ $t('auth.signIn') }}</button>
      <p class="flex flex-wrap justify-between gap-2 text-sm">
        <RouterLink :to="{ name: 'forgot-password' }">{{ $t('auth.forgot') }}</RouterLink>
        <RouterLink :to="{ name: 'register', query: route.query }">{{ $t('auth.noAccount') }}</RouterLink>
      </p>
    </form>
  </div>
</template>
