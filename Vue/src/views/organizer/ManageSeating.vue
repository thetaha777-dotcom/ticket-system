<script setup lang="ts">
/**
 * Seat-map set-up for assigned seating: choose the ticket type (price) sold in each section of the
 * venue's predefined layout and block seats that must not be sold. No visual layout editor is needed.
 */
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'

import SeatMapView from '@/components/SeatMap.vue'
import { api } from '@/lib/api'
import { errorText, money } from '@/lib/format'
import { useManagedEvent } from '@/lib/managed'
import { useToastStore } from '@/stores/toast'
import type { SeatMap, VenueLayout } from '@/types'

const { event, reload } = useManagedEvent()
const toasts = useToastStore()
const { t } = useI18n()

const layout = ref<VenueLayout | null>(null)
const live = ref<SeatMap | null>(null)
const sectionType = reactive<Record<string, string>>({}) // venue section id -> ticket type id ('' = closed)
const blocked = ref<Set<string>>(new Set()) // venue seat ids
const problem = ref('')
const locked = ref(false)

async function load(): Promise<void> {
  if (event.value.seating !== 'assigned_seating') return
  try {
    ;[layout.value, live.value] = await Promise.all([
      api.get<VenueLayout>(`/venues/${event.value.venue.id}/layout`),
      api.get<SeatMap>(`/organizer/events/${event.value.id}/seating`),
    ])
    const blockedNow = new Set<string>()
    locked.value = false
    for (const section of live.value.sections) {
      sectionType[section.id] = section.ticket_category_id ?? ''
      for (const row of section.rows) {
        for (const seat of row.seats) {
          if (seat.status === 'unavailable' && section.ticket_category_id) blockedNow.add(seat.seat_id)
          if (seat.status === 'held' || seat.status === 'sold') locked.value = true
        }
      }
    }
    blocked.value = blockedNow
  } catch (error) {
    problem.value = errorText(error)
  }
}

function toggleSeat(seatId: string): void {
  const next = new Set(blocked.value)
  if (next.has(seatId)) next.delete(seatId)
  else next.add(seatId)
  blocked.value = next
}

async function save(): Promise<void> {
  problem.value = ''
  try {
    live.value = await api.put<SeatMap>(`/organizer/events/${event.value.id}/seating`, {
      sections: Object.entries(sectionType).map(([section_id, typeId]) => ({ section_id, ticket_category_id: typeId || null })),
      unavailable_seat_ids: [...blocked.value],
    })
    await reload()
    toasts.ok(t('seating.saved'))
  } catch (error) {
    problem.value = errorText(error)
  }
}

onMounted(load)
</script>

<template>
  <div v-if="event.seating !== 'assigned_seating'" class="card">
    <p class="mb-3 max-w-[65ch]">{{ $t('seating.general') }}</p>
    <RouterLink class="btn btn-secondary" :to="{ name: 'event-edit', params: { id: event.id } }">{{ $t('manage.edit') }}</RouterLink>
  </div>

  <div v-else class="space-y-6">
    <p v-if="problem" class="notice notice-bad" role="alert">{{ problem }}</p>
    <p v-if="locked" class="notice notice-warn">{{ $t('seating.locked') }}</p>
    <p v-else-if="!event.ticket_types.length" class="notice notice-warn">
      {{ $t('seating.needTypes') }} <RouterLink :to="{ name: 'manage-tickets', params: { id: event.id } }">{{ $t('manage.tab.tickets') }}</RouterLink>
    </p>

    <form v-if="layout && !locked" class="card space-y-5" @submit.prevent="save">
      <div>
        <h2 class="card-title">{{ $t('seating.prices') }}</h2>
        <p class="mb-3 text-sm text-ink-soft">{{ $t('seating.pricesHint') }}</p>
        <div class="grid gap-3 sm:grid-cols-3">
          <div v-for="section in layout.sections" :key="section.id">
            <label class="label" :for="`section-${section.id}`">{{ section.name }} <span class="font-normal text-ink-soft">({{ section.price_category }})</span></label>
            <select :id="`section-${section.id}`" v-model="sectionType[section.id]" class="input">
              <option value="">{{ $t('seating.closed') }}</option>
              <option v-for="type in event.ticket_types" :key="type.id" :value="type.id">{{ type.name }}, {{ type.price ? money(type.price) : $t('event.free') }}</option>
            </select>
          </div>
        </div>
      </div>

      <div>
        <h2 class="card-title">{{ $t('seating.block') }}</h2>
        <p class="mb-3 text-sm text-ink-soft">{{ $t('seating.blockHint') }}</p>
        <div class="overflow-x-auto pb-2">
          <div class="mx-auto w-max min-w-full">
            <section v-for="section in layout.sections" :key="section.id" class="mb-4" :aria-label="section.name">
              <h3 class="mb-2 text-center font-sans text-sm font-semibold">{{ section.name }}</h3>
              <div v-for="row in section.rows" :key="row.id" class="mb-1 flex items-center justify-center gap-1">
                <span class="w-6 text-right text-xs text-ink-soft" aria-hidden="true">{{ row.label }}</span>
                <button
                  v-for="seat in row.seats" :key="seat.id" type="button" class="seat" :class="{ 'seat-unavailable': blocked.has(seat.id) }"
                  :aria-pressed="blocked.has(seat.id)"
                  :aria-label="`${section.name}, ${$t('seat.rowN', { row: row.label })}, ${$t('seat.seatN', { n: seat.number })}, ${blocked.has(seat.id) ? $t('seat.unavailable') : $t('seat.available')}`"
                  @click="toggleSeat(seat.id)"
                >{{ blocked.has(seat.id) ? '–' : seat.is_accessible ? '♿' : seat.number }}</button>
              </div>
            </section>
          </div>
        </div>
      </div>
      <button type="submit" class="btn btn-primary" :disabled="!event.ticket_types.length">{{ $t('seating.save') }}</button>
    </form>

    <section v-if="live?.configured" class="card">
      <h2 class="card-title">{{ $t('seating.live') }}</h2>
      <SeatMapView :map="live" readonly />
    </section>
  </div>
</template>
