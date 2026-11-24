<script setup lang="ts">
/** One issued ticket, shaped like a pass: details on top, tear line, QR code below. */
import { ref } from 'vue'

import QrCode from '@/components/QrCode.vue'
import StatusBadge from '@/components/StatusBadge.vue'
import { api } from '@/lib/api'
import { dateTime } from '@/lib/format'
import { useToastStore } from '@/stores/toast'
import type { Ticket } from '@/types'

const props = defineProps<{ ticket: Ticket }>()
const toasts = useToastStore()
const busy = ref(false)

async function downloadPdf(): Promise<void> {
  busy.value = true
  try {
    await api.download(`/tickets/${props.ticket.id}/pdf`, `ticket-${props.ticket.code}.pdf`)
  } catch (error) {
    toasts.error(error)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <article class="ticket-wrap w-full max-w-sm">
    <div class="pass">
      <div class="p-5">
        <div class="mb-2 flex items-start justify-between gap-3">
          <h3 class="text-2xl">{{ ticket.event.title }}</h3>
          <StatusBadge :status="ticket.status" />
        </div>
        <dl class="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <div class="col-span-2"><dt class="text-ink-soft">{{ $t('ticket.when') }}</dt><dd class="font-semibold">{{ dateTime(ticket.event.start_at, ticket.event.timezone) }}</dd></div>
          <div class="col-span-2"><dt class="text-ink-soft">{{ $t('ticket.where') }}</dt><dd class="font-semibold">{{ ticket.event.venue_name }}, {{ ticket.event.venue_address }}, {{ ticket.event.venue_city }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('ticket.attendee') }}</dt><dd class="font-semibold">{{ ticket.attendee_name }}</dd></div>
          <div><dt class="text-ink-soft">{{ $t('ticket.type') }}</dt><dd class="font-semibold">{{ ticket.ticket_type }}</dd></div>
          <div v-if="ticket.seat_row" class="col-span-2">
            <dt class="text-ink-soft">{{ $t('ticket.seat') }}</dt>
            <dd class="font-semibold">{{ ticket.seat_section }}, {{ $t('seat.rowN', { row: ticket.seat_row }) }}, {{ $t('seat.seatN', { n: ticket.seat_number }) }}</dd>
          </div>
        </dl>
      </div>
      <div class="pass-stub flex flex-col items-center justify-center gap-2 px-5">
        <template v-if="ticket.qr_payload">
          <QrCode :value="ticket.qr_payload" :size="170" :label="$t('ticket.qrLabel', { code: ticket.code })" />
          <p class="font-display text-xl font-semibold tracking-widest">{{ ticket.code }}</p>
          <button type="button" class="btn btn-secondary btn-sm no-print" :disabled="busy" @click="downloadPdf">{{ $t('ticket.downloadPdf') }}</button>
        </template>
        <template v-else>
          <p class="font-display text-xl font-semibold tracking-widest text-ink-soft line-through">{{ ticket.code }}</p>
          <p class="text-center text-sm text-ink-soft">{{ $t('ticket.notValid') }}</p>
        </template>
      </div>
    </div>
  </article>
</template>

<style scoped>
/* Vertical variant of the ticket shape: the notches sit on the left and right edges of the tear line. */
.pass {
  --stub: 292px;
  --notch: 11px;
  background: #fff;
  border-radius: 12px;
  -webkit-mask:
    radial-gradient(circle var(--notch) at 0 calc(100% - var(--stub)), #0000 97%, #000) left / 51% 100% no-repeat,
    radial-gradient(circle var(--notch) at 100% calc(100% - var(--stub)), #0000 97%, #000) right / 51% 100% no-repeat;
  mask:
    radial-gradient(circle var(--notch) at 0 calc(100% - var(--stub)), #0000 97%, #000) left / 51% 100% no-repeat,
    radial-gradient(circle var(--notch) at 100% calc(100% - var(--stub)), #0000 97%, #000) right / 51% 100% no-repeat;
}
.pass-stub {
  height: var(--stub);
  border-top: 2px dashed var(--color-line);
}
</style>
