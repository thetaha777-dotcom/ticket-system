<script setup lang="ts">
/** Ticket types of the event with their inventory counters; create, edit, hide and delete. */
import { reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import ModalDialog from '@/components/ModalDialog.vue'
import { api } from '@/lib/api'
import { errorText, fromLocalInput, money, toLocalInput } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { TicketType } from '@/types'

const { event, reload } = useManagedEvent()
const toasts = useToastStore()
const { t } = useI18n()

const open = ref(false)
const editing = ref<TicketType | null>(null)
const problem = ref('')
const form = reactive({ name: '', description: '', type: 'free' as 'free' | 'paid', price: 0, quantity: 100, order_limit: 10, hidden: false, saleStart: '', saleEnd: '' })
const base = (): string => `/organizer/events/${event.value.id}/ticket-types`
const seated = (): boolean => event.value.seating === 'assigned_seating'

function startCreate(): void {
  editing.value = null
  Object.assign(form, { name: '', description: '', type: 'free', price: 0, quantity: 100, order_limit: 10, hidden: false, saleStart: '', saleEnd: '' })
  problem.value = ''
  open.value = true
}

function startEdit(type: TicketType): void {
  editing.value = type
  Object.assign(form, {
    name: type.name, description: type.description ?? '', type: type.type, price: type.price, quantity: type.quantity,
    order_limit: type.order_limit, hidden: type.hidden, saleStart: toLocalInput(type.sale_start, event.value.timezone),
    saleEnd: toLocalInput(type.sale_end, event.value.timezone),
  })
  problem.value = ''
  open.value = true
}

async function save(): Promise<void> {
  const body: Record<string, unknown> = {
    name: form.name, description: form.description || null, price: form.type === 'paid' ? form.price : 0, quantity: form.quantity,
    order_limit: form.order_limit, hidden: form.hidden, sale_start: fromLocalInput(form.saleStart, event.value.timezone),
    sale_end: fromLocalInput(form.saleEnd, event.value.timezone),
  }
  try {
    if (editing.value) await api.patch(`${base()}/${editing.value.id}`, body)
    else await api.post(base(), { ...body, type: form.type })
    open.value = false
    await reload()
    toasts.ok(t('tickets.saved'))
  } catch (error) {
    problem.value = errorText(error)
  }
}

async function toggleHidden(type: TicketType): Promise<void> {
  try {
    await api.patch(`${base()}/${type.id}`, { hidden: !type.hidden })
    await reload()
  } catch (error) {
    toasts.error(error)
  }
}

async function remove(type: TicketType): Promise<void> {
  if (!window.confirm(t('tickets.deleteConfirm', { name: type.name }))) return
  try {
    await api.delete(`${base()}/${type.id}`)
    await reload()
  } catch (error) {
    toasts.error(error)
  }
}
</script>

<template>
  <div>
    <div class="mb-4 flex flex-wrap items-center justify-between gap-3">
      <p class="max-w-[65ch] text-sm text-ink-soft">{{ $t('tickets.lead') }}</p>
      <button v-if="event.status !== 'cancelled'" type="button" class="btn btn-primary" @click="startCreate">{{ $t('tickets.add') }}</button>
    </div>

    <p v-if="!event.ticket_types.length" class="card text-ink-soft">{{ $t('tickets.empty') }}</p>
    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>{{ $t('tickets.type') }}</th><th class="num">{{ $t('tickets.price') }}</th><th class="num">{{ $t('tickets.quantity') }}</th>
            <th class="num">{{ $t('tickets.available') }}</th><th class="num">{{ $t('tickets.reserved') }}</th><th class="num">{{ $t('tickets.sold') }}</th>
            <th class="num">{{ $t('tickets.refunded') }}</th><th class="num">{{ $t('tickets.checkedIn') }}</th><th><span class="sr-only">{{ $t('common.actions') }}</span></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="type in event.ticket_types" :key="type.id">
            <td>
              <strong>{{ type.name }}</strong>
              <span v-if="type.hidden" class="badge ml-2">{{ $t('tickets.hidden') }}</span>
              <div class="text-ink-soft">{{ $t('tickets.perOrder', { n: type.order_limit }) }}</div>
            </td>
            <td class="num">{{ type.type === 'free' ? $t('event.free') : money(type.price) }}</td>
            <td class="num">{{ type.quantity }}</td><td class="num">{{ type.available }}</td><td class="num">{{ type.reserved }}</td>
            <td class="num font-semibold">{{ type.sold }}</td><td class="num">{{ type.refunded }}</td><td class="num">{{ type.checked_in }}</td>
            <td class="whitespace-nowrap">
              <button type="button" class="btn btn-ghost btn-sm" @click="startEdit(type)">{{ $t('common.edit') }}</button>
              <button type="button" class="btn btn-ghost btn-sm" @click="toggleHidden(type)">{{ type.hidden ? $t('tickets.show') : $t('tickets.hide') }}</button>
              <button v-if="!type.sold && !type.reserved" type="button" class="btn btn-ghost btn-sm text-bad" @click="remove(type)">{{ $t('common.delete') }}</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <ModalDialog :open="open" :title="editing ? $t('tickets.editTitle') : $t('tickets.add')" @close="open = false">
      <form class="space-y-4" @submit.prevent="save">
        <div><label class="label" for="tt-name">{{ $t('tickets.name') }}</label><input id="tt-name" v-model="form.name" class="input" required maxlength="255" /></div>
        <div><label class="label" for="tt-desc">{{ $t('eventForm.description') }}</label><input id="tt-desc" v-model="form.description" class="input" /></div>
        <fieldset v-if="!editing">
          <legend class="label">{{ $t('tickets.kind') }}</legend>
          <label class="mr-5 inline-flex cursor-pointer items-center gap-2"><input v-model="form.type" type="radio" value="free" /> {{ $t('tickets.free') }}</label>
          <label class="inline-flex cursor-pointer items-center gap-2"><input v-model="form.type" type="radio" value="paid" /> {{ $t('tickets.paid') }}</label>
          <p v-if="form.type === 'paid'" class="hint">{{ $t('tickets.paidHint') }}</p>
        </fieldset>
        <div class="grid gap-3 sm:grid-cols-3">
          <div v-if="form.type === 'paid'"><label class="label" for="tt-price">{{ $t('tickets.priceKzt') }}</label><input id="tt-price" v-model.number="form.price" type="number" min="1" step="1" class="input" required /></div>
          <div>
            <label class="label" for="tt-qty">{{ $t('tickets.quantity') }}</label>
            <input id="tt-qty" v-model.number="form.quantity" type="number" min="1" class="input" required :disabled="seated()" />
          </div>
          <div><label class="label" for="tt-limit">{{ $t('tickets.limit') }}</label><input id="tt-limit" v-model.number="form.order_limit" type="number" min="1" max="50" class="input" required /></div>
        </div>
        <p v-if="seated()" class="hint">{{ $t('tickets.seatedHint') }}</p>
        <div class="grid gap-3 sm:grid-cols-2">
          <div><label class="label" for="tt-start">{{ $t('tickets.saleStart') }}</label><input id="tt-start" v-model="form.saleStart" type="datetime-local" class="input" /></div>
          <div><label class="label" for="tt-end">{{ $t('tickets.saleEnd') }}</label><input id="tt-end" v-model="form.saleEnd" type="datetime-local" class="input" /></div>
        </div>
        <label class="flex cursor-pointer items-center gap-2"><input v-model="form.hidden" type="checkbox" class="h-4 w-4" /> {{ $t('tickets.hiddenLabel') }}</label>
        <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
        <div class="flex justify-end gap-2">
          <button type="button" class="btn btn-secondary" @click="open = false">{{ $t('common.cancel') }}</button>
          <button type="submit" class="btn btn-primary">{{ $t('common.save') }}</button>
        </div>
      </form>
    </ModalDialog>
  </div>
</template>
