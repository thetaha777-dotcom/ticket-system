<script setup lang="ts">
/** Orders of the event: search, refund a paid order, cancel a free registration. */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import ModalDialog from '@/components/ModalDialog.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, money } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { Order, Page } from '@/types'

const { event, reload } = useManagedEvent()
const toasts = useToastStore()
const { t } = useI18n()

const filters = reactive({ q: '', status: '' })
const page = ref<Page<Order> | null>(null)
const problem = ref('')
const target = ref<Order | null>(null) // order in the refund / cancel dialog
const reason = ref('')

async function load(): Promise<void> {
  try {
    page.value = await api.get<Page<Order>>(`/organizer/events/${event.value.id}/orders`, { ...filters, limit: 100 })
  } catch (error) {
    problem.value = errorText(error)
  }
}

function ask(order: Order): void {
  target.value = order
  reason.value = ''
}

async function confirm(): Promise<void> {
  const order = target.value!
  const refund = order.total > 0
  try {
    await api.post(`/orders/${order.id}/${refund ? 'refund' : 'cancel'}`, { reason: reason.value || null })
    target.value = null
    await Promise.all([load(), reload()])
    toasts.ok(refund ? t('orders.refunded') : t('orders.cancelled'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div>
    <form class="mb-4 grid gap-3 sm:grid-cols-[1fr_14rem_auto]" role="search" @submit.prevent="load">
      <div><label class="label" for="orders-q">{{ $t('orders.search') }}</label><input id="orders-q" v-model="filters.q" type="search" class="input" :placeholder="$t('orders.searchHint')" /></div>
      <div>
        <label class="label" for="orders-status">{{ $t('common.status') }}</label>
        <select id="orders-status" v-model="filters.status" class="input" @change="load">
          <option value="">{{ $t('common.all') }}</option>
          <option v-for="status in ['pending', 'completed', 'refunded', 'cancelled', 'expired']" :key="status" :value="status">{{ $t(`status.${status}`) }}</option>
        </select>
      </div>
      <button type="submit" class="btn btn-secondary self-end">{{ $t('home.find') }}</button>
    </form>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!page" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <p v-else-if="!page.items.length" class="card text-ink-soft">{{ $t('orders.empty') }}</p>
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>{{ $t('order.order') }}</th><th>{{ $t('orders.buyer') }}</th><th class="num">{{ $t('order.ticketCount') }}</th>
            <th class="num">{{ $t('event.total') }}</th><th>{{ $t('common.status') }}</th><th>{{ $t('order.placed') }}</th>
            <th><span class="sr-only">{{ $t('common.actions') }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="order in page.items" :key="order.id">
            <td>
              <RouterLink class="font-semibold" :to="{ name: 'order', params: { id: order.id } }">{{ order.number }}</RouterLink>
              <div v-if="order.promo_code" class="text-ink-soft">{{ $t('orders.promo', { code: order.promo_code }) }}</div>
            </td>
            <td>{{ order.buyer_name }}<div class="text-ink-soft">{{ order.buyer_email }}</div></td>
            <td class="num">{{ order.quantity }}</td>
            <td class="num">{{ money(order.total) }}<div v-if="order.discount_total" class="text-ink-soft">−{{ money(order.discount_total) }}</div></td>
            <td><StatusBadge :status="order.status" /></td>
            <td class="whitespace-nowrap">{{ dateTime(order.created_at) }}</td>
            <td>
              <button v-if="order.status === 'completed' && order.total > 0" type="button" class="btn btn-danger btn-sm" :disabled="!order.refund_eligible" :title="order.refund_eligible ? '' : $t('orders.policyBlocks')" @click="ask(order)">{{ $t('orders.refund') }}</button>
              <button v-else-if="order.status === 'completed'" type="button" class="btn btn-danger btn-sm" @click="ask(order)">{{ $t('orders.cancel') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
    <p v-if="page && page.total > page.items.length" class="hint">{{ $t('orders.showing', { shown: page.items.length, total: page.total }) }}</p>

    <ModalDialog :open="target !== null" :title="target && target.total > 0 ? $t('orders.refundTitle') : $t('orders.cancelTitle')" @close="target = null">
      <form v-if="target" class="space-y-4" @submit.prevent="confirm">
        <p>
          {{ target.total > 0 ? $t('orders.refundText', { number: target.number, amount: money(target.total), name: target.buyer_name }) : $t('orders.cancelText', { number: target.number, name: target.buyer_name }) }}
        </p>
        <div><label class="label" for="order-reason">{{ $t('orders.reason') }}</label><input id="order-reason" v-model="reason" class="input" maxlength="500" /></div>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="target = null">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-danger">{{ target.total > 0 ? $t('orders.refundConfirm') : $t('orders.cancelConfirm') }}</button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>
