<script setup lang="ts">
/** Platform-wide audit trail of organizer and administrator actions, payments and refunds. */
import { onMounted, ref } from 'vue'

import { api } from '@/lib/api'
import { dateTime, errorText } from '@/lib/format'
import type { AuditEntry } from '@/types'

const action = ref('')
const entries = ref<AuditEntry[] | null>(null)
const problem = ref('')
const TYPES = ['event', 'ticket_type', 'payment', 'refund', 'order', 'promo', 'support', 'checkin', 'staff', 'activation', 'user', 'organizer', 'settings', 'report']

async function load(): Promise<void> {
  try {
    entries.value = await api.get<AuditEntry[]>('/admin/audit-log', { action: action.value, limit: 300 })
  } catch (error) {
    problem.value = errorText(error)
  }
}
onMounted(load)
</script>

<template>
  <div>
    <div class="mb-4 max-w-64">
      <label class="label" for="aa-type">{{ $t('history.type') }}</label>
      <select id="aa-type" v-model="action" class="input" @change="load">
        <option value="">{{ $t('common.all') }}</option>
        <option v-for="type in TYPES" :key="type" :value="type">{{ $t(`history.types.${type}`) }}</option>
      </select>
    </div>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!entries" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <div v-else class="table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('admin.when') }}</th><th>{{ $t('admin.actor') }}</th><th>{{ $t('admin.action') }}</th><th>{{ $t('analytics.details') }}</th></tr></thead>
        <tbody>
          <tr v-for="entry in entries" :key="entry.id">
            <td class="whitespace-nowrap">{{ dateTime(entry.created_at) }}</td><td>{{ entry.actor_name }}</td>
            <td class="whitespace-nowrap tabular-nums">{{ entry.action }}</td><td>{{ entry.description }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p class="hint">{{ $t('history.readonly') }}</p>
  </div>
</template>
