<script setup lang="ts">
/** Activity timeline of the event (audit trail). Entries can be filtered but never edited or deleted. */
import { onMounted, reactive, ref } from 'vue'

import { api } from '@/lib/api'
import { dateTime, errorText } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import type { AuditEntry } from '@/types'

const { event } = useManagedEvent()
const TYPES = ['event', 'ticket_type', 'payment', 'refund', 'order', 'promo', 'support', 'checkin', 'staff', 'activation']
const filters = reactive({ from: '', to: '', action: '' })
const entries = ref<AuditEntry[] | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  problem.value = ''
  try {
    entries.value = await api.get<AuditEntry[]>(`/organizer/events/${event.value.id}/history`, {
      date_from: filters.from ? new Date(`${filters.from}T00:00:00`).toISOString() : null,
      date_to: filters.to ? new Date(`${filters.to}T23:59:59`).toISOString() : null,
      action: filters.action,
    })
  } catch (error) {
    problem.value = errorText(error)
  }
}
const group = (action: string): string => action.split('.')[0]

onMounted(load)
</script>

<template>
  <div>
    <form class="card mb-5 grid gap-3 sm:grid-cols-[1fr_1fr_1.4fr_auto]" @submit.prevent="load">
      <div><label class="label" for="hi-from">{{ $t('analytics.from') }}</label><input id="hi-from" v-model="filters.from" type="date" class="input" /></div>
      <div><label class="label" for="hi-to">{{ $t('analytics.to') }}</label><input id="hi-to" v-model="filters.to" type="date" class="input" :min="filters.from" /></div>
      <div>
        <label class="label" for="hi-type">{{ $t('history.type') }}</label>
        <select id="hi-type" v-model="filters.action" class="input">
          <option value="">{{ $t('common.all') }}</option>
          <option v-for="type in TYPES" :key="type" :value="type">{{ $t(`history.types.${type}`) }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary self-end">{{ $t('analytics.apply') }}</button>
    </form>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!entries" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <p v-else-if="!entries.length" class="card text-ink-soft">{{ $t('history.empty') }}</p>
    <ol v-else class="relative ml-2 border-l-2 border-line">
      <li v-for="entry in entries" :key="entry.id" class="relative mb-4 pl-6">
        <span class="absolute top-1.5 -left-[7px] h-3 w-3 rounded-full border-2 border-white bg-sky-deep" aria-hidden="true" />
        <p class="text-sm text-ink-soft">
          <time :datetime="entry.created_at">{{ dateTime(entry.created_at, event.timezone) }}</time>, {{ entry.actor_name }}
          <span class="badge ml-1">{{ $t(`history.types.${group(entry.action)}`) }}</span>
        </p>
        <p>{{ entry.description }}</p>
      </li>
    </ol>
    <p class="hint">{{ $t('history.readonly') }}</p>
  </div>
</template>
