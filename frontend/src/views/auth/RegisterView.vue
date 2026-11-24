<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

const auth = useAuthStore()
const toasts = useToastStore()
const route = useRoute()
const router = useRouter()
const { t, locale } = useI18n()

const form = reactive({ name: '', email: '', password: '', role: 'attendee' as 'attendee' | 'organizer' })
const problem = ref('')
const busy = ref(false)

async function submit(): Promise<void> {
  busy.value = true
  problem.value = ''
  try {
    await api.post('/auth/register', { ...form, locale: locale.value })
    await auth.login(form.email, form.password)
    toasts.ok(t('auth.checkEmail'))
    const next = typeof route.query.next === 'string' && route.query.next.startsWith('/') ? route.query.next : null
    await router.push(next ?? (form.role === 'organizer' ? '/organizer' : '/'))
  } catch (error) {
    problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="page-narrow">
    <h1 class="mb-6">{{ $t('auth.createAccount') }}</h1>
    <form class="card space-y-4" @submit.prevent="submit">
      <fieldset>
        <legend class="label">{{ $t('auth.iWant') }}</legend>
        <div class="grid gap-2 sm:grid-cols-2">
          <label class="flex cursor-pointer items-start gap-2 rounded-lg border p-3" :class="form.role === 'attendee' ? 'border-ink bg-mist' : 'border-line'">
            <input v-model="form.role" type="radio" value="attendee" class="mt-1" />
            <span><strong class="block">{{ $t('auth.roleAttendee') }}</strong><span class="text-sm text-ink-soft">{{ $t('auth.roleAttendeeHint') }}</span></span>
          </label>
          <label class="flex cursor-pointer items-start gap-2 rounded-lg border p-3" :class="form.role === 'organizer' ? 'border-ink bg-mist' : 'border-line'">
            <input v-model="form.role" type="radio" value="organizer" class="mt-1" />
            <span><strong class="block">{{ $t('auth.roleOrganizer') }}</strong><span class="text-sm text-ink-soft">{{ $t('auth.roleOrganizerHint') }}</span></span>
          </label>
        </div>
      </fieldset>
      <div><label class="label" for="reg-name">{{ $t('auth.name') }}</label><input id="reg-name" v-model="form.name" class="input" required autocomplete="name" /></div>
      <div><label class="label" for="reg-email">{{ $t('auth.email') }}</label><input id="reg-email" v-model="form.email" type="email" class="input" required autocomplete="email" /></div>
      <div>
        <label class="label" for="reg-password">{{ $t('auth.password') }}</label>
        <input id="reg-password" v-model="form.password" type="password" class="input" required minlength="8" maxlength="72" autocomplete="new-password" aria-describedby="reg-password-hint" />
        <p id="reg-password-hint" class="hint">{{ $t('auth.passwordHint') }}</p>
      </div>
      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <button type="submit" class="btn btn-primary w-full" :disabled="busy">{{ $t('auth.createAccount') }}</button>
      <p class="text-sm"><RouterLink :to="{ name: 'login', query: route.query }">{{ $t('auth.haveAccount') }}</RouterLink></p>
    </form>
  </div>
</template>
