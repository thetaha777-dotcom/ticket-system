<script setup lang="ts">
/** Platform numbers at a glance and CSV exports of basic operational reports. */
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import StatTile from '@/components/StatTile.vue'
import { api } from '@/lib/api'
import { errorText, money } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { AdminOverview } from '@/types'

const toasts = useToastStore()
const data = ref<AdminOverview | null>(null)
const problem = ref('')

async function exportCsv(report: string): Promise<void> {
  try {
    await api.download(`/admin/export/${report}.csv`, `biletflow-${report}.csv`)
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(async () => {
  try {
    data.value = await api.get<AdminOverview>('/admin/overview')
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
  <p v-else-if="!data" class="text-ink-soft">{{ $t('common.loading') }}</p>
  <div v-else class="space-y-8">
    <section>
      <h2 class="mb-3">{{ $t('admin.needsAttention') }}</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <RouterLink class="no-underline" :to="{ name: 'admin-reports' }"><StatTile :label="$t('admin.openReports')" :value="String(data.open_reports)" /></RouterLink>
        <RouterLink class="no-underline" :to="{ name: 'admin-support' }"><StatTile :label="$t('admin.openCases')" :value="String(data.open_support_cases)" /></RouterLink>
        <RouterLink class="no-underline" :to="{ name: 'admin-payments' }"><StatTile :label="$t('admin.paymentFailures')" :value="String(data.payment_failures)" /></RouterLink>
        <RouterLink class="no-underline" :to="{ name: 'admin-events' }"><StatTile :label="$t('admin.suspendedEvents')" :value="String(data.events_suspended)" /></RouterLink>
      </div>
    </section>
    <section>
      <h2 class="mb-3">{{ $t('admin.platform') }}</h2>
      <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatTile :label="$t('admin.users')" :value="String(data.users)" :hint="$t('admin.organizersCount', data.organizers)" />
        <StatTile :label="$t('admin.publishedEvents')" :value="String(data.events_published)" />
        <StatTile :label="$t('admin.completedOrders')" :value="String(data.orders_completed)" :hint="$t('admin.ticketsIssued', data.tickets_issued)" />
        <StatTile :label="$t('analytics.gross')" :value="money(data.gross_sales)" :hint="$t('common.demoMoney')" />
        <StatTile :label="$t('analytics.refunds')" :value="money(data.refunds_total)" />
        <StatTile :label="$t('admin.activeActivations')" :value="String(data.activations_active)" :hint="$t('admin.suspendedActivations', data.activations_suspended)" />
      </div>
    </section>
    <section class="card">
      <h2 class="card-title">{{ $t('admin.exports') }}</h2>
      <p class="mb-3 text-sm text-ink-soft">{{ $t('admin.exportsHint') }}</p>
      <div class="flex flex-wrap gap-2">
        <button v-for="report in ['orders', 'payments', 'users', 'events']" :key="report" type="button" class="btn btn-secondary" @click="exportCsv(report)">{{ $t(`admin.export.${report}`) }}</button>
      </div>
    </section>
  </div>
</template>
