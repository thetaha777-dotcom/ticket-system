<script setup lang="ts">
/** Overview tab: publish / unpublish / cancel / duplicate, the public link, key numbers and money. */
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRouter } from 'vue-router'

import ModalDialog from '@/components/ModalDialog.vue'
import StatTile from '@/components/StatTile.vue'
import { api } from '@/lib/api'
import { money } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { EventManage, SalesSummary } from '@/types'

const { event, reload } = useManagedEvent()
const router = useRouter()
const toasts = useToastStore()
const { t } = useI18n()

const sales = ref<SalesSummary | null>(null)
const cancelOpen = ref(false)
const cancelReason = ref('')
const busy = ref(false)

const publicLink = computed(() => {
  const base = `${window.location.origin}/e/${event.value.slug}`
  return event.value.visibility === 'private' ? `${base}?access_key=${event.value.access_key}` : base
})
const hasPaidTypes = computed(() => event.value.ticket_types.some((type) => type.type === 'paid'))

async function act(action: 'publish' | 'unpublish', done: string): Promise<void> {
  busy.value = true
  try {
    await api.post(`/organizer/events/${event.value.id}/${action}`)
    await reload()
    toasts.ok(done)
  } catch (error) {
    toasts.error(error)
  } finally {
    busy.value = false
  }
}

async function cancelEvent(): Promise<void> {
  busy.value = true
  try {
    await api.post(`/organizer/events/${event.value.id}/cancel`, { reason: cancelReason.value || null })
    cancelOpen.value = false
    await Promise.all([reload(), loadSales()])
    toasts.ok(t('manage.cancelledDone'))
  } catch (error) {
    toasts.error(error)
  } finally {
    busy.value = false
  }
}

async function duplicate(): Promise<void> {
  try {
    const copy = await api.post<EventManage>(`/organizer/events/${event.value.id}/duplicate`)
    toasts.ok(t('manage.duplicated'))
    await router.push({ name: 'event-edit', params: { id: copy.id } })
  } catch (error) {
    toasts.error(error)
  }
}

async function copyLink(): Promise<void> {
  try {
    await navigator.clipboard.writeText(publicLink.value)
    toasts.ok(t('common.copied'))
  } catch {
    /* clipboard blocked: the link is visible and can be selected by hand */
  }
}

async function loadSales(): Promise<void> {
  try {
    sales.value = await api.get<SalesSummary>(`/organizer/events/${event.value.id}/sales`)
  } catch (error) {
    toasts.error(error)
  }
}
onMounted(loadSales)
</script>

<template>
  <div class="space-y-6">
    <section class="card">
      <h2 class="card-title">{{ $t('manage.publication') }}</h2>
      <p class="mb-4 max-w-[65ch] text-sm text-ink-soft">{{ $t(`manage.statusHelp.${event.status}`) }}</p>
      <p v-if="hasPaidTypes && !event.paid_sales_active && event.status !== 'cancelled'" class="notice notice-warn mb-4">
        {{ $t('manage.paidInactive') }}
        <RouterLink :to="{ name: 'manage-activation', params: { id: event.id } }">{{ $t('manage.tab.activation') }}</RouterLink>
      </p>
      <div class="flex flex-wrap gap-2">
        <button v-if="event.status === 'draft' || event.status === 'unpublished'" type="button" class="btn btn-sun" :disabled="busy" @click="act('publish', t('manage.published'))">{{ $t('manage.publish') }}</button>
        <button v-if="event.status === 'published'" type="button" class="btn btn-secondary" :disabled="busy" @click="act('unpublish', t('manage.unpublished'))">{{ $t('manage.unpublish') }}</button>
        <RouterLink class="btn btn-secondary" :to="{ name: 'event', params: { slug: event.slug } }">{{ event.status === 'published' ? $t('manage.viewPage') : $t('manage.preview') }}</RouterLink>
        <RouterLink v-if="event.status !== 'cancelled'" class="btn btn-secondary" :to="{ name: 'event-edit', params: { id: event.id } }">{{ $t('manage.edit') }}</RouterLink>
        <button type="button" class="btn btn-secondary" @click="duplicate">{{ $t('manage.duplicate') }}</button>
        <button v-if="event.status !== 'cancelled'" type="button" class="btn btn-danger" @click="cancelOpen = true">{{ $t('manage.cancelEvent') }}</button>
      </div>
      <div v-if="event.status === 'published'" class="mt-5 border-t border-line pt-4">
        <label class="label" for="public-link">{{ event.visibility === 'private' ? $t('manage.inviteLink') : $t('manage.publicLink') }}</label>
        <div class="flex gap-2">
          <input id="public-link" class="input" readonly :value="publicLink" @focus="($event.target as HTMLInputElement).select()" />
          <button type="button" class="btn btn-secondary shrink-0" @click="copyLink">{{ $t('common.copy') }}</button>
        </div>
      </div>
    </section>

    <section v-if="event.stats" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
      <StatTile :label="$t('org.ticketsSold')" :value="`${event.stats.tickets_sold} / ${event.stats.capacity}`" :meter="event.stats.capacity ? (100 * event.stats.tickets_sold) / event.stats.capacity : 0" />
      <StatTile :label="$t('manage.inCheckout')" :value="String(event.stats.tickets_reserved)" :hint="$t('manage.inCheckoutHint')" />
      <StatTile :label="$t('manage.orders')" :value="String(event.stats.orders)" />
      <StatTile :label="$t('org.checkedIn')" :value="String(event.stats.checked_in)" :meter="event.stats.tickets_sold ? (100 * event.stats.checked_in) / event.stats.tickets_sold : 0" />
    </section>

    <section v-if="sales" class="card">
      <h2 class="card-title">{{ $t('manage.money') }}</h2>
      <p class="mb-4 text-sm text-ink-soft">{{ $t('manage.moneyDemo') }}</p>
      <dl class="grid gap-x-8 gap-y-2 sm:grid-cols-2">
        <div class="flex justify-between gap-4"><dt>{{ $t('analytics.gross') }}</dt><dd class="tabular-nums">{{ money(sales.gross_sales) }}</dd></div>
        <div class="flex justify-between gap-4"><dt>{{ $t('analytics.discounts') }}</dt><dd class="tabular-nums">−{{ money(sales.discounts) }}</dd></div>
        <div class="flex justify-between gap-4"><dt>{{ $t('analytics.refunds') }} ({{ sales.refunded_orders }})</dt><dd class="tabular-nums">−{{ money(sales.refunds) }}</dd></div>
        <div class="flex justify-between gap-4"><dt>{{ $t('manage.fees') }}</dt><dd class="tabular-nums">−{{ money(sales.processing_fees) }}</dd></div>
        <div class="flex justify-between gap-4 border-t border-line pt-2 font-semibold"><dt>{{ $t('analytics.net') }}</dt><dd class="tabular-nums">{{ money(sales.net_revenue) }}</dd></div>
        <div class="flex justify-between gap-4 border-t border-line pt-2 font-semibold"><dt>{{ $t('manage.payout') }}</dt><dd class="tabular-nums">{{ money(sales.estimated_payout) }}</dd></div>
      </dl>
    </section>

    <ModalDialog :open="cancelOpen" :title="$t('manage.cancelEvent')" @close="cancelOpen = false">
      <form class="space-y-4" @submit.prevent="cancelEvent">
        <p class="notice notice-bad">{{ $t('manage.cancelWarning') }}</p>
        <div>
          <label class="label" for="cancel-reason">{{ $t('manage.cancelReason') }}</label>
          <textarea id="cancel-reason" v-model="cancelReason" class="input" maxlength="500" rows="3" />
          <p class="hint">{{ $t('manage.cancelReasonHint') }}</p>
        </div>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="cancelOpen = false">{{ $t('manage.keepEvent') }}</button>
          <button type="submit" class="btn btn-danger" :disabled="busy">{{ $t('manage.cancelEvent') }}</button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>
