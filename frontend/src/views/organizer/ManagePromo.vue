<script setup lang="ts">
/** Promo campaigns: create a code, get its Campaign QR code, switch it off, see exact results. */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ModalDialog from '@/components/ModalDialog.vue'
import { api } from '@/lib/api'
import { dateOnly, errorText, fromLocalInput, money } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { Campaign } from '@/types'

const { event } = useManagedEvent()
const toasts = useToastStore()
const { t } = useI18n()

const campaigns = ref<Campaign[] | null>(null)
const problem = ref('')
const createOpen = ref(false)
const formProblem = ref('')
const form = reactive({
  name: '', discount_type: 'percent' as 'percent' | 'fixed', discount_value: 10, startsAt: '', endsAt: '',
  max_redemptions: null as number | null, code: '', ticket_category_ids: [] as string[],
})
const qr = ref<{ campaign: Campaign; url: string } | null>(null)
const base = (): string => `/organizer/events/${event.value.id}/campaigns`

async function load(): Promise<void> {
  try {
    campaigns.value = await api.get<Campaign[]>(base())
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function create(): Promise<void> {
  formProblem.value = ''
  try {
    await api.post(base(), {
      name: form.name, discount_type: form.discount_type, discount_value: form.discount_value,
      starts_at: fromLocalInput(form.startsAt, event.value.timezone), ends_at: fromLocalInput(form.endsAt, event.value.timezone),
      max_redemptions: form.max_redemptions || null, code: form.code.trim() || null, ticket_category_ids: form.ticket_category_ids,
    })
    createOpen.value = false
    Object.assign(form, { name: '', discount_value: 10, startsAt: '', endsAt: '', max_redemptions: null, code: '', ticket_category_ids: [] })
    await load()
    toasts.ok(t('promo.created'))
  } catch (error) {
    formProblem.value = errorText(error)
  }
}

async function setActive(campaign: Campaign, is_active: boolean): Promise<void> {
  try {
    await api.patch(`${base()}/${campaign.id}`, { is_active })
    await load()
  } catch (error) {
    toasts.error(error)
  }
}

async function showQr(campaign: Campaign): Promise<void> {
  try {
    qr.value = { campaign, url: await api.blobUrl(`${base()}/${campaign.id}/qr.png`) }
  } catch (error) {
    toasts.error(error)
  }
}

function closeQr(): void {
  if (qr.value) URL.revokeObjectURL(qr.value.url)
  qr.value = null
}

async function copy(text: string): Promise<void> {
  try {
    await navigator.clipboard.writeText(text)
    toasts.ok(t('common.copied'))
  } catch {
    /* the text is visible and can be selected by hand */
  }
}

const describe = (campaign: Campaign): string =>
  campaign.discount_type === 'percent' ? `${campaign.discount_value}%` : t('promo.perTicket', { amount: money(campaign.discount_value) })

onMounted(load)
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <p class="max-w-[65ch] text-sm text-ink-soft">{{ $t('promo.lead') }}</p>
      <button v-if="event.status !== 'cancelled'" type="button" class="btn btn-primary" @click="createOpen = true">{{ $t('promo.create') }}</button>
    </div>

    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!campaigns" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <p v-else-if="!campaigns.length" class="card text-ink-soft">{{ $t('promo.empty') }}</p>
    <ul v-else class="space-y-4">
      <li v-for="campaign in campaigns" :key="campaign.id" class="card">
        <div class="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 class="text-2xl">{{ campaign.name }}</h2>
            <p class="mt-1 flex flex-wrap items-center gap-2">
              <button type="button" class="badge badge-sky cursor-pointer text-sm" :title="$t('common.copy')" @click="copy(campaign.code)">{{ campaign.code }}</button>
              <strong>{{ describe(campaign) }}</strong>
              <span v-if="!campaign.is_active" class="badge badge-bad">{{ $t('promo.disabled') }}</span>
            </p>
            <p class="mt-1 text-sm text-ink-soft">
              {{ campaign.ends_at ? $t('promo.until', { date: dateOnly(campaign.ends_at, event.timezone) }) : $t('promo.noEnd') }},
              {{ campaign.ticket_category_ids.length ? $t('promo.someTypes', campaign.ticket_category_ids.length) : $t('promo.allTypes') }}
            </p>
          </div>
          <div class="flex flex-wrap gap-2">
            <button type="button" class="btn btn-secondary btn-sm" @click="showQr(campaign)">{{ $t('promo.qr') }}</button>
            <button type="button" class="btn btn-secondary btn-sm" @click="copy(campaign.link)">{{ $t('promo.copyLink') }}</button>
            <button v-if="campaign.is_active" type="button" class="btn btn-danger btn-sm" @click="setActive(campaign, false)">{{ $t('promo.disable') }}</button>
            <button v-else type="button" class="btn btn-secondary btn-sm" @click="setActive(campaign, true)">{{ $t('promo.enable') }}</button>
          </div>
        </div>
        <dl class="mt-4 grid grid-cols-2 gap-x-6 gap-y-3 border-t border-line pt-4 text-sm sm:grid-cols-4 lg:grid-cols-7">
          <div><dt class="text-ink-soft">{{ $t('promo.redemptions') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ campaign.stats.redemptions }}<span v-if="campaign.max_redemptions" class="text-ink-soft"> / {{ campaign.max_redemptions }}</span></dd></div>
          <div><dt class="text-ink-soft">{{ $t('promo.orders') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ campaign.stats.orders }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('promo.tickets') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ campaign.stats.tickets_sold }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('analytics.gross') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ money(campaign.stats.gross_revenue) }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('analytics.discounts') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ money(campaign.stats.discount_amount) }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('analytics.net') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ money(campaign.stats.net_revenue) }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('promo.visits') }}</dt><dd class="text-lg font-semibold tabular-nums">{{ campaign.stats.link_visits }}</dd></div>
        </dl>
      </li>
    </ul>

    <ModalDialog :open="createOpen" :title="$t('promo.create')" @close="createOpen = false">
      <form class="space-y-4" @submit.prevent="create">
        <div><label class="label" for="pc-name">{{ $t('promo.name') }}</label><input id="pc-name" v-model="form.name" class="input" required maxlength="255" /></div>
        <div class="grid gap-3 sm:grid-cols-2">
          <div>
            <label class="label" for="pc-type">{{ $t('promo.discountType') }}</label>
            <select id="pc-type" v-model="form.discount_type" class="input"><option value="percent">{{ $t('promo.percent') }}</option><option value="fixed">{{ $t('promo.fixed') }}</option></select>
          </div>
          <div>
            <label class="label" for="pc-value">{{ form.discount_type === 'percent' ? $t('promo.valuePercent') : $t('promo.valueKzt') }}</label>
            <input id="pc-value" v-model.number="form.discount_value" type="number" min="1" :max="form.discount_type === 'percent' ? 100 : undefined" class="input" required />
          </div>
          <div><label class="label" for="pc-start">{{ $t('promo.starts') }}</label><input id="pc-start" v-model="form.startsAt" type="datetime-local" class="input" /></div>
          <div><label class="label" for="pc-end">{{ $t('promo.ends') }}</label><input id="pc-end" v-model="form.endsAt" type="datetime-local" class="input" /></div>
          <div><label class="label" for="pc-max">{{ $t('promo.max') }}</label><input id="pc-max" v-model.number="form.max_redemptions" type="number" min="1" class="input" /><p class="hint">{{ $t('promo.maxHint') }}</p></div>
          <div><label class="label" for="pc-code">{{ $t('promo.code') }}</label><input id="pc-code" v-model="form.code" class="input uppercase" pattern="[A-Za-z0-9_\-]{3,40}" /><p class="hint">{{ $t('promo.codeHint') }}</p></div>
        </div>
        <fieldset v-if="event.ticket_types.length > 1">
          <legend class="label">{{ $t('promo.appliesTo') }}</legend>
          <label v-for="type in event.ticket_types" :key="type.id" class="mr-4 inline-flex cursor-pointer items-center gap-2">
            <input v-model="form.ticket_category_ids" type="checkbox" :value="type.id" class="h-4 w-4" /> {{ type.name }}
          </label>
          <p class="hint">{{ $t('promo.appliesHint') }}</p>
        </fieldset>
        <p v-if="formProblem" class="notice notice-bad" role="alert">{{ formProblem }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="createOpen = false">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-primary">{{ $t('promo.create') }}</button>
        </div>
      </form>
    </ModalDialog>

    <ModalDialog :open="qr !== null" :title="$t('promo.qrTitle')" @close="closeQr">
      <div v-if="qr" class="space-y-4 text-center">
        <img :src="qr.url" :alt="$t('promo.qrAlt', { code: qr.campaign.code })" class="mx-auto w-64 max-w-full" />
        <p class="text-sm text-ink-soft">{{ $t('promo.qrText') }}</p>
        <p class="text-sm break-all">{{ qr.campaign.link }}</p>
        <a class="btn btn-primary" :href="qr.url" :download="`promo-${qr.campaign.code}.png`">{{ $t('promo.download') }}</a>
      </div>
    </ModalDialog>
  </div>
</template>
