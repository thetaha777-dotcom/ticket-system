<script setup lang="ts">
/** Events reported by users. Review each report; suspend the event from the Events tab if needed. */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { ReportRow } from '@/types'

const toasts = useToastStore()
const { t } = useI18n()
const status = ref('open')
const rows = ref<ReportRow[] | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    rows.value = await api.get<ReportRow[]>('/admin/reports', { status: status.value })
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function review(row: ReportRow, next: 'reviewed' | 'dismissed'): Promise<void> {
  try {
    await api.patch(`/admin/reports/${row.id}`, { status: next })
    await load()
    toasts.ok(t('admin.reportSaved'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <div class="mb-4 max-w-56">
      <label class="label" for="ar-status">{{ $t('admin.show') }}</label>
      <select id="ar-status" v-model="status" class="input" @change="load">
        <option value="open">{{ $t('status.open') }}</option><option value="reviewed">{{ $t('status.reviewed') }}</option><option value="dismissed">{{ $t('status.dismissed') }}</option><option value="">{{ $t('common.all') }}</option>
      </select>
    </div>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!rows" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <p v-else-if="!rows.length" class="card text-ink-soft">{{ $t('admin.noReports') }}</p>
    <ul v-else class="space-y-3">
      <li v-for="row in rows" :key="row.id" class="card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div class="min-w-0">
            <p class="mb-1 flex flex-wrap items-center gap-2"><StatusBadge :status="row.status" /><span v-if="row.event_suspended" class="badge badge-bad">{{ $t('admin.eventIsSuspended') }}</span></p>
            <h2 class="text-xl"><RouterLink :to="{ name: 'event', params: { slug: row.event_slug } }">{{ row.event_title }}</RouterLink></h2>
            <p class="mt-2 max-w-[70ch] whitespace-pre-line">{{ row.reason }}</p>
            <p class="mt-2 text-sm text-ink-soft">{{ row.reporter.name }} ({{ row.reporter.email }}), {{ dateTime(row.created_at) }}</p>
          </div>
          <div v-if="row.status === 'open'" class="flex flex-wrap gap-2">
            <button type="button" class="btn btn-secondary btn-sm" @click="review(row, 'reviewed')">{{ $t('admin.markReviewed') }}</button>
            <button type="button" class="btn btn-secondary btn-sm" @click="review(row, 'dismissed')">{{ $t('admin.dismiss') }}</button>
            <RouterLink class="btn btn-danger btn-sm" :to="{ name: 'admin-events' }">{{ $t('admin.goSuspend') }}</RouterLink>
          </div>
        </div>
      </li>
    </ul>
  </div>
</template>
