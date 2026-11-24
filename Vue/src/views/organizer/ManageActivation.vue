<script setup lang="ts">
/** Paid Sales Activation checklist. Every step is a clearly labelled simulation in this academic version. */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { errorText, money } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { Activation } from '@/types'

const { event, reload } = useManagedEvent()
const toasts = useToastStore()
const { t } = useI18n()

const activation = ref<Activation | null>(null)
const problem = ref('')
const accepted = ref(false)
const base = (): string => `/organizer/events/${event.value.id}/activation`
const done = (key: string): boolean => activation.value?.steps.find((step) => step.key === key)?.done ?? false

async function load(): Promise<void> {
  try {
    activation.value = await api.get<Activation>(base())
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function run(call: () => Promise<Activation | unknown>, message: string): Promise<void> {
  problem.value = ''
  try {
    await call()
    await Promise.all([load(), reload()])
    toasts.ok(message)
  } catch (error) {
    problem.value = errorText(error)
    await load()
  }
}

const verifyIdentity = (): Promise<void> => run(() => api.post('/users/me/organizer-profile/verify-identity'), t('org.identityDone'))
const payFee = (outcome: 'success' | 'failure'): Promise<void> => run(() => api.post(`${base()}/pay-fee`, { outcome }), t('activation.feePaid'))
const acceptTerms = (): Promise<void> => run(() => api.post(`${base()}/accept-terms`), t('activation.termsDone'))

onMounted(load)
</script>

<template>
  <div class="max-w-3xl">
    <p v-if="!activation && !problem" class="text-ink-soft">{{ $t('common.loading') }}</p>
    <template v-if="activation">
      <div class="mb-5 flex flex-wrap items-center gap-3">
        <h2>{{ $t('activation.title') }}</h2>
        <StatusBadge :status="activation.status" />
      </div>
      <p class="mb-4 max-w-[65ch] text-ink-soft">{{ $t('activation.lead') }}</p>
      <p class="notice notice-warn mb-5">{{ $t('activation.demo') }}</p>
      <p v-if="activation.status === 'suspended'" class="notice notice-bad mb-5" role="status">{{ $t('activation.suspended', { reason: activation.suspended_reason }) }}</p>
      <p v-else-if="activation.is_active" class="notice notice-ok mb-5" role="status">{{ $t('activation.active') }}</p>
      <p v-if="problem" class="notice notice-bad mb-5" role="alert">{{ problem }}</p>

      <!-- The five steps really are a sequence, so they are numbered -->
      <ol class="space-y-3">
        <li v-for="(key, index) in ['paid_ticket_type', 'identity_verified', 'payout_account', 'fee_paid', 'terms_accepted']" :key="key" class="card flex gap-4">
          <span
            class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full font-display text-lg font-semibold"
            :class="done(key) ? 'bg-ok text-white' : 'bg-mist text-ink'" aria-hidden="true"
          >{{ done(key) ? '✓' : index + 1 }}</span>
          <div class="min-w-0 flex-1">
            <h3 class="font-sans text-base font-semibold">
              {{ $t(`activation.step.${key}.title`) }}
              <span class="sr-only">, {{ done(key) ? $t('activation.done') : $t('activation.notDone') }}</span>
            </h3>
            <p class="mb-2 text-sm text-ink-soft">{{ $t(`activation.step.${key}.text`, { amount: money(activation.fee_amount) }) }}</p>
            <template v-if="!done(key)">
              <RouterLink v-if="key === 'paid_ticket_type'" class="btn btn-secondary btn-sm" :to="{ name: 'manage-tickets', params: { id: event.id } }">{{ $t('tickets.add') }}</RouterLink>
              <button v-else-if="key === 'identity_verified'" type="button" class="btn btn-secondary btn-sm" @click="verifyIdentity">{{ $t('org.identityButton') }}</button>
              <RouterLink v-else-if="key === 'payout_account'" class="btn btn-secondary btn-sm" :to="{ name: 'organizer-profile' }">{{ $t('org.payoutConnect') }}</RouterLink>
              <div v-else-if="key === 'fee_paid'" class="flex flex-wrap gap-2">
                <button type="button" class="btn btn-sun btn-sm" @click="payFee('success')">{{ $t('activation.payFee', { amount: money(activation.fee_amount) }) }}</button>
                <button type="button" class="btn btn-secondary btn-sm" @click="payFee('failure')">{{ $t('checkout.payFailure') }}</button>
              </div>
              <div v-else class="space-y-2">
                <label class="flex cursor-pointer items-start gap-2 text-sm"><input v-model="accepted" type="checkbox" class="mt-0.5 h-4 w-4" /> {{ $t('activation.termsLabel') }}</label>
                <button type="button" class="btn btn-secondary btn-sm" :disabled="!accepted" @click="acceptTerms">{{ $t('activation.acceptTerms') }}</button>
              </div>
            </template>
          </div>
        </li>
      </ol>
    </template>
  </div>
</template>
