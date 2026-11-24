<script setup lang="ts">
/** Account: name, language, email verification, password and in-app notifications. */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import { setLocale, type LocaleCode } from '@/i18n'
import { api } from '@/lib/api'
import { dateTime } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Notification, User } from '@/types'

const auth = useAuthStore()
const toasts = useToastStore()
const { t } = useI18n()

const profile = reactive({ name: auth.user?.name ?? '', locale: auth.user?.locale ?? 'ru' })
const password = reactive({ current_password: '', new_password: '' })
const notifications = ref<Notification[]>([])

async function saveProfile(): Promise<void> {
  try {
    auth.user = await api.patch<User>('/users/me', profile)
    setLocale(profile.locale as LocaleCode)
    toasts.ok(t('account.saved'))
  } catch (error) {
    toasts.error(error)
  }
}

async function changePassword(): Promise<void> {
  try {
    await api.post('/users/me/change-password', password)
    password.current_password = password.new_password = ''
    toasts.ok(t('account.passwordChanged'))
  } catch (error) {
    toasts.error(error)
  }
}

async function resend(): Promise<void> {
  try {
    await api.post('/auth/resend-verification')
    toasts.ok(t('account.verificationSent'))
  } catch (error) {
    toasts.error(error)
  }
}

async function markAllRead(): Promise<void> {
  await api.post('/users/me/notifications/read-all')
  notifications.value.forEach((note) => (note.is_read = true))
}

onMounted(async () => {
  try {
    notifications.value = await api.get<Notification[]>('/users/me/notifications')
  } catch (error) {
    toasts.error(error)
  }
})
</script>

<template>
  <div class="page">
    <h1 class="mb-6">{{ $t('account.title') }}</h1>
    <div class="grid gap-6 lg:grid-cols-2">
      <div class="space-y-6">
        <form class="card space-y-4" @submit.prevent="saveProfile">
          <h2 class="card-title">{{ $t('account.profile') }}</h2>
          <div><label class="label" for="acc-name">{{ $t('auth.name') }}</label><input id="acc-name" v-model="profile.name" class="input" required autocomplete="name" /></div>
          <div>
            <label class="label" for="acc-email">{{ $t('auth.email') }}</label>
            <input id="acc-email" :value="auth.user?.email" class="input" disabled />
            <p v-if="auth.user?.is_verified" class="hint text-ok">✓ {{ $t('account.verified') }}</p>
            <p v-else class="hint">
              {{ $t('account.notVerified') }}
              <button type="button" class="cursor-pointer font-semibold text-sky-deep underline" @click="resend">{{ $t('account.resend') }}</button>
            </p>
          </div>
          <div>
            <label class="label" for="acc-locale">{{ $t('account.emailLanguage') }}</label>
            <select id="acc-locale" v-model="profile.locale" class="input">
              <option value="kk">Қазақша</option><option value="ru">Русский</option><option value="en">English</option>
            </select>
          </div>
          <button type="submit" class="btn btn-primary">{{ $t('common.save') }}</button>
        </form>

        <form class="card space-y-4" @submit.prevent="changePassword">
          <h2 class="card-title">{{ $t('account.password') }}</h2>
          <div><label class="label" for="acc-current">{{ $t('account.currentPassword') }}</label><input id="acc-current" v-model="password.current_password" type="password" class="input" required autocomplete="current-password" /></div>
          <div><label class="label" for="acc-new">{{ $t('account.newPassword') }}</label><input id="acc-new" v-model="password.new_password" type="password" class="input" required minlength="8" maxlength="72" autocomplete="new-password" /></div>
          <button type="submit" class="btn btn-secondary">{{ $t('account.changePassword') }}</button>
        </form>

        <div class="card">
          <h2 class="card-title">{{ $t('account.organizerTitle') }}</h2>
          <p class="mb-3 text-sm text-ink-soft">{{ auth.isOrganizer ? $t('account.organizerYes') : $t('account.organizerNo') }}</p>
          <RouterLink class="btn btn-secondary" :to="{ name: 'organizer-profile' }">{{ auth.isOrganizer ? $t('account.openOrganizerProfile') : $t('account.becomeOrganizer') }}</RouterLink>
        </div>
      </div>

      <section class="card">
        <div class="mb-3 flex items-center justify-between gap-3">
          <h2 class="card-title mb-0">{{ $t('account.notifications') }}</h2>
          <button v-if="notifications.some((note) => !note.is_read)" type="button" class="btn btn-ghost btn-sm" @click="markAllRead">{{ $t('account.markRead') }}</button>
        </div>
        <p v-if="!notifications.length" class="text-ink-soft">{{ $t('account.noNotifications') }}</p>
        <ul class="divide-y divide-line">
          <li v-for="note in notifications" :key="note.id" class="py-3">
            <p class="font-semibold">
              <span v-if="!note.is_read" class="mr-1 inline-block h-2 w-2 rounded-full bg-sky-deep align-middle" :title="$t('account.unread')" />
              <RouterLink v-if="note.link" :to="note.link">{{ note.title }}</RouterLink><template v-else>{{ note.title }}</template>
            </p>
            <p class="line-clamp-3 text-sm whitespace-pre-line">{{ note.body }}</p>
            <p class="text-sm text-ink-soft">{{ dateTime(note.created_at) }}</p>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>
