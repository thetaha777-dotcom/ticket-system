<script setup lang="ts">
/** Attendee list: one row per ticket, with search, status filter and CSV export. */
import { onMounted, reactive, ref } from 'vue'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { AttendeeRow } from '@/types'

const { event } = useManagedEvent()
const toasts = useToastStore()
const filters = reactive({ q: '', status: '' })
const rows = ref<AttendeeRow[] | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    rows.value = await api.get<AttendeeRow[]>(`/organizer/events/${event.value.id}/attendees`, filters)
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function exportCsv(): Promise<void> {
  try {
    await api.download(`/organizer/events/${event.value.id}/attendees.csv`, `attendees-${event.value.slug}.csv`)
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <form class="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem_auto_auto]" role="search" @submit.prevent="load">
      <div><label class="label" for="att-q">{{ $t('attendees.search') }}</label><input id="att-q" v-model="filters.q" type="search" class="input" :placeholder="$t('attendees.searchHint')" /></div>
      <div>
        <label class="label" for="att-status">{{ $t('common.status') }}</label>
        <select id="att-status" v-model="filters.status" class="input" @change="load">
          <option value="">{{ $t('common.all') }}</option>
          <option v-for="status in ['valid', 'checked_in', 'cancelled', 'refunded']" :key="status" :value="status">{{ $t(`status.${status}`) }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-secondary self-end">{{ $t('home.find') }}</button>
      <button type="button" class="btn btn-secondary self-end" @click="exportCsv">{{ $t('attendees.export') }}</button>
    </form>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!rows" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <p v-else-if="!rows.length" class="card text-ink-soft">{{ $t('attendees.empty') }}</p>
    <template v-else>
      <p class="mb-2 text-sm text-ink-soft">{{ $t('attendees.count', rows.length) }}</p>
      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>{{ $t('ticket.attendee') }}</th><th>{{ $t('ticket.type') }}</th><th>{{ $t('ticket.seat') }}</th><th>{{ $t('attendees.ticket') }}</th>
              <th>{{ $t('common.status') }}</th><th>{{ $t('attendees.checkedInAt') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in rows" :key="row.ticket_id">
              <td>{{ row.attendee_name }}<div class="text-ink-soft">{{ row.attendee_email }}</div></td>
              <td>{{ row.ticket_type }}</td>
              <td>{{ row.seat ?? '—' }}</td>
              <td class="tabular-nums">{{ row.code }}<div class="text-ink-soft">{{ row.order_number }}</div></td>
              <td><StatusBadge :status="row.status" /></td>
              <td class="whitespace-nowrap">{{ row.checked_in_at ? dateTime(row.checked_in_at, event.timezone) : '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>
