<script setup lang="ts">
/**
 * Basic analytics of one event: capacity, revenue, sales over time, ticket types, campaigns, attendance.
 * All numbers come from BiletFlow's own orders, tickets, refunds and check-ins.
 */
import { computed, onMounted, reactive, ref } from 'vue'

import BarChart, { type ChartPoint } from '@/components/BarChart.vue'
import StatTile from '@/components/StatTile.vue'
import { api } from '@/lib/api'
import { errorText, money } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import type { Analytics } from '@/types'

const { event } = useManagedEvent()
const filters = reactive({ from: '', to: '', ticket_type_id: '' })
const data = ref<Analytics | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  problem.value = ''
  try {
    data.value = await api.get<Analytics>(`/organizer/events/${event.value.id}/analytics`, {
      date_from: filters.from ? new Date(`${filters.from}T00:00:00`).toISOString() : null,
      date_to: filters.to ? new Date(`${filters.to}T23:59:59`).toISOString() : null,
      ticket_type_id: filters.ticket_type_id,
    })
  } catch (error) {
    problem.value = errorText(error)
  }
}

function reset(): void {
  Object.assign(filters, { from: '', to: '', ticket_type_id: '' })
  void load()
}

const dayLabel = (iso: string): string => `${iso.slice(8, 10)}.${iso.slice(5, 7)}`
const ticketPoints = computed<ChartPoint[]>(() =>
  (data.value?.sales_over_time ?? []).map((point) => ({ label: dayLabel(point.date), value: point.tickets, detail: money(point.revenue) })))
const revenuePoints = computed<ChartPoint[]>(() =>
  (data.value?.sales_over_time ?? []).map((point) => ({ label: dayLabel(point.date), value: point.revenue })))
const share = (part: number, whole: number): number => (whole ? Math.round((100 * part) / whole) : 0)

onMounted(load)
</script>

<template>
  <div class="space-y-6">
    <!-- Filters sit in one row above everything they affect -->
    <form class="card grid gap-3 sm:grid-cols-[1fr_1fr_1.4fr_auto_auto]" @submit.prevent="load">
      <div><label class="label" for="an-from">{{ $t('analytics.from') }}</label><input id="an-from" v-model="filters.from" type="date" class="input" /></div>
      <div><label class="label" for="an-to">{{ $t('analytics.to') }}</label><input id="an-to" v-model="filters.to" type="date" class="input" :min="filters.from" /></div>
      <div>
        <label class="label" for="an-type">{{ $t('ticket.type') }}</label>
        <select id="an-type" v-model="filters.ticket_type_id" class="input">
          <option value="">{{ $t('analytics.allTypes') }}</option>
          <option v-for="type in event.ticket_types" :key="type.id" :value="type.id">{{ type.name }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-primary self-end">{{ $t('analytics.apply') }}</button>
      <button type="button" class="btn btn-secondary self-end" @click="reset">{{ $t('analytics.reset') }}</button>
    </form>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!data" class="text-ink-soft">{{ $t('common.loading') }}</p>

    <template v-else>
      <section :aria-label="$t('analytics.capacity')" class="grid gap-4 sm:grid-cols-3">
        <StatTile :label="$t('analytics.sold')" :value="`${data.capacity.sold} / ${data.capacity.total}`" :meter="data.capacity.percent_sold" :hint="$t('analytics.percentSold', { n: data.capacity.percent_sold })" />
        <StatTile :label="$t('analytics.remaining')" :value="String(data.capacity.remaining)" />
        <StatTile :label="$t('analytics.attendance')" :value="`${data.attendance.checked_in} / ${data.attendance.registered}`" :meter="data.attendance.percent" :hint="$t('analytics.absent', { n: data.attendance.absent, percent: data.attendance.percent })" />
      </section>

      <section :aria-label="$t('analytics.revenue')">
        <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile :label="$t('analytics.gross')" :value="money(data.revenue.gross)" />
          <StatTile :label="$t('analytics.discounts')" :value="money(data.revenue.discounts)" />
          <StatTile :label="$t('analytics.refunds')" :value="money(data.revenue.refunds)" />
          <StatTile :label="$t('analytics.net')" :value="money(data.revenue.net)" />
        </div>
        <p class="hint">{{ $t('common.demoMoney') }}</p>
      </section>

      <!-- Tickets and money have different scales, so they get two charts instead of two axes -->
      <div class="grid gap-6 lg:grid-cols-2">
        <section class="card"><BarChart :points="ticketPoints" :title="$t('analytics.ticketsPerDay')" /></section>
        <section class="card"><BarChart :points="revenuePoints" :title="$t('analytics.revenuePerDay')" :format="money" /></section>
      </div>

      <section>
        <h2 class="mb-3">{{ $t('analytics.byType') }}</h2>
        <div class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>{{ $t('ticket.type') }}</th><th class="num">{{ $t('tickets.price') }}</th><th class="w-1/3">{{ $t('analytics.sold') }}</th>
                <th class="num">{{ $t('analytics.remaining') }}</th><th class="num">{{ $t('tickets.checkedIn') }}</th><th class="num">{{ $t('analytics.net') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in data.by_ticket_type" :key="row.ticket_type_id">
                <td class="font-semibold">{{ row.name }}</td>
                <td class="num">{{ row.price ? money(row.price) : $t('event.free') }}</td>
                <td>
                  <div class="flex items-center gap-3">
                    <div class="h-2 flex-1 overflow-hidden rounded-full bg-sky-pale" role="meter" :aria-valuenow="row.sold" aria-valuemin="0" :aria-valuemax="row.quantity" :aria-label="`${row.name}: ${row.sold} / ${row.quantity}`">
                      <div class="h-full rounded-full bg-chart" :style="{ width: `${share(row.sold, row.quantity)}%` }" />
                    </div>
                    <span class="w-20 text-right tabular-nums">{{ row.sold }} / {{ row.quantity }}</span>
                  </div>
                </td>
                <td class="num">{{ row.remaining }}</td><td class="num">{{ row.checked_in }}</td><td class="num">{{ money(row.revenue) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section>
        <h2 class="mb-3">{{ $t('analytics.campaigns') }}</h2>
        <p v-if="!data.campaigns.length" class="card text-ink-soft">{{ $t('promo.empty') }}</p>
        <div v-else class="table-wrap">
          <table class="table">
            <thead>
              <tr>
                <th>{{ $t('promo.name') }}</th><th>{{ $t('promo.code') }}</th><th class="num">{{ $t('promo.redemptions') }}</th><th class="num">{{ $t('promo.tickets') }}</th>
                <th class="num">{{ $t('analytics.gross') }}</th><th class="num">{{ $t('analytics.discounts') }}</th><th class="num">{{ $t('analytics.net') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in data.campaigns" :key="row.campaign_id">
                <td class="font-semibold">{{ row.name }}<span v-if="!row.is_active" class="badge badge-bad ml-2">{{ $t('promo.disabled') }}</span></td>
                <td>{{ row.code }}</td><td class="num">{{ row.redemptions }}</td><td class="num">{{ row.tickets }}</td>
                <td class="num">{{ money(row.gross) }}</td><td class="num">{{ money(row.discount) }}</td><td class="num">{{ money(row.net) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>
