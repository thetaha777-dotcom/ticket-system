<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, money } from '@/lib/format'
import type { AdminOrderRow, Page } from '@/types'

const filters = reactive({ q: '', status: '' })
const page = ref<Page<AdminOrderRow> | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    page.value = await api.get<Page<AdminOrderRow>>('/admin/orders', { ...filters, limit: 100 })
  } catch (error) {
    problem.value = errorText(error)
  }
}
onMounted(load)
</script>

<template>
  <div>
    <form class="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem_auto]" role="search" @submit.prevent="load">
      <div><label class="label" for="ao-q">{{ $t('orders.search') }}</label><input id="ao-q" v-model="filters.q" type="search" class="input" :placeholder="$t('orders.searchHint')" /></div>
      <div>
        <label class="label" for="ao-status">{{ $t('common.status') }}</label>
        <select id="ao-status" v-model="filters.status" class="input" @change="load">
          <option value="">{{ $t('common.all') }}</option>
          <option v-for="status in ['pending', 'completed', 'refunded', 'cancelled', 'expired']" :key="status" :value="status">{{ $t(`status.${status}`) }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-secondary self-end">{{ $t('home.find') }}</button>
    </form>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <div v-else-if="page" class="table-wrap">
      <table class="table">
        <thead><tr><th>{{ $t('order.order') }}</th><th>{{ $t('order.event') }}</th><th>{{ $t('orders.buyer') }}</th><th class="num">{{ $t('order.ticketCount') }}</th><th class="num">{{ $t('event.total') }}</th><th>{{ $t('common.status') }}</th><th>{{ $t('order.placed') }}</th></tr></thead>
        <tbody>
          <tr v-for="order in page.items" :key="order.id">
            <td class="font-semibold">{{ order.number }}<div v-if="order.promo_code" class="font-normal text-ink-soft">{{ $t('orders.promo', { code: order.promo_code }) }}</div></td>
            <td>{{ order.event_title }}</td>
            <td>{{ order.buyer_name }}<div class="text-ink-soft">{{ order.buyer_email }}</div></td>
            <td class="num">{{ order.quantity }}</td><td class="num">{{ money(order.total) }}</td>
            <td><StatusBadge :status="order.status" /></td>
            <td class="whitespace-nowrap">{{ dateTime(order.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="page" class="hint">{{ $t('orders.showing', { shown: page.items.length, total: page.total }) }}</p>
  </div>
</template>
