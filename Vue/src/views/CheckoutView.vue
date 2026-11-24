<script setup lang="ts">
/** Payment step for a pending order. The payment is a clearly labelled simulation. */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'

import CountdownTimer from '@/components/CountdownTimer.vue'
import { api } from '@/lib/api'
import { dateTime, errorText, lineLabel, money } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { Order } from '@/types'

const props = defineProps<{ id: string }>()
const router = useRouter()
const toasts = useToastStore()
const { t } = useI18n()

const order = ref<Order | null>(null)
const problem = ref('')
const declined = ref(false)
const expired = ref(false)
const busy = ref(false)

async function load(): Promise<void> {
  try {
    order.value = await api.get<Order>(`/orders/${props.id}`)
    if (order.value.status !== 'pending') await router.replace({ name: 'order', params: { id: props.id } })
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function pay(outcome: 'success' | 'failure'): Promise<void> {
  busy.value = true
  problem.value = ''
  declined.value = false
  try {
    const result = await api.post<Order>(`/orders/${props.id}/pay`, { outcome })
    if (result.status === 'completed') {
      toasts.ok(t('checkout.paid'))
      await router.replace({ name: 'order', params: { id: props.id } })
    } else {
      order.value = result
      declined.value = true
    }
  } catch (error) {
    problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}

async function abandon(): Promise<void> {
  try {
    await api.post(`/orders/${props.id}/cancel`, {})
    await router.replace({ name: 'event', params: { slug: order.value!.event.slug } })
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-narrow">
    <p v-if="problem && !order" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!order" class="text-ink-soft">{{ $t('common.loading') }}</p>

    <template v-else>
      <h1 class="mb-2">{{ $t('checkout.title') }}</h1>
      <p class="mb-6 text-ink-soft">{{ order.event.title }}, {{ dateTime(order.event.start_at, order.event.timezone) }}</p>

      <div v-if="expired" class="notice notice-bad" role="alert">
        <p class="font-semibold">{{ $t('checkout.expired') }}</p>
        <RouterLink class="btn btn-secondary btn-sm mt-3" :to="{ name: 'event', params: { slug: order.event.slug } }">{{ $t('checkout.startAgain') }}</RouterLink>
      </div>

      <template v-else>
        <div class="card mb-5 flex items-center justify-between gap-4">
          <p class="text-sm">{{ $t('checkout.heldFor') }}</p>
          <CountdownTimer v-if="order.expires_at" :until="order.expires_at" @expired="expired = true" />
        </div>

        <div class="card mb-5">
          <h2 class="card-title">{{ $t('order.number', { number: order.number }) }}</h2>
          <ul class="space-y-1 text-sm">
            <li v-for="item in order.items" :key="item.id" class="flex justify-between gap-3">
              <span>{{ lineLabel(item) }}</span>
              <span class="tabular-nums">{{ money(item.unit_price * item.quantity) }}</span>
            </li>
            <li v-if="order.discount_total" class="flex justify-between gap-3 font-semibold text-ok">
              <span>{{ $t('event.discount', { code: order.promo_code }) }}</span><span class="tabular-nums">−{{ money(order.discount_total) }}</span>
            </li>
          </ul>
          <p class="mt-3 flex items-baseline justify-between border-t border-dashed border-line pt-3 font-semibold">
            <span>{{ $t('event.total') }}</span><span class="font-display text-3xl tabular-nums">{{ money(order.total) }}</span>
          </p>
        </div>

        <div class="card border-sun">
          <h2 class="card-title">{{ $t('checkout.demoTitle') }}</h2>
          <p v-if="declined" class="notice notice-bad mb-4" role="alert">{{ $t('checkout.declined') }}</p>
          <p v-if="problem" class="notice notice-bad mb-4" role="alert">{{ problem }}</p>
          <div class="flex flex-col gap-2 sm:flex-row">
            <button type="button" class="btn btn-sun flex-1" :disabled="busy" @click="pay('success')">{{ $t('checkout.paySuccess', { amount: money(order.total) }) }}</button>
            <button type="button" class="btn btn-secondary" :disabled="busy" @click="pay('failure')">{{ $t('checkout.payFailure') }}</button>
          </div>
        </div>
        <button type="button" class="btn btn-ghost mt-4" @click="abandon">{{ $t('checkout.abandon') }}</button>
      </template>
    </template>
  </div>
</template>
