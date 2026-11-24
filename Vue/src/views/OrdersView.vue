<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, money } from '@/lib/format'
import type { Order } from '@/types'

const orders = ref<Order[] | null>(null)
const problem = ref('')

onMounted(async () => {
  try {
    orders.value = await api.get<Order[]>('/orders')
  } catch (error) {
    problem.value = errorText(error)
  }
})
</script>

<template>
  <div class="page">
    <h1 class="mb-6">{{ $t('order.myOrders') }}</h1>
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!orders" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <div v-else-if="!orders.length" class="card">
      <p class="mb-3 text-ink-soft">{{ $t('order.empty') }}</p>
      <RouterLink class="btn btn-primary" :to="{ name: 'home' }">{{ $t('order.browse') }}</RouterLink>
    </div>
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>{{ $t('order.order') }}</th><th>{{ $t('order.event') }}</th><th class="num">{{ $t('order.ticketCount') }}</th>
            <th class="num">{{ $t('event.total') }}</th><th>{{ $t('common.status') }}</th><th>{{ $t('order.placed') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in orders" :key="order.id">
            <td><RouterLink class="font-semibold" :to="{ name: order.status === 'pending' ? 'checkout' : 'order', params: { id: order.id } }">{{ order.number }}</RouterLink></td>
            <td>{{ order.event.title }}<div class="text-ink-soft">{{ dateTime(order.event.start_at, order.event.timezone) }}</div></td>
            <td class="num">{{ order.quantity }}</td>
            <td class="num">{{ money(order.total) }}</td>
            <td><StatusBadge :status="order.status" /></td>
            <td class="whitespace-nowrap">{{ dateTime(order.created_at) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>
