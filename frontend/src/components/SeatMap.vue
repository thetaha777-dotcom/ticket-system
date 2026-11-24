<script setup lang="ts">
/**
 * Interactive seat map for assigned-seating events.
 * Every seat is a real <button> with a spoken label, and every status has a symbol
 * as well as a colour: number = available, ✓ = selected, … = held, ✕ = sold, – = unavailable.
 */
import { useI18n } from 'vue-i18n'

import { money } from '@/lib/format'
import type { SeatMap, SeatMapSeat, SeatMapSection } from '@/types'

const props = withDefaults(defineProps<{ map: SeatMap; modelValue?: string[]; readonly?: boolean; max?: number }>(), {
  modelValue: () => [], readonly: false, max: 10,
})
const emit = defineEmits<{ 'update:modelValue': [ids: string[]]; limit: [] }>()
const { t } = useI18n()

const isSelected = (seat: SeatMapSeat): boolean => props.modelValue.includes(seat.id)

function seatClass(seat: SeatMapSeat): string {
  if (isSelected(seat)) return 'seat-selected'
  return { available: '', held: 'seat-held', sold: 'seat-sold', unavailable: 'seat-unavailable' }[seat.status]
}
function symbol(seat: SeatMapSeat): string {
  if (isSelected(seat)) return '✓'
  if (seat.status === 'held') return '…'
  if (seat.status === 'sold') return '✕'
  if (seat.status === 'unavailable') return '–'
  return seat.is_accessible ? '♿' : String(seat.number)
}
function label(section: SeatMapSection, row: string, seat: SeatMapSeat): string {
  const status = isSelected(seat) ? t('seat.selected') : t(`seat.${seat.status}`)
  const parts = [section.name, t('seat.rowN', { row }), t('seat.seatN', { n: seat.number }), status]
  if (seat.is_accessible) parts.push(t('seat.accessible'))
  if (section.price !== null) parts.push(money(section.price))
  return parts.join(', ')
}
function toggle(seat: SeatMapSeat): void {
  if (props.readonly || seat.status !== 'available') return
  if (isSelected(seat)) emit('update:modelValue', props.modelValue.filter((id) => id !== seat.id))
  else if (props.modelValue.length >= props.max) emit('limit')
  else emit('update:modelValue', [...props.modelValue, seat.id])
}
</script>

<template>
  <div>
    <div class="overflow-x-auto pb-2">
      <div class="mx-auto w-max min-w-full px-1">
        <div class="mx-auto mb-5 w-2/3 max-w-md rounded-b-[2rem] bg-ink py-1.5 text-center text-sm font-semibold text-white">{{ $t('seat.stage') }}</div>
        <section v-for="section in map.sections" :key="section.id" class="mb-5" :aria-label="section.name">
          <h4 class="mb-2 text-center text-sm font-semibold">
            {{ section.name }}
            <span v-if="section.price !== null" class="font-normal text-ink-soft">
              ({{ section.ticket_type_name }}, {{ section.price === 0 ? $t('event.free') : money(section.price) }})
            </span>
          </h4>
          <div v-for="row in section.rows" :key="row.label" class="mb-1 flex items-center justify-center gap-1">
            <span class="w-6 text-right text-xs text-ink-soft" aria-hidden="true">{{ row.label }}</span>
            <button
              v-for="seat in row.seats" :key="seat.id" type="button" class="seat" :class="seatClass(seat)"
              :disabled="readonly || seat.status !== 'available'" :aria-pressed="isSelected(seat)"
              :aria-label="label(section, row.label, seat)" :title="label(section, row.label, seat)" @click="toggle(seat)"
            >{{ symbol(seat) }}</button>
            <span class="w-6 text-xs text-ink-soft" aria-hidden="true">{{ row.label }}</span>
          </div>
        </section>
      </div>
    </div>

    <ul class="mt-2 flex flex-wrap gap-x-5 gap-y-2 text-sm" :aria-label="$t('seat.legend')">
      <li class="flex items-center gap-2"><span class="seat" aria-hidden="true">7</span>{{ $t('seat.available') }}</li>
      <li class="flex items-center gap-2"><span class="seat seat-selected" aria-hidden="true">✓</span>{{ $t('seat.selected') }}</li>
      <li class="flex items-center gap-2"><span class="seat seat-held" aria-hidden="true">…</span>{{ $t('seat.held') }}</li>
      <li class="flex items-center gap-2"><span class="seat seat-sold" aria-hidden="true">✕</span>{{ $t('seat.sold') }}</li>
      <li class="flex items-center gap-2"><span class="seat seat-unavailable" aria-hidden="true">–</span>{{ $t('seat.unavailable') }}</li>
      <li class="flex items-center gap-2"><span class="seat" aria-hidden="true">♿</span>{{ $t('seat.accessible') }}</li>
    </ul>
  </div>
</template>
