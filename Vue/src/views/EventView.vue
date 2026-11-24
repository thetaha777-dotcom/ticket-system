<script setup lang="ts">
/**
 * Public event page: details, ticket or seat selection, promo code, price from the server,
 * and the step that starts checkout. Also the organizer's preview of a draft.
 */
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import CalendarButtons from '@/components/CalendarButtons.vue'
import ModalDialog from '@/components/ModalDialog.vue'
import SeatMapView from '@/components/SeatMap.vue'
import SupportRequestButton from '@/components/SupportRequestButton.vue'
import { api } from '@/lib/api'
import { categoryColour, dateTime, errorText, lineLabel, money, timeOnly } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { EventDetail, Order, PromoPreview, Quote, SeatMap } from '@/types'

const props = defineProps<{ slug: string }>()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toasts = useToastStore()
const { t } = useI18n()

const accessKey = computed(() => (typeof route.query.access_key === 'string' ? route.query.access_key : null))
const event = ref<EventDetail | null>(null)
const seatMap = ref<SeatMap | null>(null)
const loadProblem = ref('')

const quantities = reactive<Record<string, number>>({}) // ticket type id -> how many
const selectedSeats = ref<string[]>([])
const promoInput = ref('')
const promoCode = ref<string | null>(null) // the code that is applied right now
const promoNote = ref('')
const promoProblem = ref('')
const quote = ref<Quote | null>(null)
const quoteProblem = ref('')

const detailsOpen = ref(false)
const buyer = reactive({ name: '', email: '', phone: '' })
const attendeeNames = ref<string[]>([])
const busy = ref(false)
const checkoutProblem = ref('')

const reportOpen = ref(false)
const reportReason = ref('')

const isSeated = computed(() => event.value?.seating === 'assigned_seating')
const ticketCount = computed(() => (isSeated.value ? selectedSeats.value.length : Object.values(quantities).reduce((a, b) => a + b, 0)))

function selection(): Record<string, unknown> {
  const body: Record<string, unknown> = { event_id: event.value!.id, promo_code: promoCode.value }
  if (isSeated.value) body.seat_ids = selectedSeats.value
  else body.items = Object.entries(quantities).filter(([, n]) => n > 0).map(([id, n]) => ({ ticket_category_id: id, quantity: n }))
  return body
}

async function load(): Promise<void> {
  loadProblem.value = ''
  try {
    event.value = await api.get<EventDetail>(`/events/${props.slug}`, { access_key: accessKey.value })
    if (isSeated.value) seatMap.value = await api.get<SeatMap>(`/events/${props.slug}/seats`, { access_key: accessKey.value })
    document.title = `${event.value.title} — BiletFlow`
  } catch (error) {
    loadProblem.value = errorText(error)
  }
}

/** A Campaign QR link looks like /e/<slug>?c=<token>. The server turns the token into a promo code. */
async function applyCampaignToken(): Promise<void> {
  const token = route.query.c
  if (typeof token !== 'string') return
  try {
    const preview = await api.get<PromoPreview>('/promo/resolve', { token })
    setPromo(preview)
  } catch (error) {
    promoProblem.value = errorText(error)
  }
}

function setPromo(preview: PromoPreview): void {
  promoCode.value = preview.code
  promoInput.value = preview.code
  promoProblem.value = ''
  const amount = preview.discount_type === 'percent' ? `${preview.discount_value}%` : money(preview.discount_value)
  promoNote.value = t('event.promoApplied', { code: preview.code, amount })
}

async function applyTypedPromo(): Promise<void> {
  promoProblem.value = ''
  promoNote.value = ''
  if (!promoInput.value.trim()) {
    promoCode.value = null
    return
  }
  try {
    setPromo(await api.post<PromoPreview>('/promo/check', { event_id: event.value!.id, code: promoInput.value.trim() }))
  } catch (error) {
    promoCode.value = null
    promoProblem.value = errorText(error)
  }
}

/** Ask the server for the price every time the selection or the promo code changes. */
async function refreshQuote(): Promise<void> {
  quoteProblem.value = ''
  if (!event.value || ticketCount.value === 0) {
    quote.value = null
    return
  }
  try {
    quote.value = await api.post<Quote>('/orders/quote', selection())
  } catch (error) {
    quote.value = null
    quoteProblem.value = errorText(error)
  }
}
watch([quantities, selectedSeats, promoCode], refreshQuote, { deep: true })

function step(typeId: string, delta: number, limit: number): void {
  quantities[typeId] = Math.min(limit, Math.max(0, (quantities[typeId] ?? 0) + delta))
}

function openDetails(): void {
  if (!auth.isSignedIn) {
    void router.push({ name: 'login', query: { next: route.fullPath } })
    return
  }
  buyer.name = buyer.name || auth.user!.name
  buyer.email = buyer.email || auth.user!.email
  attendeeNames.value = Array.from({ length: ticketCount.value }, (_, i) => attendeeNames.value[i] ?? buyer.name)
  checkoutProblem.value = ''
  detailsOpen.value = true
}

async function startCheckout(): Promise<void> {
  busy.value = true
  checkoutProblem.value = ''
  try {
    const order = await api.post<Order>('/orders', {
      ...selection(), buyer_name: buyer.name, buyer_email: buyer.email, buyer_phone: buyer.phone || null,
      attendees: attendeeNames.value.map((name) => ({ name: name.trim() || buyer.name })),
    })
    detailsOpen.value = false
    if (order.status === 'completed') {
      toasts.ok(t('checkout.registered'))
      await router.push({ name: 'order', params: { id: order.id } })
    } else {
      await router.push({ name: 'checkout', params: { id: order.id } })
    }
  } catch (error) {
    checkoutProblem.value = errorText(error)
    if (isSeated.value) {
      selectedSeats.value = []
      void load() // someone may have taken a seat: show the fresh map
    }
  } finally {
    busy.value = false
  }
}

async function sendReport(): Promise<void> {
  try {
    await api.post(`/events/${event.value!.id}/report`, { reason: reportReason.value })
    reportOpen.value = false
    reportReason.value = ''
    toasts.ok(t('event.reportSent'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(async () => {
  await load()
  await applyCampaignToken()
})
</script>

<template>
  <div v-if="loadProblem" class="page"><p class="notice notice-bad" role="alert">{{ loadProblem }}</p></div>
  <p v-else-if="!event" class="page text-ink-soft">{{ $t('common.loading') }}</p>

  <template v-else>
    <!-- Cover: a band in the category colour, like a printed ticket roll -->
    <section class="border-b border-line" :style="{ background: categoryColour(event.category) }">
      <div class="mx-auto grid max-w-6xl gap-6 px-4 py-8 sm:px-6 sm:py-12 md:grid-cols-[1fr_auto] md:items-end">
        <div>
          <p class="mb-3 flex flex-wrap gap-2">
            <span class="badge bg-white/80">{{ event.category }}</span>
            <span v-if="event.visibility !== 'public'" class="badge bg-white/80">{{ $t(`visibility.${event.visibility}`) }}</span>
          </p>
          <h1 class="max-w-[22ch]">{{ event.title }}</h1>
          <p class="mt-4 text-lg font-semibold">{{ dateTime(event.start_at, event.timezone) }} – {{ timeOnly(event.end_at, event.timezone) }}</p>
          <p class="text-lg">{{ event.venue.name }}, {{ event.venue.address }}, {{ event.venue.city }}</p>
        </div>
        <img v-if="event.images[0]" :src="event.images[0]" :alt="$t('event.coverAlt', { title: event.title })" class="max-h-56 w-full rounded-xl object-cover md:w-80" />
      </div>
    </section>

    <div class="page grid gap-8 lg:grid-cols-[1fr_22rem]">
      <div class="min-w-0 space-y-6">
        <p v-if="event.can_manage" class="notice notice-warn flex flex-wrap items-center justify-between gap-3">
          <span>{{ event.status === 'published' ? $t('event.youManage') : $t('event.previewNote') }}</span>
          <RouterLink class="btn btn-secondary btn-sm" :to="{ name: 'manage-overview', params: { id: event.id } }">{{ $t('event.manage') }}</RouterLink>
        </p>
        <p v-if="event.status === 'cancelled'" class="notice notice-bad" role="status">{{ $t('event.cancelledNote') }}</p>
        <p v-else-if="event.is_suspended" class="notice notice-bad" role="status">{{ $t('event.suspendedNote') }}</p>

        <section v-if="event.description">
          <h2 class="mb-3">{{ $t('event.about') }}</h2>
          <p class="max-w-[70ch] leading-relaxed whitespace-pre-line">{{ event.description }}</p>
        </section>

        <section v-if="isSeated && seatMap" class="card">
          <h2 class="mb-1">{{ $t('event.chooseSeats') }}</h2>
          <p class="mb-4 text-sm text-ink-soft">{{ $t('event.chooseSeatsHint') }}</p>
          <SeatMapView v-model="selectedSeats" :map="seatMap" :readonly="!event.is_on_sale" @limit="toasts.ok($t('seat.limit'))" />
        </section>

        <section class="card">
          <h2 class="mb-3">{{ $t('event.goodToKnow') }}</h2>
          <dl class="grid gap-4 sm:grid-cols-2">
            <div><dt class="text-sm text-ink-soft">{{ $t('event.organizer') }}</dt><dd class="font-semibold">{{ event.organizer_name }}</dd></div>
            <div><dt class="text-sm text-ink-soft">{{ $t('event.timezone') }}</dt><dd class="font-semibold">{{ event.timezone }}</dd></div>
            <div class="sm:col-span-2">
              <dt class="text-sm text-ink-soft">{{ $t('event.refunds') }}</dt>
              <dd class="font-semibold">{{ $t(`refundPolicy.${event.refund_policy}`) }}</dd>
              <dd v-if="event.refund_policy_text" class="text-sm">{{ event.refund_policy_text }}</dd>
            </div>
          </dl>
          <div class="mt-5"><CalendarButtons :event-ref="event.id" :access-key="accessKey" /></div>
          <div v-if="auth.isSignedIn" class="mt-5 flex flex-wrap gap-2">
            <SupportRequestButton :event-id="event.id" />
            <button type="button" class="btn btn-ghost btn-sm" @click="reportOpen = true">{{ $t('event.report') }}</button>
          </div>
        </section>
      </div>

      <!-- Ticket panel -->
      <aside class="lg:sticky lg:top-4 lg:self-start">
        <div class="card">
          <h2 class="mb-3">{{ $t('event.tickets') }}</h2>
          <p v-if="!event.is_on_sale" class="notice notice-warn mb-3">{{ $t('event.salesClosed') }}</p>

          <ul v-if="!isSeated" class="space-y-4">
            <li v-for="type in event.ticket_types" :key="type.id" class="border-b border-line pb-4 last:border-0 last:pb-0">
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="font-semibold">{{ type.name }}</p>
                  <p class="font-display text-xl font-semibold">{{ type.price ? money(type.price) : $t('event.free') }}</p>
                  <p v-if="type.description" class="text-sm text-ink-soft">{{ type.description }}</p>
                </div>
                <div v-if="type.on_sale" class="flex shrink-0 items-center gap-1">
                  <button type="button" class="btn btn-secondary btn-sm w-9 px-0" :aria-label="$t('event.fewer', { name: type.name })" :disabled="!quantities[type.id]" @click="step(type.id, -1, type.order_limit)">−</button>
                  <output class="w-7 text-center font-semibold tabular-nums" :aria-label="$t('event.quantityOf', { name: type.name })">{{ quantities[type.id] ?? 0 }}</output>
                  <button type="button" class="btn btn-secondary btn-sm w-9 px-0" :aria-label="$t('event.more', { name: type.name })" :disabled="(quantities[type.id] ?? 0) >= Math.min(type.order_limit, type.available)" @click="step(type.id, 1, Math.min(type.order_limit, type.available))">+</button>
                </div>
              </div>
              <p v-if="!type.on_sale" class="mt-1 text-sm font-semibold text-warn">{{ $t(`unavailable.${type.unavailable_reason}`) }}</p>
              <p v-else-if="type.available <= 10" class="mt-1 text-sm text-warn">{{ $t('event.left', type.available) }}</p>
            </li>
            <li v-if="!event.ticket_types.length" class="text-ink-soft">{{ $t('event.noTickets') }}</li>
          </ul>
          <p v-else-if="!selectedSeats.length" class="text-ink-soft">{{ $t('event.noSeatsYet') }}</p>

          <form class="mt-4 flex items-end gap-2 border-t border-dashed border-line pt-4" @submit.prevent="applyTypedPromo">
            <div class="min-w-0 flex-1">
              <label class="label" for="promo">{{ $t('event.promoCode') }}</label>
              <input id="promo" v-model="promoInput" class="input uppercase" autocomplete="off" maxlength="40" />
            </div>
            <button type="submit" class="btn btn-secondary">{{ $t('event.apply') }}</button>
          </form>
          <p v-if="promoNote" class="mt-2 text-sm font-semibold text-ok" role="status">✓ {{ promoNote }}</p>
          <p v-if="promoProblem" class="mt-2 text-sm font-semibold text-bad" role="alert">{{ promoProblem }}</p>

          <div v-if="quote" class="mt-4 space-y-1 border-t border-dashed border-line pt-4 text-sm" aria-live="polite">
            <div v-for="line in quote.lines" :key="line.event_seat_id ?? line.ticket_category_id" class="flex justify-between gap-3">
              <span>{{ lineLabel(line) }}</span>
              <span class="tabular-nums">{{ money(line.unit_price * line.quantity) }}</span>
            </div>
            <div v-if="quote.discount_total" class="flex justify-between gap-3 font-semibold text-ok">
              <span>{{ $t('event.discount', { code: quote.promo?.code }) }}</span><span class="tabular-nums">−{{ money(quote.discount_total) }}</span>
            </div>
            <div class="flex justify-between gap-3 pt-2 text-base font-semibold">
              <span>{{ $t('event.total') }}</span><span class="font-display text-2xl tabular-nums">{{ money(quote.total) }}</span>
            </div>
          </div>
          <p v-if="quoteProblem" class="notice notice-bad mt-3" role="alert">{{ quoteProblem }}</p>

          <button type="button" class="btn btn-sun mt-4 w-full" :disabled="!quote || !event.is_on_sale" @click="openDetails">
            {{ quote && quote.total === 0 ? $t('event.register') : $t('event.continue') }}
          </button>
          <p v-if="!auth.isSignedIn" class="hint">{{ $t('event.signInHint') }}</p>
        </div>
      </aside>
    </div>

    <ModalDialog :open="detailsOpen" :title="$t('checkout.yourDetails')" @close="detailsOpen = false">
      <form class="space-y-4" @submit.prevent="startCheckout">
        <div class="grid gap-3 sm:grid-cols-2">
          <div><label class="label" for="buyer-name">{{ $t('checkout.buyerName') }}</label><input id="buyer-name" v-model="buyer.name" class="input" required autocomplete="name" /></div>
          <div><label class="label" for="buyer-email">{{ $t('checkout.buyerEmail') }}</label><input id="buyer-email" v-model="buyer.email" type="email" class="input" required autocomplete="email" /></div>
          <div class="sm:col-span-2"><label class="label" for="buyer-phone">{{ $t('checkout.buyerPhone') }}</label><input id="buyer-phone" v-model="buyer.phone" type="tel" class="input" autocomplete="tel" /></div>
        </div>
        <fieldset v-if="attendeeNames.length > 1">
          <legend class="label">{{ $t('checkout.attendeeNames') }}</legend>
          <div class="space-y-2">
            <input v-for="(_, index) in attendeeNames" :key="index" v-model="attendeeNames[index]" class="input" :aria-label="$t('checkout.attendeeN', { n: index + 1 })" :placeholder="$t('checkout.attendeeN', { n: index + 1 })" />
          </div>
        </fieldset>
        <p class="text-sm text-ink-soft">{{ $t('checkout.holdHint') }}</p>
        <p v-if="checkoutProblem" class="notice notice-bad" role="alert">{{ checkoutProblem }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="detailsOpen = false">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-sun" :disabled="busy">{{ quote && quote.total === 0 ? $t('event.register') : $t('checkout.toPayment') }}</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog :open="reportOpen" :title="$t('event.report')" @close="reportOpen = false">
      <form class="space-y-4" @submit.prevent="sendReport">
        <div>
          <label class="label" for="report-reason">{{ $t('event.reportReason') }}</label>
          <textarea id="report-reason" v-model="reportReason" class="input" required minlength="5" maxlength="2000" />
        </div>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="reportOpen = false">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-primary">{{ $t('event.sendReport') }}</button>
        </div>
      </form>
    </ModalDialog>
  </template>
</template>
