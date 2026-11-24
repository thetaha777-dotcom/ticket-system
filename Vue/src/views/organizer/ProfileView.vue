<script setup lang="ts">
/** Organizer profile: contact details plus the simulated identity check and payout account. */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { api, ApiError } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { OrganizerProfile } from '@/types'

const auth = useAuthStore()
const toasts = useToastStore()
const { t } = useI18n()

const profile = ref<OrganizerProfile | null>(null)
const loaded = ref(false)
const form = reactive({ display_name: '', contact_email: auth.user?.email ?? '', contact_phone: '', description: '', website: '' })
const payout = reactive({ bank_name: '', account_holder: '', account_number: '' })

function fill(data: OrganizerProfile): void {
  profile.value = data
  Object.assign(form, {
    display_name: data.display_name, contact_email: data.contact_email, contact_phone: data.contact_phone ?? '',
    description: data.description ?? '', website: data.website ?? '',
  })
  if (data.payout_account) Object.assign(payout, { bank_name: data.payout_account.bank_name, account_holder: data.payout_account.account_holder })
}

async function save(): Promise<void> {
  try {
    fill(await api.put<OrganizerProfile>('/users/me/organizer-profile', {
      ...form, contact_phone: form.contact_phone || null, description: form.description || null, website: form.website || null,
    }))
    await auth.refresh() // an attendee has just become an organizer
    toasts.ok(t('org.profileSaved'))
  } catch (error) {
    toasts.error(error)
  }
}

async function verifyIdentity(): Promise<void> {
  try {
    fill(await api.post<OrganizerProfile>('/users/me/organizer-profile/verify-identity'))
    toasts.ok(t('org.identityDone'))
  } catch (error) {
    toasts.error(error)
  }
}

async function savePayout(): Promise<void> {
  try {
    fill(await api.put<OrganizerProfile>('/users/me/payout-account', payout))
    payout.account_number = ''
    toasts.ok(t('org.payoutDone'))
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(async () => {
  try {
    fill(await api.get<OrganizerProfile>('/users/me/organizer-profile'))
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 404)) toasts.error(error) // 404 = no profile yet
  }
  loaded.value = true
})
</script>

<template>
  <div class="page">
    <div class="mb-2 flex flex-wrap items-center justify-between gap-4">
      <h1>{{ $t('org.profile') }}</h1>
      <RouterLink class="btn btn-secondary" :to="{ name: 'organizer-emotional-support' }">{{ $t('org.emotionalSupport') }}</RouterLink>
    </div>
    <p v-if="loaded && !profile" class="mb-6 max-w-[65ch] text-ink-soft">{{ $t('org.becomeLead') }}</p>

    <div class="mt-6 grid gap-6 lg:grid-cols-2">
      <form class="card space-y-4" @submit.prevent="save">
        <h2 class="card-title">{{ $t('org.contact') }}</h2>
        <div><label class="label" for="org-name">{{ $t('org.displayName') }}</label><input id="org-name" v-model="form.display_name" class="input" required maxlength="255" /></div>
        <div><label class="label" for="org-email">{{ $t('org.contactEmail') }}</label><input id="org-email" v-model="form.contact_email" type="email" class="input" required /></div>
        <div><label class="label" for="org-phone">{{ $t('org.contactPhone') }}</label><input id="org-phone" v-model="form.contact_phone" type="tel" class="input" /></div>
        <div><label class="label" for="org-site">{{ $t('org.website') }}</label><input id="org-site" v-model="form.website" class="input" placeholder="https://" /></div>
        <div><label class="label" for="org-about">{{ $t('org.about') }}</label><textarea id="org-about" v-model="form.description" class="input" rows="3" /></div>
        <button type="submit" class="btn btn-primary">{{ profile ? $t('common.save') : $t('org.createProfile') }}</button>
      </form>

      <div v-if="profile" class="space-y-6">
        <div class="card">
          <h2 class="card-title flex items-center gap-2">{{ $t('org.identity') }} <StatusBadge :status="profile.verification_status" /></h2>
          <p class="mb-3 text-sm text-ink-soft">{{ $t('org.identityText') }}</p>
          <button v-if="profile.verification_status !== 'verified'" type="button" class="btn btn-secondary" @click="verifyIdentity">{{ $t('org.identityButton') }}</button>
        </div>

        <form class="card space-y-4" @submit.prevent="savePayout">
          <h2 class="card-title flex items-center gap-2">
            {{ $t('org.payout') }}
            <StatusBadge v-if="profile.payout_account" status="verified" />
          </h2>
          <p class="text-sm text-ink-soft">{{ $t('org.payoutText') }}</p>
          <p v-if="profile.payout_account" class="notice">{{ $t('org.payoutCurrent', { bank: profile.payout_account.bank_name, last4: profile.payout_account.account_last4 }) }}</p>
          <div><label class="label" for="pay-bank">{{ $t('org.bank') }}</label><input id="pay-bank" v-model="payout.bank_name" class="input" required /></div>
          <div><label class="label" for="pay-holder">{{ $t('org.holder') }}</label><input id="pay-holder" v-model="payout.account_holder" class="input" required /></div>
          <div>
            <label class="label" for="pay-number">{{ $t('org.accountNumber') }}</label>
            <input id="pay-number" v-model="payout.account_number" class="input" required minlength="4" maxlength="34" autocomplete="off" aria-describedby="pay-number-hint" />
            <p id="pay-number-hint" class="hint">{{ $t('org.accountHint') }}</p>
          </div>
          <button type="submit" class="btn btn-secondary">{{ profile.payout_account ? $t('org.payoutReplace') : $t('org.payoutConnect') }}</button>
        </form>
      </div>
    </div>
  </div>
</template>
