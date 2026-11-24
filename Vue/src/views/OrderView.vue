<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import CalendarButtons from '@/components/CalendarButtons.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import SupportRequestButton from '@/components/SupportRequestButton.vue'
import TicketPass from '@/components/TicketPass.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, lineLabel, money } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { Order } from '@/types'

const props = defineProps<{ id: string }>()
const toasts = useToastStore()
const { t } = useI18n()
const order = ref<Order | null>(null)
const problem = ref('')

async function load(): Promise<void> {
  try {
    order.value = await api.get<Order>(`/orders/${props.id}`)
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function downloadAll(): Promise<void> {
  try {
    await api.download(`/orders/${props.id}/tickets.pdf`, `tickets-${order.value!.number}.pdf`)
  } catch (error) {
    toasts.error(error)
  }
}

async function cancelRegistration(): Promise<void> {
  if (!window.confirm(t('order.cancelConfirm'))) return
  try {
    order.value = await api.post<Order>(`/orders/${props.id}/cancel`, {})
    toasts.ok(t('order.cancelled'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!order" class="text-ink-soft">{{ $t('common.loading') }}</p>

    <template v-else>
      <div class="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="mb-1 flex items-center gap-2 text-ink-soft">{{ $t('order.number', { number: order.number }) }} <StatusBadge :status="order.status" /></p>
          <h1><RouterLink class="text-ink no-underline hover:underline" :to="{ name: 'event', params: { slug: order.event.slug } }">{{ order.event.title }}</RouterLink></h1>
          <p class="mt-2 text-lg">{{ dateTime(order.event.start_at, order.event.timezone) }}, {{ order.event.venue_name }}, {{ order.event.venue_city }}</p>
        </div>
        <div class="no-print flex flex-wrap gap-2">
          <RouterLink v-if="order.status === 'pending'" class="btn btn-sun" :to="{ name: 'checkout', params: { id: order.id } }">{{ $t('order.continuePayment') }}</RouterLink>
          <button v-if="order.tickets.some((ticket) => ticket.qr_payload)" type="button" class="btn btn-primary" @click="downloadAll">{{ $t('order.downloadAll') }}</button>
          <SupportRequestButton :order-id="order.id" />
        </div>
      </div>

      <p v-if="order.event.status === 'cancelled'" class="notice notice-bad mb-5">{{ $t('event.cancelledNote') }}</p>
      <p v-if="order.status === 'refunded'" class="notice mb-5">{{ $t('order.refundedNote', { amount: money(order.refunds[0]?.amount ?? order.total) }) }}</p>

      <div class="grid gap-8 lg:grid-cols-[1fr_20rem]">
        <section>
          <h2 class="mb-4">{{ $t('order.tickets') }}</h2>
          <div v-if="order.tickets.length" class="grid gap-5 sm:grid-cols-2">
            <TicketPass v-for="ticket in order.tickets" :key="ticket.id" :ticket="ticket" />
          </div>
          <p v-else class="card text-ink-soft">{{ $t('order.noTickets') }}</p>
        </section>

        <aside class="space-y-5">
          <div class="card">
            <h2 class="card-title">{{ $t('order.summary') }}</h2>
            <ul class="space-y-1 text-sm">
              <li v-for="item in order.items" :key="item.id" class="flex justify-between gap-3">
                <span>{{ lineLabel(item) }}</span>
                <span class="tabular-nums">{{ money(item.unit_price * item.quantity) }}</span>
              </li>
              <li v-if="order.discount_total" class="flex justify-between gap-3 font-semibold text-ok">
                <span>{{ $t('event.discount', { code: order.promo_code }) }}</span><span class="tabular-nums">−{{ money(order.discount_total) }}</span>
              </li>
              <li class="flex justify-between gap-3 border-t border-dashed border-line pt-2 text-base font-semibold">
                <span>{{ $t('event.total') }}</span><span class="tabular-nums">{{ money(order.total) }}</span>
              </li>
            </ul>
            <p v-if="order.total > 0" class="mt-3 text-sm text-ink-soft">{{ $t('order.demoPayment') }}</p>
            <ul v-if="order.payments.length" class="mt-3 space-y-1 border-t border-line pt-3 text-sm">
              <li v-for="payment in order.payments" :key="payment.id" class="flex items-center justify-between gap-2">
                <span>{{ dateTime(payment.created_at) }}</span><StatusBadge :status="payment.status" />
              </li>
            </ul>
          </div>
          <div class="card no-print"><CalendarButtons :event-ref="order.event.id" /></div>
          <button v-if="order.status === 'completed' && order.total === 0" type="button" class="btn btn-danger no-print w-full" @click="cancelRegistration">{{ $t('order.cancelRegistration') }}</button>
          <p v-else-if="order.status === 'completed'" class="text-sm text-ink-soft">{{ order.refund_eligible ? $t('order.refundHow') : $t('order.refundNotPossible') }}</p>
        </aside>
      </div>
    </template>
  </div>
</template>
