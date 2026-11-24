<script setup lang="ts">
/** Monitoring of (simulated) payments, payment failures and refunds. */
import { onMounted, ref } from 'vue'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, money } from '@/lib/format'
import type { Payment, Refund } from '@/types'

const q = ref('')
const status = ref('')
const payments = ref<Payment[] | null>(null)
const refunds = ref<Refund[]>([])
const problem = ref('')

async function load(): Promise<void> {
  try {
    ;[payments.value, refunds.value] = await Promise.all([api.get<Payment[]>('/admin/payments', { q: q.value, status: status.value }), api.get<Refund[]>('/admin/refunds')])
  } catch (error) {
    problem.value = errorText(error)
  }
}
onMounted(load)
</script>

<template>
  <div class="space-y-8">
    <p class="notice notice-warn">{{ $t('admin.paymentsDemo') }}</p>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <section>
      <h2 class="mb-3">{{ $t('admin.payments') }}</h2>
      <form class="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem_auto]" role="search" @submit.prevent="load">
        <div><label class="label" for="ap-q">{{ $t('admin.searchPayments') }}</label><input id="ap-q" v-model="q" type="search" class="input" :placeholder="$t('admin.searchPaymentsHint')" /></div>
        <div>
          <label class="label" for="ap-status">{{ $t('common.status') }}</label>
          <select id="ap-status" v-model="status" class="input" @change="load">
            <option value="">{{ $t('common.all') }}</option><option value="succeeded">{{ $t('status.succeeded') }}</option><option value="failed">{{ $t('status.failed') }}</option>
          </select>
        </div>
        <button type="submit" class="btn btn-secondary self-end">{{ $t('home.find') }}</button>
      </form>
      <p v-if="payments && !payments.length" class="card text-ink-soft">{{ $t('admin.noPayments') }}</p>
      <div v-else-if="payments" class="table-wrap">
        <table class="table">
          <thead><tr><th>{{ $t('admin.reference') }}</th><th>{{ $t('admin.kind') }}</th><th class="num">{{ $t('admin.amount') }}</th><th class="num">{{ $t('manage.fees') }}</th><th>{{ $t('common.status') }}</th><th>{{ $t('admin.when') }}</th></tr></thead>
          <tbody>
            <tr v-for="payment in payments" :key="payment.id">
              <td class="tabular-nums">{{ payment.provider_reference }}</td>
              <td>{{ $t(`admin.paymentKind.${payment.kind}`) }}</td>
              <td class="num">{{ money(payment.amount) }}</td><td class="num">{{ money(payment.processing_fee) }}</td>
              <td><StatusBadge :status="payment.status" /><div v-if="payment.failure_reason" class="text-ink-soft">{{ payment.failure_reason }}</div></td>
              <td class="whitespace-nowrap">{{ dateTime(payment.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    <section>
      <h2 class="mb-3">{{ $t('analytics.refunds') }}</h2>
      <p v-if="!refunds.length" class="card text-ink-soft">{{ $t('admin.noRefunds') }}</p>
      <div v-else class="table-wrap">
        <table class="table">
          <thead><tr><th class="num">{{ $t('admin.amount') }}</th><th>{{ $t('admin.reason') }}</th><th>{{ $t('common.status') }}</th><th>{{ $t('admin.when') }}</th></tr></thead>
          <tbody>
            <tr v-for="refund in refunds" :key="refund.id">
              <td class="num">{{ money(refund.amount) }}</td><td>{{ refund.reason ?? '—' }}</td><td><StatusBadge :status="refund.status" /></td>
              <td class="whitespace-nowrap">{{ dateTime(refund.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  </div>
</template>
