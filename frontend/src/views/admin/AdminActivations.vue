<script setup lang="ts">
/** Paid-sales activation records; suspend paid sales of an event when fraud or a policy violation is suspected. */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateOnly, errorText, money } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { ActivationRow } from '@/types'

const toasts = useToastStore()
const { t } = useI18n()
const rows = ref<ActivationRow[] | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    rows.value = await api.get<ActivationRow[]>('/admin/activations')
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function suspend(row: ActivationRow): Promise<void> {
  const reason = window.prompt(t('admin.suspendSalesPrompt', { title: row.event_title }))
  if (!reason || reason.trim().length < 3) return
  try {
    await api.post(`/admin/activations/${row.id}/suspend`, { reason })
    await load()
    toasts.ok(t('admin.salesSuspended'))
  } catch (error) {
    toasts.error(error)
  }
}

async function reinstate(row: ActivationRow): Promise<void> {
  try {
    await api.post(`/admin/activations/${row.id}/reinstate`)
    await load()
    toasts.ok(t('admin.salesReinstated'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
  <p v-else-if="!rows" class="text-ink-soft">{{ $t('common.loading') }}</p>
  <p v-else-if="!rows.length" class="card text-ink-soft">{{ $t('admin.noActivations') }}</p>
  <div v-else class="table-wrap">
    <table class="table">
      <thead><tr><th>{{ $t('order.event') }}</th><th>{{ $t('event.organizer') }}</th><th class="num">{{ $t('admin.fee') }}</th><th>{{ $t('admin.checks') }}</th><th>{{ $t('common.status') }}</th><th><span class="sr-only">{{ $t('common.actions') }}</span></th></tr></thead>
      <tbody>
        <tr v-for="row in rows" :key="row.id">
          <td class="font-semibold">{{ row.event_title }}<div class="font-normal text-ink-soft">{{ dateOnly(row.created_at) }}</div></td>
          <td>{{ row.organizer.name }}<div class="text-ink-soft">{{ row.organizer.email }}</div></td>
          <td class="num">{{ money(row.fee_amount) }}</td>
          <td>
            <div>{{ row.fee_paid ? '✓' : '○' }} {{ $t('admin.feePaid') }}</div>
            <div>{{ row.terms_accepted ? '✓' : '○' }} {{ $t('admin.termsAccepted') }}</div>
          </td>
          <td><StatusBadge :status="row.status" /><div v-if="row.suspended_reason" class="text-ink-soft">{{ row.suspended_reason }}</div></td>
          <td>
            <button v-if="row.status === 'suspended'" type="button" class="btn btn-secondary btn-sm" @click="reinstate(row)">{{ $t('admin.reinstate') }}</button>
            <button v-else type="button" class="btn btn-danger btn-sm" @click="suspend(row)">{{ $t('admin.suspendSales') }}</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
