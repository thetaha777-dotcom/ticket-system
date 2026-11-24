<script setup lang="ts">
import { ref } from 'vue'

import { api } from '@/lib/api'
import { errorText } from '@/lib/format'

const email = ref('')
const sent = ref(false)
const problem = ref('')

async function submit(): Promise<void> {
  problem.value = ''
  try {
    await api.post('/auth/forgot-password', { email: email.value })
    sent.value = true
  } catch (error) {
    problem.value = errorText(error)
  }
}
</script>

<template>
  <div class="page-narrow">
    <h1 class="mb-6">{{ $t('auth.forgotTitle') }}</h1>
    <p v-if="sent" class="notice notice-ok" role="status">{{ $t('auth.resetSent') }}</p>
    <form v-else class="card space-y-4" @submit.prevent="submit">
      <p class="text-sm text-ink-soft">{{ $t('auth.forgotLead') }}</p>
      <div><label class="label" for="forgot-email">{{ $t('auth.email') }}</label><input id="forgot-email" v-model="email" type="email" class="input" required autocomplete="email" /></div>
      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <button type="submit" class="btn btn-primary">{{ $t('auth.sendResetLink') }}</button>
    </form>
  </div>
</template>
