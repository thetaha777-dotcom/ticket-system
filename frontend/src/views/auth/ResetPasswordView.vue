<script setup lang="ts">
/** Landing page of the link in the password-reset email: /reset-password?token=... */
import { ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { api } from '@/lib/api'
import { errorText } from '@/lib/format'

const route = useRoute()
const password = ref('')
const done = ref(false)
const problem = ref('')

async function submit(): Promise<void> {
  problem.value = ''
  try {
    await api.post('/auth/reset-password', { token: String(route.query.token ?? ''), new_password: password.value })
    done.value = true
  } catch (error) {
    problem.value = errorText(error)
  }
}
</script>

<template>
  <div class="page-narrow">
    <h1 class="mb-6">{{ $t('auth.resetTitle') }}</h1>
    <div v-if="done" class="notice notice-ok" role="status">
      <p class="font-semibold">{{ $t('auth.resetDone') }}</p>
      <RouterLink class="btn btn-primary btn-sm mt-3" :to="{ name: 'login' }">{{ $t('auth.signIn') }}</RouterLink>
    </div>
    <form v-else class="card space-y-4" @submit.prevent="submit">
      <div>
        <label class="label" for="reset-password">{{ $t('account.newPassword') }}</label>
        <input id="reset-password" v-model="password" type="password" class="input" required minlength="8" maxlength="72" autocomplete="new-password" />
        <p class="hint">{{ $t('auth.passwordHint') }}</p>
      </div>
      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <button type="submit" class="btn btn-primary">{{ $t('auth.setPassword') }}</button>
    </form>
  </div>
</template>
