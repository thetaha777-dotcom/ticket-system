<script setup lang="ts">
/**
 * One support case as a chat-like thread. It is asynchronous: the page re-reads the case
 * every 8 seconds while it is visible (simple polling, no WebSocket needed).
 */
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime, errorText } from '@/lib/format'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { CaseStatus, SupportCase } from '@/types'

const props = defineProps<{ id: string }>()
const auth = useAuthStore()
const toasts = useToastStore()
const { t } = useI18n()

const STATUSES: CaseStatus[] = ['open', 'in_progress', 'waiting_for_customer', 'resolved']
const item = ref<SupportCase | null>(null)
const problem = ref('')
const reply = ref('')
const busy = ref(false)
const thread = ref<HTMLElement | null>(null)
let timer: number | undefined

async function load(scroll = false): Promise<void> {
  try {
    const fresh = await api.get<SupportCase>(`/support/cases/${props.id}`)
    const grew = (fresh.messages?.length ?? 0) > (item.value?.messages?.length ?? 0)
    item.value = fresh
    if (scroll || grew) {
      await nextTick()
      thread.value?.lastElementChild?.scrollIntoView({ block: 'nearest' })
    }
  } catch (error) {
    if (!item.value) problem.value = errorText(error)
  }
}

async function send(): Promise<void> {
  if (!reply.value.trim()) return
  busy.value = true
  try {
    item.value = await api.post<SupportCase>(`/support/cases/${props.id}/messages`, { body: reply.value })
    reply.value = ''
    await nextTick()
    thread.value?.lastElementChild?.scrollIntoView({ block: 'nearest' })
  } catch (error) {
    toasts.error(error)
  } finally {
    busy.value = false
  }
}

async function update(changes: Record<string, unknown>, done: string): Promise<void> {
  try {
    item.value = await api.patch<SupportCase>(`/support/cases/${props.id}`, changes)
    toasts.ok(done)
  } catch (error) {
    toasts.error(error)
  }
}

onMounted(() => {
  void load(true)
  timer = window.setInterval(() => {
    if (document.visibilityState === 'visible') void load()
  }, 8000)
})
onBeforeUnmount(() => window.clearInterval(timer))
</script>

<template>
  <div class="page max-w-4xl">
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-else-if="!item" class="text-ink-soft">{{ $t('common.loading') }}</p>

    <template v-else>
      <RouterLink :to="{ name: 'support' }" class="text-sm font-semibold">{{ $t('support.back') }}</RouterLink>
      <div class="mt-2 mb-5">
        <p class="mb-1 flex flex-wrap items-center gap-2 text-ink-soft">
          {{ item.number }} <StatusBadge :status="item.status" />
          <span class="badge">{{ $t(`supportCategory.${item.category}`) }}</span>
          <span v-if="item.is_escalated" class="badge badge-bad">{{ $t('support.escalated') }}</span>
        </p>
        <h1 class="text-3xl sm:text-4xl">{{ item.subject }}</h1>
      </div>

      <!-- Context captured when the request was opened -->
      <dl class="card mb-5 grid gap-3 text-sm sm:grid-cols-3">
        <div><dt class="text-ink-soft">{{ $t('support.from') }}</dt><dd class="font-semibold">{{ item.requester.name }}</dd></div>
        <div v-if="item.context.event_title">
          <dt class="text-ink-soft">{{ $t('order.event') }}</dt>
          <dd><RouterLink :to="{ name: 'event', params: { slug: item.context.event_slug } }">{{ item.context.event_title }}</RouterLink></dd>
        </div>
        <div v-if="item.context.order_number">
          <dt class="text-ink-soft">{{ $t('order.order') }}</dt>
          <dd class="font-semibold">{{ item.context.order_number }}<template v-if="item.context.ticket_code">, {{ $t('ticket.code', { code: item.context.ticket_code }) }}</template></dd>
        </div>
        <div v-if="item.assigned_to"><dt class="text-ink-soft">{{ $t('support.assignee') }}</dt><dd class="font-semibold">{{ item.assigned_to.name }}</dd></div>
      </dl>

      <div v-if="item.can_manage" class="card mb-5 flex flex-wrap items-end gap-3">
        <div>
          <label class="label" for="case-status">{{ $t('common.status') }}</label>
          <select id="case-status" class="input" :value="item.status" @change="update({ status: ($event.target as HTMLSelectElement).value }, t('support.statusSaved'))">
            <option v-for="status in STATUSES" :key="status" :value="status">{{ $t(`status.${status}`) }}</option>
          </select>
        </div>
        <button v-if="item.assigned_to?.id !== auth.user?.id" type="button" class="btn btn-secondary" @click="update({ assigned_to_id: auth.user?.id }, t('support.assigned'))">{{ $t('support.assignMe') }}</button>
        <button v-if="item.kind === 'attendee' && !item.is_escalated" type="button" class="btn btn-secondary" @click="update({ is_escalated: true }, t('support.escalatedDone'))">{{ $t('support.escalate') }}</button>
      </div>

      <ol ref="thread" class="space-y-3" aria-live="polite">
        <li v-for="message in item.messages" :key="message.id" class="flex" :class="message.is_mine ? 'justify-end' : 'justify-start'">
          <div class="max-w-[85%] rounded-xl border px-4 py-3" :class="message.is_mine ? 'border-sky-deep/30 bg-sky-pale' : 'border-line bg-white'">
            <p class="mb-1 text-sm">
              <strong>{{ message.is_mine ? $t('support.you') : message.author_name }}</strong>
              <span v-if="message.from_staff" class="text-ink-soft"> ({{ $t('support.staffSide') }})</span>
              <span class="text-ink-soft">, {{ dateTime(message.created_at) }}</span>
            </p>
            <p class="whitespace-pre-line">{{ message.body }}</p>
          </div>
        </li>
      </ol>

      <form class="card mt-5" @submit.prevent="send">
        <label class="label" for="reply">{{ $t('support.reply') }}</label>
        <textarea id="reply" v-model="reply" class="input" rows="3" maxlength="5000" required />
        <div class="mt-3 flex items-center justify-between gap-3">
          <p class="text-sm text-ink-soft">{{ $t('support.asyncHint') }}</p>
          <button type="submit" class="btn btn-primary" :disabled="busy">{{ $t('support.send') }}</button>
        </div>
      </form>
    </template>
  </div>
</template>
