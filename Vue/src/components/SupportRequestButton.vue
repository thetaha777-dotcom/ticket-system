<script setup lang="ts">
/**
 * "Ask for help" button. Put it on an event, order or ticket page and pass the id you have:
 * the server links the case to the right event / order / ticket by itself.
 */
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import ModalDialog from '@/components/ModalDialog.vue'
import { api } from '@/lib/api'
import { errorText } from '@/lib/format'
import type { SupportCase } from '@/types'

const props = withDefaults(defineProps<{ eventId?: string; orderId?: string; ticketId?: string; kind?: 'attendee' | 'organizer'; label?: string }>(), { kind: 'attendee' })
const router = useRouter()

const ATTENDEE_CATEGORIES = ['ticket_delivery', 'payment', 'refund', 'seating', 'event_information', 'check_in', 'technical']
const ORGANIZER_CATEGORIES = ['account', 'activation', 'payment', 'technical']
const categories = props.kind === 'organizer' ? ORGANIZER_CATEGORIES : ATTENDEE_CATEGORIES

const open = ref(false)
const busy = ref(false)
const problem = ref('')
const form = reactive({ category: categories[0], subject: '', message: '' })

async function submit(): Promise<void> {
  busy.value = true
  problem.value = ''
  try {
    const created = await api.post<SupportCase>('/support/cases', {
      kind: props.kind, ...form, event_id: props.eventId, order_id: props.orderId, ticket_id: props.ticketId,
    })
    open.value = false
    await router.push({ name: 'support-case', params: { id: created.id } })
  } catch (error) {
    problem.value = errorText(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <button type="button" class="btn btn-secondary btn-sm" @click="open = true">{{ label ?? $t('support.ask') }}</button>
  <ModalDialog :open="open" :title="kind === 'organizer' ? $t('support.askPlatform') : $t('support.askOrganizer')" @close="open = false">
    <form class="space-y-4" @submit.prevent="submit">
      <div>
        <label class="label" for="case-category">{{ $t('support.category') }}</label>
        <select id="case-category" v-model="form.category" class="input">
          <option v-for="item in categories" :key="item" :value="item">{{ $t(`supportCategory.${item}`) }}</option>
        </select>
      </div>
      <div>
        <label class="label" for="case-subject">{{ $t('support.subject') }}</label>
        <input id="case-subject" v-model="form.subject" class="input" required minlength="3" maxlength="255" />
      </div>
      <div>
        <label class="label" for="case-message">{{ $t('support.message') }}</label>
        <textarea id="case-message" v-model="form.message" class="input" required maxlength="5000" rows="5" />
        <p class="hint">{{ $t('support.contextHint') }}</p>
      </div>
      <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
      <div class="flex justify-end gap-2">
        <button type="button" class="btn btn-secondary" @click="open = false">{{ $t('common.cancel') }}</button>
        <button type="submit" class="btn btn-primary" :disabled="busy">{{ $t('support.send') }}</button>
      </div>
    </form>
  </ModalDialog>
</template>
