<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { api } from '@/lib/api'
import { dateOnly, errorText } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Page, User } from '@/types'

const auth = useAuthStore()
const toasts = useToastStore()
const { t } = useI18n()
const filters = reactive({ q: '', role: '' })
const page = ref<Page<User> | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    page.value = await api.get<Page<User>>('/admin/users', { ...filters, limit: 100 })
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function setActive(user: User, is_active: boolean): Promise<void> {
  if (!is_active && !window.confirm(t('admin.suspendUserConfirm', { email: user.email }))) return
  try {
    await api.patch(`/admin/users/${user.id}`, { is_active })
    await load()
    toasts.ok(is_active ? t('admin.userReactivated') : t('admin.userSuspended'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <form class="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem_auto]" role="search" @submit.prevent="load">
      <div><label class="label" for="au-q">{{ $t('admin.searchUsers') }}</label><input id="au-q" v-model="filters.q" type="search" class="input" /></div>
      <div>
        <label class="label" for="au-role">{{ $t('admin.role') }}</label>
        <select id="au-role" v-model="filters.role" class="input" @change="load">
          <option value="">{{ $t('common.all') }}</option>
          <option v-for="role in ['attendee', 'organizer', 'event_admin', 'platform_admin']" :key="role" :value="role">{{ $t(`role.${role}`) }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-secondary self-end">{{ $t('home.find') }}</button>
    </form>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <div v-else-if="page" class="table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('auth.name') }}</th><th>{{ $t('admin.role') }}</th><th>{{ $t('admin.emailStatus') }}</th><th>{{ $t('admin.account') }}</th><th>{{ $t('admin.joined') }}</th><th><span class="sr-only">{{ $t('common.actions') }}</span></th></tr></thead>
        <tbody>
          <tr v-for="user in page.items" :key="user.id">
            <td>{{ user.name }}<div class="text-ink-soft">{{ user.email }}</div></td>
            <td>{{ $t(`role.${user.role}`) }}</td>
            <td><span class="badge" :class="user.is_verified ? 'badge-ok' : 'badge-warn'">{{ user.is_verified ? $t('account.verified') : $t('admin.unverified') }}</span></td>
            <td><span class="badge" :class="user.is_active ? 'badge-ok' : 'badge-bad'">{{ user.is_active ? $t('status.active') : $t('status.suspended') }}</span></td>
            <td>{{ dateOnly(user.created_at) }}</td>
            <td>
              <template v-if="user.id !== auth.user?.id">
                <button v-if="user.is_active" type="button" class="btn btn-danger btn-sm" @click="setActive(user, false)">{{ $t('admin.suspend') }}</button>
                <button v-else type="button" class="btn btn-secondary btn-sm" @click="setActive(user, true)">{{ $t('admin.reactivate') }}</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="page" class="hint">{{ $t('orders.showing', { shown: page.items.length, total: page.total }) }}</p>
  </div>
</template>
