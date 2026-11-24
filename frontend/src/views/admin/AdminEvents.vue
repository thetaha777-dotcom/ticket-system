<script setup lang="ts">
/** All events on the platform; suspend a suspicious event to hide it and stop its sales. */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import ModalDialog from '@/components/ModalDialog.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateOnly, errorText } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { AdminEventRow, Page } from '@/types'

const toasts = useToastStore()
const { t } = useI18n()
const filters = reactive({ q: '', suspended: '' })
const page = ref<Page<AdminEventRow> | null>(null)
const problem = ref('')
const target = ref<AdminEventRow | null>(null)
const reason = ref('')

async function load(): Promise<void> {
  try {
    page.value = await api.get<Page<AdminEventRow>>('/admin/events', { ...filters, limit: 100 })
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function suspend(): Promise<void> {
  try {
    await api.post(`/admin/events/${target.value!.id}/suspend`, { reason: reason.value })
    target.value = null
    reason.value = ''
    await load()
    toasts.ok(t('admin.eventSuspended'))
  } catch (error) {
    toasts.error(error)
  }
}

async function unsuspend(event: AdminEventRow): Promise<void> {
  try {
    await api.post(`/admin/events/${event.id}/unsuspend`)
    await load()
    toasts.ok(t('admin.eventRestored'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <form class="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem_auto]" role="search" @submit.prevent="load">
      <div><label class="label" for="ae-q">{{ $t('admin.searchEvents') }}</label><input id="ae-q" v-model="filters.q" type="search" class="input" /></div>
      <div>
        <label class="label" for="ae-susp">{{ $t('admin.show') }}</label>
        <select id="ae-susp" v-model="filters.suspended" class="input" @change="load">
          <option value="">{{ $t('common.all') }}</option><option value="true">{{ $t('admin.onlySuspended') }}</option><option value="false">{{ $t('admin.notSuspended') }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-secondary self-end">{{ $t('home.find') }}</button>
    </form>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <div v-else-if="page" class="table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('order.event') }}</th><th>{{ $t('event.organizer') }}</th><th>{{ $t('common.status') }}</th><th class="num">{{ $t('org.ticketsSold') }}</th><th class="num">{{ $t('admin.openReports') }}</th><th><span class="sr-only">{{ $t('common.actions') }}</span></th></tr></thead>
        <tbody>
          <tr v-for="event in page.items" :key="event.id">
            <td><RouterLink class="font-semibold" :to="{ name: 'event', params: { slug: event.slug } }">{{ event.title }}</RouterLink><div class="text-ink-soft">{{ dateOnly(event.start_at) }}</div></td>
            <td>{{ event.organizer.name }}<div class="text-ink-soft">{{ event.organizer.email }}</div></td>
            <td>
              <StatusBadge :status="event.status" />
              <div v-if="event.is_suspended" class="mt-1"><span class="badge badge-bad">{{ $t('status.suspended') }}</span><div class="text-ink-soft">{{ event.suspended_reason }}</div></div>
            </td>
            <td class="num">{{ event.tickets_sold }}</td>
            <td class="num">{{ event.open_reports }}</td>
            <td>
              <button v-if="event.is_suspended" type="button" class="btn btn-secondary btn-sm" @click="unsuspend(event)">{{ $t('admin.restore') }}</button>
              <button v-else type="button" class="btn btn-danger btn-sm" @click="target = event">{{ $t('admin.suspend') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ModalDialog :open="target !== null" :title="$t('admin.suspendEventTitle')" @close="target = null">
      <form v-if="target" class="space-y-4" @submit.prevent="suspend">
        <p>{{ $t('admin.suspendEventText', { title: target.title }) }}</p>
        <div><label class="label" for="susp-reason">{{ $t('admin.reason') }}</label><textarea id="susp-reason" v-model="reason" class="input" required minlength="3" maxlength="500" /></div>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="target = null">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-danger">{{ $t('admin.suspend') }}</button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>
